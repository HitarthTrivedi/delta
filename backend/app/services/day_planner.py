"""
day_planner.py — Distribute a week's Delta tasks across 7 concrete days.

Used when a user picks the "day" plan style. The distribution is proposed by
Groq (via ai_service.quality_model, which auto-falls back to gemma) and then
passed through a deterministic repair pass so the output is ALWAYS structurally
valid regardless of what the model returns:

  - every week task appears on at least one day (never silently dropped),
  - multi-item tasks are sliced into daily bites ("solve 4 problems" -> "do any
    1 of 4 today") when the title implies a count,
  - days with no Delta task become free days (naturally when tasks < 7),
  - the user's own recurring commitments are attached as per-day reminders.
"""
from __future__ import annotations

import datetime
import logging
import math
import re

logger = logging.getLogger("delta.day_planner")

_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_WEEKDAY_LABEL = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
    "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
}
_FREE_NOTE = "Free from Delta tasks — use today for your own commitments."


def _action_id(a: dict) -> str:
    return str(a.get("id") or a.get("title") or "").strip().lower()


def _detect_count(action: dict) -> int:
    """Leading small integer in a task title implies it can be split (e.g.
    'Solve 4 LeetCode problems' -> 4). Returns 1 when nothing splittable."""
    text = f"{action.get('title', '')}"
    for match in re.findall(r"\b(\d{1,2})\b", text):
        n = int(match)
        if 2 <= n <= 14:
            return n
    return 1


def _cadence_days(cadence: str) -> list[str]:
    """Map a free-text cadence ('Mon/Wed', 'daily 30m', 'weekends') to weekday keys."""
    c = (cadence or "").lower()
    if "daily" in c or "every day" in c or "everyday" in c:
        return list(_WEEKDAYS)
    if "weekend" in c:
        return ["sat", "sun"]
    if "weekday" in c:
        return ["mon", "tue", "wed", "thu", "fri"]
    hits = [d for d in _WEEKDAYS if d in c or _WEEKDAY_LABEL[d].lower() in c]
    return hits


def _init_days(week_start: datetime.datetime, day_schedule: dict) -> list[dict]:
    """Build 7 day slots seeded with per-day availability and personal reminders."""
    day_schedule = day_schedule or {}
    per_hours = day_schedule.get("per_day_hours") or {}
    days = []
    for i in range(7):
        d = week_start + datetime.timedelta(days=i)
        key = _WEEKDAYS[d.weekday()]
        hours = per_hours.get(key)
        days.append({
            "date": d.date().isoformat(),
            "weekday": key,
            "label": _WEEKDAY_LABEL[key],
            # No per-day hours configured => treat every day as available.
            "hours": float(hours) if hours is not None else None,
            "delta_tasks": [],
            "personal": [],
            "is_free": False,
        })

    # Fixed commitments (college/work) and recurring personal tasks -> reminders.
    for item in day_schedule.get("fixed") or []:
        label = (item.get("label") or "").strip()
        if not label:
            continue
        for key in (item.get("days") or []):
            for day in days:
                if day["weekday"] == str(key).strip().lower():
                    day["personal"].append(label)
    for item in day_schedule.get("recurring") or []:
        label = (item.get("label") or "").strip()
        if not label:
            continue
        matched = _cadence_days(item.get("cadence") or "")
        target = matched or [days[0]["weekday"]]  # unclear cadence -> first day
        cadence_txt = (item.get("cadence") or "").strip()
        note = f"{label}" + (f" ({cadence_txt})" if cadence_txt and not matched else "")
        for day in days:
            if day["weekday"] in target:
                day["personal"].append(note)
    return days


def _available_indexes(days: list[dict]) -> list[int]:
    """Days the user can do Delta work on: those with hours > 0, else all days."""
    idx = [i for i, d in enumerate(days) if d["hours"] is None or d["hours"] > 0]
    return idx or list(range(len(days)))


def _assign(days: list[dict], actions: list[dict]) -> None:
    """Deterministically place every task on a day: round-robin over the days the
    user can actually work, splitting multi-item tasks into daily bites. This is the
    guaranteed structural layer — no task is ever dropped and counts are always split."""
    available = _available_indexes(days)
    cursor = 0

    def _place(day_idx: int, action: dict, note: str) -> None:
        days[day_idx]["delta_tasks"].append({
            "id": action.get("id") or _action_id(action),
            "title": action.get("title") or "Task",
            "note": note,
        })

    for action in actions:
        count = _detect_count(action)
        if count >= 2:
            spread = min(count, len(available))
            per = max(1, round(count / spread))
            for _ in range(spread):
                day_idx = available[cursor % len(available)]
                cursor += 1
                _place(day_idx, action, f"Do any {per} of {count} today")
        else:
            day_idx = available[cursor % len(available)]
            cursor += 1
            _place(day_idx, action, action.get("title") or "Task")


def _llm_day_focus(days: list[dict], day_schedule: dict) -> dict:
    """Ask Groq for one short, motivating focus line per day given what's scheduled.
    Purely additive polish on top of the deterministic structure — returns {index: line}
    or {} on any failure (Groq off, rate-limited, malformed)."""
    working = [i for i, d in enumerate(days) if d["delta_tasks"]]
    if not working:
        return {}
    try:
        from app.services.ai_service import generate_json, quality_model
    except Exception:
        return {}

    day_lines = "\n".join(
        f"{i} ({d['label']}): tasks=[{', '.join(t['title'] for t in d['delta_tasks'])}]"
        + (f" personal=[{', '.join(d['personal'])}]" if d["personal"] else "")
        for i, d in enumerate(days) if d["delta_tasks"]
    )
    prompt = (
        "For each listed day, write ONE short, concrete focus line (max 12 words) that "
        "frames that day's Delta tasks around the person's other commitments. Be practical, "
        "not fluffy.\n\n"
        f"{day_lines}\n\n"
        'Return ONLY JSON: {"focus": {"<day index>": "line", ...}}'
    )
    try:
        raw = generate_json(prompt, temperature=0.5, model=quality_model())
    except Exception as exc:
        logger.warning("day-plan focus generation failed: %s", type(exc).__name__)
        return {}

    focus = (raw or {}).get("focus") if isinstance(raw, dict) else None
    out: dict = {}
    for key, line in (focus or {}).items():
        try:
            idx = int(key)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(days) and str(line).strip():
            out[idx] = str(line).strip()[:120]
    return out


def _finalize(days: list[dict]) -> None:
    for day in days:
        if not day["delta_tasks"]:
            day["is_free"] = True
            if not day["personal"]:
                day["personal"] = [_FREE_NOTE]


def build_day_plan(week_actions: list[dict], day_schedule: dict, week_start: datetime.datetime) -> dict:
    """Return {"days": [...7 day slots...]} distributing the week's tasks.

    The distribution + splitting + free days are guaranteed deterministically; Groq
    only layers a short per-day focus line on top (best-effort)."""
    days = _init_days(week_start, day_schedule or {})
    actions = [a for a in (week_actions or []) if a.get("id") or a.get("title")]
    _assign(days, actions)
    focus = _llm_day_focus(days, day_schedule or {})
    for idx, line in focus.items():
        days[idx]["focus"] = line
    _finalize(days)
    return {
        "days": days,
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "task_count": len(actions),
        "source": "groq-enhanced" if focus else "deterministic",
    }
