"""
Persistent memory for Agent 2 weekly tutoring and planning.
Stored in the `agent2_memory_data` JSON column on the users table so it
survives Render dyno restarts (ephemeral disk would wipe file-based storage).

Schema (stored as JSON in agent2_memory_data):
{
  "user_context": {...},
  "upcoming_events": {"events": [...]},
  "current_week": {...},
  "chat_notes": [{"intent", "user_message", "assistant_response", "created_at"}, ...]
  "progress_log": [{...}, ...]
}
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from typing import Any

logger = logging.getLogger("delta.agent2_memory")


def _safe_user_id(user_id: str) -> str:
    user_id = str(user_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", user_id):
        raise ValueError("Invalid user_id.")
    return user_id


def _open_db():
    from app.database import SessionLocal
    return SessionLocal()


def _load_blob(user_id: str) -> dict:
    """Load the full agent2_memory_data blob for a user."""
    db = _open_db()
    try:
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.agent2_memory_data:
            return {}
        return json.loads(user.agent2_memory_data)
    except Exception as e:
        logger.error(f"Failed to load agent2_memory for {user_id}: {e}")
        return {}
    finally:
        db.close()


def _save_blob(user_id: str, blob: dict) -> None:
    """Persist the full agent2_memory_data blob for a user."""
    db = _open_db()
    try:
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.agent2_memory_data = json.dumps(blob, ensure_ascii=False, default=str)
            db.commit()
        else:
            logger.warning(f"User {user_id} not found — agent2_memory not persisted")
    except Exception as e:
        logger.error(f"Failed to save agent2_memory for {user_id}: {e}")
        db.rollback()
    finally:
        db.close()


def sync_user_context(user_id: str, profile: dict | None, context: dict | None = None) -> None:
    _safe_user_id(user_id)
    context = context or {}
    memory = context.get("memory") or {}
    blob = _load_blob(user_id)
    blob["user_context"] = {
        "user_id": user_id,
        "source": "agent1_profile_and_career_context",
        "profile": profile or {},
        "identity": memory.get("identity") or memory.get("identity_context") or {},
        "ambitions": memory.get("ambitions") or memory.get("ambition_map") or {},
        "capabilities": memory.get("capabilities") or memory.get("capability_map") or {},
        "constraints": memory.get("constraints") or memory.get("constraint_map") or {},
        "preferences": memory.get("preferences") or memory.get("preference_map") or {},
        "progress_summary": context.get("progress_summary") or {},
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
    }
    _save_blob(user_id, blob)


def sync_current_week(user_id: str, context: dict | None = None, actions: list[dict] | None = None, reason: str = "") -> None:
    _safe_user_id(user_id)
    context = context or {}
    roadmap = context.get("roadmap") or {}
    weekly_focus = roadmap.get("weekly_focus") or {}
    current_actions = actions if actions is not None else weekly_focus.get("primary_actions") or []
    blob = _load_blob(user_id)
    blob["current_week"] = {
        "user_id": user_id,
        "week_number": context.get("week_number"),
        "current_week_started_at": context.get("current_week_started_at"),
        "phase_name": weekly_focus.get("phase_name"),
        "tasks": current_actions,
        "reason": reason or roadmap.get("last_replanned_reason") or "",
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
    }
    _save_blob(user_id, blob)


def append_progress_event(user_id: str, event: dict) -> None:
    _safe_user_id(user_id)
    event_type = str(event.get("event_type") or "")
    if event_type not in {
        "weekly_task_completed", "weekly_task_reopened", "weekly_task_skipped",
        "weekly_cycle_completed", "assistant_guidance",
    }:
        return
    blob = _load_blob(user_id)
    log = blob.get("progress_log") or []
    log.append({**event, "created_at": datetime.datetime.utcnow().isoformat() + "Z"})
    blob["progress_log"] = log[-200:]  # keep last 200
    _save_blob(user_id, blob)


def append_chat_turn(user_id: str, user_message: str, assistant_response: str, intent: str = "") -> None:
    _safe_user_id(user_id)
    blob = _load_blob(user_id)
    notes = blob.get("chat_notes") or []
    notes.append({
        "intent": intent,
        "user_message": user_message,
        "assistant_response": assistant_response,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    })
    blob["chat_notes"] = notes[-100:]  # keep last 100 turns
    _save_blob(user_id, blob)


def upsert_upcoming_event(user_id: str, event: dict) -> dict:
    _safe_user_id(user_id)
    blob = _load_blob(user_id)
    events_blob = blob.get("upcoming_events") or {"events": []}
    items = events_blob.get("events") if isinstance(events_blob, dict) else []
    event_id = event.get("id") or f"event-{len(items) + 1}"
    event = {**event, "id": event_id}
    updated = False
    merged = []
    for item in items:
        if item.get("id") == event_id:
            merged.append({**item, **event})
            updated = True
        else:
            merged.append(item)
    if not updated:
        merged.append(event)
    blob["upcoming_events"] = {"events": merged, "last_updated": datetime.datetime.utcnow().isoformat() + "Z"}
    _save_blob(user_id, blob)
    return event


def load_agent2_memory(user_id: str) -> dict[str, Any]:
    _safe_user_id(user_id)
    blob = _load_blob(user_id)
    return {
        "user_context": blob.get("user_context", {}),
        "upcoming_events": blob.get("upcoming_events", {"events": []}),
        "current_week": blob.get("current_week", {}),
        "chat_notes": blob.get("chat_notes", []),
    }


def active_blocking_events(user_id: str, today: datetime.date | None = None) -> list[dict]:
    today = today or datetime.date.today()
    events = load_agent2_memory(user_id).get("upcoming_events", {}).get("events", [])
    active = []
    for event in events:
        start_raw = event.get("start_date") or event.get("date")
        end_raw = event.get("end_date") or start_raw
        try:
            start = datetime.date.fromisoformat(str(start_raw))
            end = datetime.date.fromisoformat(str(end_raw))
        except Exception:
            continue
        if start <= today <= end and event.get("blocks_normal_work", True):
            active.append(event)
    return active


def memory_context_text(user_id: str) -> str:
    memory = load_agent2_memory(user_id)
    events = memory.get("upcoming_events", {}).get("events", [])
    week = memory.get("current_week", {})
    tasks = week.get("tasks") or []
    # Last 8 chat turns for in-prompt conversation context
    recent_turns = memory.get("chat_notes") or []
    event_lines = [
        f"- {event.get('title', 'Event')}: {event.get('start_date') or event.get('date')} to {event.get('end_date') or event.get('date')}; impact={event.get('impact', '')}"
        for event in events[-8:]
    ]
    task_lines = [
        f"- {task.get('title') or task.get('skill')}: {task.get('description') or task.get('detail') or ''}"
        for task in tasks
    ]
    turn_lines = []
    for turn in recent_turns[-12:]:
        turn_lines.append(f"User: {turn.get('user_message', '')[:300]}")
        turn_lines.append(f"Agent: {turn.get('assistant_response', '')[:400]}")

    parts = [
        "Agent 2 persistent memory:",
        f"Current week: week={week.get('week_number')} phase={week.get('phase_name')}",
        "Tasks this week:",
        *(task_lines or ["- none stored"]),
        "Upcoming events:",
        *(event_lines or ["- none stored"]),
    ]
    if turn_lines:
        parts += ["", "Recent conversation history (most recent last):"] + turn_lines

    return "\n".join(parts)
