"""Yale SOM course explorer API.

Run from backend/:  uvicorn main:app --port 8000
Open API docs:      http://127.0.0.1:8000/docs
Frontend (Vite):    http://127.0.0.1:5173

Database: data/yale_som.db locally, or Supabase when DATABASE_URL is set.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

import db
from agent import run_agent
from auth import create_token, current_user, hash_password, verify_password
from models import (
    AuthResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    SignupRequest,
    User,
)

# How many earlier messages the agent sees as conversation context.
HISTORY_FOR_AGENT = 20


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()  # creates users / chats if they don't exist yet
    yield


app = FastAPI(title="Yale SOM Courses", version="0.2.0", lifespan=lifespan)

# FRONTEND_ORIGIN: comma-separated list, e.g. https://yale-som-courses.onrender.com
_origins = [o.strip().rstrip("/") for o in os.environ.get("FRONTEND_ORIGIN", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,  # auth uses a Bearer header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


# ---------------------------------------------------------------------------
# Health + catalog
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"ok": True, "database": db.backend_name(), "courses": db.count_courses()}


@app.get("/api/courses")
def list_courses(q: str | None = Query(default=None)):
    """Return courses for the React catalog (optional text filter)."""
    courses = db.list_courses(q)
    return {"count": len(courses), "courses": courses}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest):
    email = _normalize_email(body.email)
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if len(body.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=422, detail="Password must be at most 72 bytes.")

    user = db.create_user(email, body.name.strip(), hash_password(body.password))
    if user is None:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    return AuthResponse(token=create_token(user["id"]), user=User(**user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: LoginRequest):
    row = db.get_user_with_hash(_normalize_email(body.email))
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    user = User(id=row["id"], email=row["email"], name=row["name"])
    return AuthResponse(token=create_token(user.id), user=user)


@app.get("/api/auth/me", response_model=User)
def me(user: dict = Depends(current_user)):
    return User(**user)


# ---------------------------------------------------------------------------
# Chat (signed-in users only)
# ---------------------------------------------------------------------------

@app.get("/api/chats", response_model=ChatHistoryResponse)
def chat_history(user: dict = Depends(current_user)):
    return {"messages": db.get_chat_history(user["id"])}


@app.delete("/api/chats")
def clear_chats(user: dict = Depends(current_user)):
    return {"deleted": db.clear_chat_history(user["id"])}


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user: dict = Depends(current_user)):
    history = db.get_chat_history(user["id"], limit=HISTORY_FOR_AGENT)
    result = run_agent(body.message, history=history, user_id=user["id"])
    reply = result.get("reply", "")
    tools_used = list(result.get("tools_used") or [])

    db.add_chat_messages(
        user["id"],
        [
            {"role": "user", "content": body.message},
            {"role": "assistant", "content": reply, "tools_used": tools_used},
        ],
    )
    return ChatResponse(reply=reply, tools_used=tools_used)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
