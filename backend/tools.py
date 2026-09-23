"""Tool implementations for the Yale SOM course-explorer agent.

search_courses  — SQL search over the `courses` table (SQLite or Supabase)
web_search      — DuckDuckGo instant-answer API (no key required)
"""

from __future__ import annotations

import httpx

import db
from models import CourseSearchResult

_MAX_RESULTS = 15


def search_courses(
    query: str = "",
    category: str = "",
    day: str = "",
    faculty: str = "",
    session: str = "",
) -> list[dict]:
    """
    Search the Yale SOM Fall 2026 course catalog.

    Parameters
    ----------
    query:    Free-text search across title, course number, faculty name, category, and description.
    category: Filter by category, e.g. 'Core', 'Finance', 'Artificial Intelligence'.
    day:      Filter by meeting day abbreviation: 'Mo', 'Tu', 'We', 'Th', 'Fr'.
    faculty:  Filter by faculty last name or partial name fragment.
    session:  Filter by session: 'fall', 'fall-1', or 'fall-2'.

    Returns up to 15 matching courses as dicts.
    """
    rows = db.search_courses(
        query=query,
        category=category,
        day=day,
        faculty=faculty,
        session=session,
        limit=_MAX_RESULTS,
    )

    results: list[CourseSearchResult] = []
    for row in rows:
        desc = row["course_description"] or ""
        results.append(
            CourseSearchResult(
                number=row["course_number"] or "",
                section=row["section"] or "",
                title=row["course_title"] or "",
                faculty=row["faculty_1"] or "",
                category=row["course_category"] or "",
                daytimes=row["daytimes"] or "",
                session=row["course_session"] or "",
                units=row["units"] or "",
                room=row["room"] or "",
                description=desc[:400] + "…" if len(desc) > 400 else desc,
                faculty_bio=(row["faculty_bio"] or "")[:300],
                syllabus=row["syllabus"] or row["old_syllabus"] or "",
            )
        )
    return [r.model_dump() for r in results]


def web_search(query: str) -> str:
    """
    Search the public web via DuckDuckGo's Instant Answer API.

    Use when the course catalog is insufficient — e.g. faculty news,
    research context, external syllabi, or Yale SOM announcements.
    """
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
            )
            data = resp.json()

        abstract = data.get("AbstractText", "").strip()
        if abstract:
            return abstract

        related = data.get("RelatedTopics", [])
        snippets = [
            t["Text"]
            for t in related[:4]
            if isinstance(t, dict) and t.get("Text")
        ]
        return "\n".join(snippets) if snippets else "No web results found for that query."

    except Exception as exc:
        return f"Web search unavailable: {exc}"
