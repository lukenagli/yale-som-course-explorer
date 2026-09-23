"""Database layer for the Yale SOM course explorer.

One set of table definitions, two databases:
  - Local:      data/yale_som.db (SQLite) — used when DATABASE_URL is unset.
  - Production: Supabase Postgres — set DATABASE_URL to the Supabase
                connection string (Session pooler URI).

Tables:
  courses  — SOM course catalog (ships pre-filled in yale_som.db)
  users    — accounts; passwords stored as bcrypt hashes
  chats    — one row per chat message, linked to users.id
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    delete,
    func,
    insert,
    or_,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SQLITE_PATH = ROOT / "data" / "yale_som.db"

load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def normalize_url(url: str) -> str:
    """Point postgres:// / postgresql:// URLs at the psycopg (v3) driver."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def make_engine(url: str) -> Engine:
    url = normalize_url(url)
    if url.startswith("sqlite"):
        # FastAPI runs sync endpoints on a thread pool.
        return create_engine(url, connect_args={"check_same_thread": False})
    # prepare_threshold=None keeps psycopg compatible with Supabase's pooler.
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"prepare_threshold": None},
    )


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip() or f"sqlite:///{SQLITE_PATH.as_posix()}"
engine = make_engine(DATABASE_URL)


def backend_name() -> str:
    return engine.dialect.name  # "sqlite" or "postgresql"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
metadata = MetaData()

COURSE_COLUMNS = [
    "course_id", "course_number", "course_title", "course_category",
    "course_type", "course_session", "course_description", "faculty_1",
    "faculty_1_email", "faculty_bio", "daytimes", "timings_day",
    "timings_start", "timings_end", "room", "section", "units",
    "term_code", "syllabus", "old_syllabus",
]

courses = Table(
    "courses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    *[Column(name, Text) for name in COURSE_COLUMNS],
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("name", String(255), nullable=False, default=""),
    Column("password_hash", String(255), nullable=False),  # bcrypt, salt included
    Column("created_at", DateTime(timezone=True), nullable=False, default=_utcnow),
)

chats = Table(
    "chats",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("role", String(16), nullable=False),  # "user" | "assistant"
    Column("content", Text, nullable=False),
    Column("tools_used", JSON, nullable=False, default=list),
    Column("created_at", DateTime(timezone=True), nullable=False, default=_utcnow),
)


def init_db(target: Engine | None = None) -> None:
    """Create any missing tables. Existing tables (e.g. courses) are left alone."""
    metadata.create_all(target or engine, checkfirst=True)


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

SEARCH_FIELDS = (
    "course_title", "course_number", "faculty_1", "course_category", "course_description",
)


_ESC = "!"  # LIKE escape char; avoids backslash quoting differences between SQLite and Postgres


def _like(value: str) -> str:
    escaped = value.replace(_ESC, _ESC * 2).replace("%", _ESC + "%").replace("_", _ESC + "_")
    return f"%{escaped}%"


def _ilike(column, value: str):
    return column.ilike(_like(value), escape=_ESC)


def list_courses(q: str | None = None) -> list[dict]:
    """All courses for the catalog grid, optionally filtered by free text."""
    stmt = select(courses).order_by(courses.c.course_number, courses.c.section, courses.c.id)
    if q and q.strip():
        stmt = stmt.where(or_(*(_ilike(courses.c[name], q.strip()) for name in COURSE_COLUMNS)))
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(stmt).mappings()]


def count_courses() -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(courses)).scalar_one()


def search_courses(
    query: str = "",
    category: str = "",
    day: str = "",
    faculty: str = "",
    session: str = "",
    limit: int = 15,
) -> list[dict]:
    """Field + free-text search over the courses table.

    Every word in `query` must appear in at least one of SEARCH_FIELDS
    (case-insensitive), so "machine learning" matches either word order.
    """
    conditions = []
    for term in query.split():
        conditions.append(or_(*(_ilike(courses.c[f], term) for f in SEARCH_FIELDS)))
    if category.strip():
        conditions.append(_ilike(courses.c.course_category, category.strip()))
    if day.strip():
        conditions.append(_ilike(courses.c.timings_day, day.strip()))
    if faculty.strip():
        conditions.append(_ilike(courses.c.faculty_1, faculty.strip()))
    if session.strip():
        conditions.append(func.lower(courses.c.course_session) == session.strip().lower())

    stmt = (
        select(courses)
        .where(and_(*conditions))
        .order_by(courses.c.course_number, courses.c.section, courses.c.id)
        .limit(limit)
    )
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(stmt).mappings()]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def _public_user(row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def create_user(email: str, name: str, password_hash: str) -> dict | None:
    """Insert a user. Returns None if the email is already registered."""
    try:
        with engine.begin() as conn:
            new_id = conn.execute(
                insert(users)
                .values(email=email, name=name, password_hash=password_hash)
                .returning(users.c.id)
            ).scalar_one()
    except IntegrityError:
        return None
    return {"id": new_id, "email": email, "name": name}


def get_user_with_hash(email: str) -> dict | None:
    """Row including password_hash — only for login verification."""
    with engine.connect() as conn:
        row = conn.execute(select(users).where(users.c.email == email)).mappings().first()
    return dict(row) if row else None


def get_user(user_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(select(users).where(users.c.id == user_id)).mappings().first()
    return _public_user(row) if row else None


# ---------------------------------------------------------------------------
# Chats
# ---------------------------------------------------------------------------

def _chat_row(row) -> dict:
    created = row["created_at"]
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "tools_used": row["tools_used"] or [],
        "created_at": created.isoformat() if created else None,
    }


def add_chat_messages(user_id: int, messages: list[dict]) -> None:
    """Save messages ({role, content, tools_used?}) in order, in one transaction."""
    rows = [
        {
            "user_id": user_id,
            "role": m["role"],
            "content": m["content"],
            "tools_used": list(m.get("tools_used") or []),
        }
        for m in messages
    ]
    with engine.begin() as conn:
        for row in rows:  # one insert per row so ids follow message order
            conn.execute(insert(chats).values(**row))


def get_chat_history(user_id: int, limit: int | None = None) -> list[dict]:
    """A user's messages, oldest first. With `limit`, only the most recent N."""
    stmt = select(chats).where(chats.c.user_id == user_id).order_by(chats.c.id.desc())
    if limit:
        stmt = stmt.limit(limit)
    with engine.connect() as conn:
        rows = [_chat_row(r) for r in conn.execute(stmt).mappings()]
    rows.reverse()
    return rows


def clear_chat_history(user_id: int) -> int:
    with engine.begin() as conn:
        return conn.execute(delete(chats).where(chats.c.user_id == user_id)).rowcount
