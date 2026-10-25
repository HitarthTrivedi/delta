"""Integrity notes for practice sessions recruiters rely on.

Plain facts, never an accusation: how a session was taken (timed or not) and a
few signals worth a second look (leaving the tab, pasting code, finishing
implausibly fast). The learner sees exactly what a recruiter sees.

Tab and paste counts are reported by the learner's browser, so they are
signals, not proof. Timing comes from our own server clock.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.models.sandbox_session import SandboxSession

PASTE_NOTE_CHARS = 200        # pasted code below this is ordinary (a variable name, an import)
FAST_SECONDS_PER_QUESTION = 4  # faster than this across a whole test is worth a note


class IntegrityPayload(BaseModel):
    """What the browser saw during the session (counts since it started)."""
    tab_switches: int = Field(default=0, ge=0, le=999)
    pastes: int = Field(default=0, ge=0, le=999)
    pasted_chars: int = Field(default=0, ge=0, le=1_000_000)


def record(data: dict, payload: IntegrityPayload | None) -> None:
    """Store the browser's counts on the session data (latest report wins)."""
    if payload is not None:
        data["integrity"] = payload.model_dump()


def notes(session: SandboxSession) -> dict:
    try:
        data = json.loads(session.data or "{}")
    except ValueError:
        data = {}
    seen = data.get("integrity") or {}
    flags = []
    switches = int(seen.get("tab_switches") or 0)
    if switches:
        flags.append(f"Left the tab {switches} time{'s' if switches != 1 else ''}")
    pasted = int(seen.get("pasted_chars") or 0)
    if pasted >= PASTE_NOTE_CHARS:
        what = "code" if session.type == "coding" else "text into answers"
        flags.append(f"Pasted about {pasted} characters of {what}")
    result = data.get("result") or {}
    timed = bool(session.type == "theory" and data.get("time_limit_seconds"))
    if session.type == "theory":
        total, taken = result.get("total") or 0, result.get("time_taken_seconds")
        if total >= 5 and taken is not None and taken < total * FAST_SECONDS_PER_QUESTION:
            flags.append(f"Answered {total} questions in {taken} seconds")
        if result.get("overtime"):
            flags.append("Went past the time limit")
    return {"timed": timed, "flags": flags, "reported": bool(seen)}


def summary(sessions: list[SandboxSession]) -> dict:
    """Across a learner's completed sessions: how many were timed, and how many have notes."""
    all_notes = [notes(s) for s in sessions]
    return {
        "sessions": len(all_notes),
        "timed": sum(1 for n in all_notes if n["timed"]),
        "with_notes": sum(1 for n in all_notes if n["flags"]),
    }
