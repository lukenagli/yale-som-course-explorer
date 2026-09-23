"""Copy the local SQLite database (data/yale_som.db) into Supabase Postgres.

Usage (from backend/, with the venv active):

    python migrate_to_supabase.py                 # uses SUPABASE_DB_URL from .env
    python migrate_to_supabase.py "postgresql://postgres.xxxx:PASSWORD@aws-0-...pooler.supabase.com:5432/postgres"

Creates the courses / users / chats tables in Supabase if needed, then copies
the course catalog. Pass --with-users to also copy local accounts and chats.
Tables that already have rows in Supabase are skipped unless you pass --replace.
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import delete, func, insert, select, text

import db


def _copy_table(source, target, table, replace: bool) -> None:
    with target.connect() as conn:
        existing = conn.execute(select(func.count()).select_from(table)).scalar_one()
    if existing and not replace:
        print(f"  {table.name}: Supabase already has {existing} rows — skipped (use --replace)")
        return

    with source.connect() as conn:
        rows = [dict(r) for r in conn.execute(select(table).order_by(table.c.id)).mappings()]

    with target.begin() as conn:
        if existing:
            conn.execute(delete(table))
        if rows:
            conn.execute(insert(table), rows)
        # Keep Postgres' auto-increment counter ahead of the copied ids.
        conn.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table.name}), 1), "
            f"(SELECT MAX(id) FROM {table.name}) IS NOT NULL)"
        ))
    print(f"  {table.name}: copied {len(rows)} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", nargs="?", help="Supabase connection string (defaults to SUPABASE_DB_URL)")
    parser.add_argument("--with-users", action="store_true", help="also copy users and chats")
    parser.add_argument("--replace", action="store_true", help="overwrite tables that already have rows")
    args = parser.parse_args()

    url = args.url or os.environ.get("SUPABASE_DB_URL", "").strip()
    if not url:
        sys.exit("Pass the Supabase connection string, or set SUPABASE_DB_URL in .env.")
    if not db.normalize_url(url).startswith("postgresql"):
        sys.exit("That doesn't look like a Postgres connection string.")

    source = db.make_engine(f"sqlite:///{db.SQLITE_PATH.as_posix()}")
    target = db.make_engine(url)

    print(f"Source: {db.SQLITE_PATH}")
    print(f"Target: {target.url.render_as_string(hide_password=True)}")
    db.init_db(target)
    print("  tables ready: courses, users, chats")

    tables = [db.courses] + ([db.users, db.chats] if args.with_users else [])
    for table in tables:
        _copy_table(source, target, table, args.replace)
    print("Done.")


if __name__ == "__main__":
    main()
