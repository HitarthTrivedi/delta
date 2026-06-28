"""
User context documents for Agent 2. Two documents per user, stored as strings
inside the agent2_memory_data JSON blob (no extra DB columns needed).

DOCUMENT 1 — instructions_doc
  Sections (in order, top to bottom):
    PERMANENT INSTRUCTIONS  — firm rules that never auto-clear (carry every week)
    PRESENT WEEK REQUESTS   — adjustments/context for the current week only
    NEXT WEEK REQUESTS      — what the user wants included in next week's plan
    GENERAL Q&A             — course questions + answers logged this week

  After each week closes, an ===WEEK_END=== separator is inserted.
  Agent 2 reads only up to the FIRST occurrence of this marker — so old weeks
  are invisible to it without manual deletion.

DOCUMENT 2 — profile_doc
  Static identity info from intake + cumulative skills/projects/courses
  appended after each week closes.
"""

from __future__ import annotations

import datetime
import logging
import re

logger = logging.getLogger("delta.user_context_store")

WEEK_END_SEP = "===WEEK_END==="

_BLANK_INSTRUCTIONS = """\
# PERMANENT INSTRUCTIONS
(Firm rules that apply every week. Never change unless the user explicitly says so.)


# PRESENT WEEK REQUESTS
(Tasks, context, or adjustments for the current week only.)


# NEXT WEEK REQUESTS
(Things the user wants included in the next weekly plan.)


# GENERAL Q&A
(Course questions and agent answers logged this week.)

"""


# ── Blob helpers (reuse existing agent2_memory_data column) ──────────────────

def _load_blob(user_id: str) -> dict:
    import json
    from app.database import SessionLocal
    from app.models.user import User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.agent2_memory_data:
            return {}
        return json.loads(user.agent2_memory_data)
    except Exception as e:
        logger.error(f"[ctx_store] load error {user_id}: {e}")
        return {}
    finally:
        db.close()


def _save_blob(user_id: str, blob: dict) -> None:
    import json
    from app.database import SessionLocal
    from app.models.user import User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.agent2_memory_data = json.dumps(blob, ensure_ascii=False, default=str)
            db.commit()
    except Exception as e:
        logger.error(f"[ctx_store] save error {user_id}: {e}")
        db.rollback()
    finally:
        db.close()


def _get_instructions(user_id: str) -> str:
    return _load_blob(user_id).get("instructions_doc") or _BLANK_INSTRUCTIONS


def _set_instructions(user_id: str, doc: str) -> None:
    blob = _load_blob(user_id)
    blob["instructions_doc"] = doc
    _save_blob(user_id, blob)


# ── Read helpers ──────────────────────────────────────────────────────────────

def read_current_week_context(user_id: str) -> str:
    """Return only content above the first WEEK_END_SEP — the current week."""
    doc = _get_instructions(user_id)
    if WEEK_END_SEP in doc:
        return doc.split(WEEK_END_SEP)[0].strip()
    return doc.strip()


def read_profile_doc(user_id: str) -> str:
    return _load_blob(user_id).get("profile_doc") or ""


def _extract_bullets(doc: str, from_marker: str, to_markers: list[str]) -> list[str]:
    """Return bullet items between from_marker and the first matching to_marker."""
    if from_marker not in doc:
        return []
    start = doc.index(from_marker) + len(from_marker)
    end = len(doc)
    for m in to_markers:
        pos = doc.find(m, start)
        if pos != -1:
            end = min(end, pos)
    text = doc[start:end]
    return [ln.lstrip("- ").strip() for ln in text.splitlines() if ln.strip().startswith("-")]


def get_permanent_instructions(user_id: str) -> list[str]:
    doc = _get_instructions(user_id)
    return _extract_bullets(doc, "# PERMANENT INSTRUCTIONS", ["# PRESENT WEEK REQUESTS", WEEK_END_SEP])


def get_next_week_requests(user_id: str) -> list[dict]:
    """Return timed next-week requests as [{text, weeks_remaining}] from the JSON blob."""
    return _load_blob(user_id).get("timed_requests") or []


def _replace_bullets(doc: str, section_marker: str, next_marker: str, items: list[str]) -> str:
    """Replace bullet items in a section without touching comments or other sections."""
    if section_marker not in doc:
        return doc
    sec_start = doc.index(section_marker) + len(section_marker)
    if next_marker and next_marker in doc:
        sec_end = doc.index(next_marker, sec_start)
    else:
        sec_end = len(doc)
    # Preserve any parenthetical comment line at the top of the section
    raw = doc[sec_start:sec_end]
    comment = next((ln for ln in raw.splitlines() if ln.strip().startswith("(")), "")
    bullets = "\n".join(f"- {item}" for item in items)
    new_block = f"\n{comment}\n\n{bullets}\n\n" if comment else f"\n{bullets}\n\n"
    return doc[:sec_start] + new_block + doc[sec_end:]


def set_permanent_instructions(user_id: str, items: list[str]) -> None:
    doc = _get_instructions(user_id)
    doc = _replace_bullets(doc, "# PERMANENT INSTRUCTIONS", "# PRESENT WEEK REQUESTS", items)
    _set_instructions(user_id, doc)


def set_next_week_requests(user_id: str, items: list[dict]) -> None:
    """Save timed next-week requests [{text, weeks_remaining}] to JSON blob + sync to text doc."""
    blob = _load_blob(user_id)
    blob["timed_requests"] = [{"text": i.get("text", ""), "weeks_remaining": int(i.get("weeks_remaining", i.get("weeks", 1)))} for i in items if i.get("text", "").strip()]
    _sync_timed_requests_to_doc(blob)
    _save_blob(user_id, blob)


def _sync_timed_requests_to_doc(blob: dict) -> None:
    """Write timed_requests back into the instructions_doc text so Agent 2 can read them."""
    doc = blob.get("instructions_doc") or _BLANK_INSTRUCTIONS
    items = blob.get("timed_requests") or []
    # _replace_bullets adds "- " prefix, so pass bare text with the [Xw] tag
    text_items = [f"[{r['weeks_remaining']}w] {r['text']}" for r in items]
    doc = _replace_bullets(doc, "# NEXT WEEK REQUESTS", "# GENERAL Q&A", text_items)
    blob["instructions_doc"] = doc


# ── Write helpers — instructions_doc ─────────────────────────────────────────

def _insert_before_marker(doc: str, before_marker: str, entry: str) -> str:
    """Insert `entry` on a new line just before `before_marker` in `doc`."""
    if before_marker in doc:
        idx = doc.index(before_marker)
        return doc[:idx].rstrip() + "\n" + entry + "\n\n" + doc[idx:]
    return doc.rstrip() + "\n" + entry + "\n"


def append_permanent_instruction(user_id: str, text: str) -> None:
    doc = _get_instructions(user_id)
    entry = f"- {text}"
    doc = _insert_before_marker(doc, "# PRESENT WEEK REQUESTS", entry)
    _set_instructions(user_id, doc)


def append_next_week_request(user_id: str, text: str, weeks: int = 1) -> None:
    blob = _load_blob(user_id)
    items = blob.get("timed_requests") or []
    items.append({"text": text.strip(), "weeks_remaining": max(1, int(weeks))})
    blob["timed_requests"] = items
    _sync_timed_requests_to_doc(blob)
    _save_blob(user_id, blob)


def append_present_session(user_id: str, text: str) -> None:
    doc = _get_instructions(user_id)
    entry = f"- {text}"
    doc = _insert_before_marker(doc, "# NEXT WEEK REQUESTS", entry)
    _set_instructions(user_id, doc)


def append_qa(user_id: str, question: str, answer: str) -> None:
    doc = _get_instructions(user_id)
    entry = f"\nQ: {question[:300]}\nA: {answer[:800]}"
    sep_pos = doc.find(WEEK_END_SEP)
    if sep_pos != -1:
        doc = doc[:sep_pos].rstrip() + entry + "\n\n" + doc[sep_pos:]
    else:
        doc = doc.rstrip() + entry + "\n"
    _set_instructions(user_id, doc)


# ── Week transition ───────────────────────────────────────────────────────────

def promote_next_week_requests(user_id: str) -> None:
    """
    Called at the START of a new weekly cycle.
    Decrements weeks_remaining on timed requests, promotes active ones, expires finished ones.
    """
    blob = _load_blob(user_id)
    items = blob.get("timed_requests") or []
    if not items:
        return

    active, to_promote = [], []
    for item in items:
        remaining = int(item.get("weeks_remaining", 1)) - 1
        if remaining > 0:
            active.append({"text": item["text"], "weeks_remaining": remaining})
            to_promote.append(item["text"])
        else:
            to_promote.append(item["text"])  # last active week — include once then expire

    blob["timed_requests"] = active
    _sync_timed_requests_to_doc(blob)

    # Also promote text into PRESENT WEEK REQUESTS
    if to_promote:
        doc = blob.get("instructions_doc") or _BLANK_INSTRUCTIONS
        present_marker = "# PRESENT WEEK REQUESTS"
        next_marker = "# NEXT WEEK REQUESTS"
        if present_marker in doc and next_marker in doc:
            present_start = doc.index(present_marker) + len(present_marker)
            present_end = doc.index(next_marker)
            present_raw = doc[present_start:present_end].strip()
            new_items = "\n".join(f"- {t}" for t in to_promote)
            doc = (
                doc[:present_start].rstrip() + "\n"
                + (present_raw + "\n" if present_raw else "")
                + new_items + "\n\n"
                + doc[present_end:]
            )
            blob["instructions_doc"] = doc

    _save_blob(user_id, blob)


def end_week(user_id: str, week_label: str) -> None:
    """
    Called at the START of a new weekly cycle (after promoting next-week requests).
    Archives current-week sections below WEEK_END_SEP, resets them for the new week.
    PERMANENT INSTRUCTIONS are preserved at the top.
    """
    doc = _get_instructions(user_id)
    perm_marker = "# PERMANENT INSTRUCTIONS"
    present_marker = "# PRESENT WEEK REQUESTS"

    if perm_marker in doc and present_marker in doc:
        perm_end = doc.index(present_marker)
        permanent_block = doc[:perm_end]
        archived = doc[perm_end:].strip()
    else:
        permanent_block = ""
        archived = doc.strip()

    new_doc = (
        permanent_block.rstrip() + "\n\n"
        "# PRESENT WEEK REQUESTS\n"
        "(Tasks, context, or adjustments for the current week only.)\n\n\n"
        "# NEXT WEEK REQUESTS\n"
        "(Things the user wants included in the next weekly plan.)\n\n\n"
        "# GENERAL Q&A\n"
        "(Course questions and agent answers logged this week.)\n\n"
        f"{WEEK_END_SEP}\n"
        f"# {week_label} — ARCHIVED\n"
        f"{archived}\n"
    )
    _set_instructions(user_id, new_doc)


# ── Profile document ──────────────────────────────────────────────────────────

def initialize_profile_doc(user_id: str, profile: dict, user_obj=None) -> None:
    """Build or rebuild the profile doc from Agent 1 intake data."""
    name = (getattr(user_obj, "name", None) or profile.get("name") or "User")
    role = (getattr(user_obj, "target_role", None) or profile.get("target_role") or profile.get("domain") or "")
    major = profile.get("major") or ""
    university = profile.get("university") or profile.get("college") or ""
    study_year = profile.get("study_year") or profile.get("year_of_study") or ""
    hours = profile.get("hours_per_week") or profile.get("weekly_hours") or ""
    horizon = profile.get("planning_horizon") or ""
    skill_level = profile.get("skill_level") or ""

    skills_raw = profile.get("skills") or {}
    if isinstance(skills_raw, dict):
        skill_lines = "\n".join(f"- {k}: {v}/10 (self-assessed)" for k, v in skills_raw.items())
    elif isinstance(skills_raw, list):
        skill_lines = "\n".join(f"- {s}" for s in skills_raw)
    else:
        skill_lines = "- Not specified"

    doc = f"""# USER PROFILE — {name}
Last updated: Intake

## Identity
- Name: {name}
- Target Role: {role}
- Major: {major}
- University / College: {university}
- Study Year: {study_year}
- Hours/Week Available: {hours}
- Planning Horizon: {horizon}
- Self-assessed Skill Level: {skill_level}

## Current Skills (from intake)
{skill_lines}

## Completed Journey
(Completed tasks and proofs are added here as each week closes.)

## Projects Built
(Project tasks are logged here after completion.)

## Courses / Resources Used
(Course tasks are logged here after completion.)
"""
    blob = _load_blob(user_id)
    blob["profile_doc"] = doc
    _save_blob(user_id, blob)


def update_profile_with_completed_tasks(user_id: str, completed_tasks: list[dict], week_label: str) -> None:
    """Append completed tasks from a closed week into the profile doc sections."""
    blob = _load_blob(user_id)
    doc = blob.get("profile_doc") or ""
    if not doc:
        return

    journey_entries, project_entries, course_entries = [], [], []
    for task in completed_tasks:
        title = task.get("title") or task.get("skill") or ""
        ttype = (task.get("type") or "").lower()
        if "course" in ttype or "resource" in ttype:
            course_entries.append(f"- [{week_label}] {title}")
        elif "project" in ttype or "proof" in title.lower():
            project_entries.append(f"- [{week_label}] {title}")
        else:
            journey_entries.append(f"- [{week_label}] {title}")

    def _insert_after(doc: str, marker: str, entries: list[str]) -> str:
        if marker in doc and entries:
            idx = doc.index(marker) + len(marker)
            doc = doc[:idx] + "\n" + "\n".join(entries) + doc[idx:]
        return doc

    doc = _insert_after(doc, "## Completed Journey", journey_entries)
    doc = _insert_after(doc, "## Projects Built", project_entries)
    doc = _insert_after(doc, "## Courses / Resources Used", course_entries)
    doc = re.sub(r"Last updated: .*", f"Last updated: {week_label}", doc, count=1)

    blob["profile_doc"] = doc
    _save_blob(user_id, blob)
