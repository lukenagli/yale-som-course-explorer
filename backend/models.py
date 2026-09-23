"""Pydantic data models shared by tools.py, agent.py, and main.py."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CourseSearchResult(BaseModel):
    """Trimmed course record returned by search_courses tool."""

    number: str
    section: str
    title: str
    faculty: str
    category: str
    daytimes: str
    session: str
    units: str
    room: str
    description: str
    faculty_bio: str
    syllabus: str


class AgentResult(BaseModel):
    """Shape returned by run_agent() and consumed by main.py."""

    reply: str
    tools_used: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API request / response bodies
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)  # bcrypt uses the first 72 bytes
    name: str = Field(default="", max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=72)


class User(BaseModel):
    id: int
    email: str
    name: str


class AuthResponse(BaseModel):
    token: str
    user: User


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    tools_used: list[str] = Field(default_factory=list)
    created_at: str | None = None


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageOut]
