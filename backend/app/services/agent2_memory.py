"""Persistent file memory for Agent 2 weekly tutoring and planning."""

from __future__ import annotations

import datetime
import json
import pathlib
import re
from typing import Any


BASE_DIR = pathlib.Path(__file__).resolve().parents[3] / "data" / "agent2_memory"


def _safe_user_id(user_id: str) -> str:
    user_id = str(user_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", user_id):
        raise ValueError("Invalid user_id.")
    return user_id


def _user_dir(user_id: str) -> pathlib.Path:
    path = BASE_DIR / _safe_user_id(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path(user_id: str, filename: str) -> pathlib.Path:
    return _user_dir(user_id) / filename


def _read_json(user_id: str, filename: str, fallback):
    path = _path(user_id, filename)
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write_json(user_id: str, filename: str, data) -> None:
    payload = {
        **data,
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
    } if isinstance(data, dict) else data
    _path(user_id, filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _append_jsonl(user_id: str, filename: str, data: dict) -> None:
    payload = {
        **data,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    with _path(user_id, filename).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def sync_user_context(user_id: str, profile: dict | None, context: dict | None = None) -> None:
    context = context or {}
    memory = context.get("memory") or {}
    payload = {
        "user_id": user_id,
        "source": "agent1_profile_and_career_context",
        "profile": profile or {},
        "identity": memory.get("identity") or memory.get("identity_context") or {},
        "ambitions": memory.get("ambitions") or memory.get("ambition_map") or {},
        "capabilities": memory.get("capabilities") or memory.get("capability_map") or {},
        "constraints": memory.get("constraints") or memory.get("constraint_map") or {},
        "preferences": memory.get("preferences") or memory.get("preference_map") or {},
        "progress_summary": context.get("progress_summary") or {},
    }
    _write_json(user_id, "user_context.json", payload)


def sync_current_week(user_id: str, context: dict | None = None, actions: list[dict] | None = None, reason: str = "") -> None:
    context = context or {}
    roadmap = context.get("roadmap") or {}
    weekly_focus = roadmap.get("weekly_focus") or {}
    current_actions = actions if actions is not None else weekly_focus.get("primary_actions") or []
    payload = {
        "user_id": user_id,
        "week_number": context.get("week_number"),
        "current_week_started_at": context.get("current_week_started_at"),
        "phase_name": weekly_focus.get("phase_name"),
        "tasks": current_actions,
        "reason": reason or roadmap.get("last_replanned_reason") or "",
    }
    _write_json(user_id, "current_week.json", payload)


def append_progress_event(user_id: str, event: dict) -> None:
    event_type = str(event.get("event_type") or "")
    if event_type in {
        "weekly_task_completed",
        "weekly_task_reopened",
        "weekly_task_skipped",
        "weekly_cycle_completed",
        "assistant_guidance",
    }:
        _append_jsonl(user_id, "progress_log.jsonl", event)


def append_chat_turn(user_id: str, user_message: str, assistant_response: str, intent: str = "") -> None:
    _append_jsonl(user_id, "chat_notes.jsonl", {
        "intent": intent,
        "user_message": user_message,
        "assistant_response": assistant_response,
    })


def upsert_upcoming_event(user_id: str, event: dict) -> dict:
    events = _read_json(user_id, "upcoming_events.json", {"events": []})
    items = events.get("events") if isinstance(events, dict) else []
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
    _write_json(user_id, "upcoming_events.json", {"events": merged})
    return event


def load_agent2_memory(user_id: str) -> dict[str, Any]:
    return {
        "user_context": _read_json(user_id, "user_context.json", {}),
        "upcoming_events": _read_json(user_id, "upcoming_events.json", {"events": []}),
        "current_week": _read_json(user_id, "current_week.json", {}),
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
    event_lines = [
        f"- {event.get('title', 'Event')}: {event.get('start_date') or event.get('date')} to {event.get('end_date') or event.get('date')}; impact={event.get('impact', '')}"
        for event in events[-8:]
    ]
    task_lines = [
        f"- {task.get('title') or task.get('skill')}: {task.get('description') or task.get('detail') or ''}"
        for task in tasks
    ]
    return "\n".join([
        "Agent 2 persistent memory:",
        f"Current week file: week={week.get('week_number')} phase={week.get('phase_name')}",
        "Current week tasks:",
        *(task_lines or ["- none stored"]),
        "Upcoming events:",
        *(event_lines or ["- none stored"]),
    ])
