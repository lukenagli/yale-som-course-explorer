"""Password hashing (bcrypt) and login tokens (signed JWTs).

bcrypt generates a random salt per password and stores it inside the hash
string itself ("$2b$12$<22-char salt><31-char hash>"), so the users table
only needs a single password_hash column.

After login the API returns a JWT that the browser sends back as
`Authorization: Bearer <token>`. Tokens are signed with JWT_SECRET.
"""

from __future__ import annotations

import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import db

TOKEN_TTL = timedelta(days=7)
_ALGORITHM = "HS256"

JWT_SECRET = os.environ.get("JWT_SECRET", "").strip()
if not JWT_SECRET:
    # Fine for local dev; logins reset whenever the server restarts.
    JWT_SECRET = secrets.token_urlsafe(48)
    warnings.warn("JWT_SECRET is not set — using a temporary secret for this process.")


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + TOKEN_TTL}
    return jwt.encode(payload, JWT_SECRET, algorithm=_ALGORITHM)


_bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI dependency: the signed-in user, or 401."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Please sign in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[_ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = db.get_user(user_id)
    if user is None:
        raise unauthorized
    return user
