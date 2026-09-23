"""PydanticAI agent wired to OPENAI_MODEL (default gpt-5.6-luna) via Portkey.

Exposes run_agent(message, history, user_id) -> dict  which main.py calls synchronously.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

import tools as tool_impl
from models import AgentResult

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"

# ---------------------------------------------------------------------------
# Environment — load before building the provider
# ---------------------------------------------------------------------------
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

PORTKEY_API_KEY = os.environ.get("PORTKEY_API_KEY", "")
if not PORTKEY_API_KEY:
    raise RuntimeError(
        "PORTKEY_API_KEY is not set. Add it to Lecture 8/.env (local) "
        "or the Render environment variables (production)."
    )
PORTKEY_BASE_URL = os.environ.get("PORTKEY_BASE_URL", "").strip() or "https://api.portkey.ai/v1"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "").strip() or "gpt-5.6-luna"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Model — Portkey as an OpenAI-compatible gateway
# ---------------------------------------------------------------------------
_provider = OpenAIProvider(
    base_url=PORTKEY_BASE_URL,
    api_key=PORTKEY_API_KEY,
)
_model = OpenAIChatModel(OPENAI_MODEL, provider=_provider)

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
# `instructions` (unlike `system_prompt`) is sent on every run, including runs
# that continue a saved conversation via message_history.
agent = Agent(_model, instructions=_SYSTEM_PROMPT)


@agent.tool_plain
def search_courses(
    query: str = "",
    category: str = "",
    day: str = "",
    faculty: str = "",
    session: str = "",
) -> list[dict]:
    """
    Search the Yale SOM Fall 2026 course catalog.

    query:    Free-text search across title, number, faculty, description.
    category: e.g. 'Core', 'Finance', 'Artificial Intelligence'.
    day:      'Mo', 'Tu', 'We', 'Th', or 'Fr'.
    faculty:  Faculty last name or partial name fragment.
    session:  'fall', 'fall-1', or 'fall-2'.
    """
    return tool_impl.search_courses(
        query=query, category=category, day=day, faculty=faculty, session=session
    )


@agent.tool_plain
def web_search(query: str) -> str:
    """
    Search the public web for context not in the course catalog —
    faculty news, research background, external syllabi, Yale SOM announcements.
    """
    return tool_impl.web_search(query)


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

def _append_audit(entry: dict) -> None:
    """Append one entry to output/audit_trail.json without wiping earlier rows."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if AUDIT_PATH.exists():
        try:
            existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []
    else:
        existing = []
    existing.append(entry)
    AUDIT_PATH.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _extract_tool_calls(result) -> list[dict]:
    """Walk this run's new messages and collect tool name + args + result preview."""
    calls: dict[str, dict] = {}  # keyed by tool_call_id

    for msg in result.new_messages():
        if not hasattr(msg, "parts"):
            continue
        for part in msg.parts:
            tool_name = getattr(part, "tool_name", None)
            if tool_name is None:
                continue

            # ToolCallPart: has args
            if hasattr(part, "args"):
                raw = part.args
                if hasattr(raw, "args_dict"):
                    args = raw.args_dict
                elif isinstance(raw, dict):
                    args = raw
                else:
                    try:
                        args = json.loads(str(raw))
                    except Exception:
                        args = {"raw": str(raw)}

                call_id = getattr(part, "tool_call_id", tool_name)
                calls[call_id] = {"tool": tool_name, "args": args, "result_summary": ""}

            # ToolReturnPart: has content
            elif hasattr(part, "content"):
                call_id = getattr(part, "tool_call_id", tool_name)
                preview = str(part.content)[:200]
                if call_id in calls:
                    calls[call_id]["result_summary"] = preview
                else:
                    calls[call_id] = {
                        "tool": tool_name,
                        "args": {},
                        "result_summary": preview,
                    }

    return list(calls.values())


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def _to_model_messages(history: list[dict]) -> list[ModelMessage]:
    """Turn saved chat rows ({role, content}) into PydanticAI message history."""
    messages: list[ModelMessage] = []
    for row in history:
        if row["role"] == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=row["content"])]))
        elif messages:  # history must start with a user turn
            messages.append(ModelResponse(parts=[TextPart(content=row["content"])]))
    return messages


def run_agent(
    message: str,
    history: list[dict] | None = None,
    user_id: int | None = None,
) -> dict:
    """
    Run the agent synchronously.

    history: earlier saved messages for this user, oldest first, so the agent
             remembers the conversation.

    Returns a dict with:
        reply      str        — the agent's final answer
        tools_used list[str]  — deduplicated tool names in call order
    """
    result = agent.run_sync(message, message_history=_to_model_messages(history or []))

    tool_calls = _extract_tool_calls(result)
    tools_used = list(dict.fromkeys(tc["tool"] for tc in tool_calls))  # ordered dedup

    # Audit trail
    _append_audit(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "user_message": message,
            "tool_calls": tool_calls,
            "reply": result.output,
            "tools_used": tools_used,
            "stop_reason": "end_turn",
        }
    )

    return AgentResult(reply=result.output, tools_used=tools_used).model_dump()
