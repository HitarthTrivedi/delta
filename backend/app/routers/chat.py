from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import datetime
import json
import logging
import re
import uuid

logger = logging.getLogger("delta.chat")

from app.database import get_db
from app.services.cache import cached
from app.models import JourneyEvent, PersonalizationProfile, RoadmapState, SkillNode, User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    OnboardingFinalizeRequest,
    OnboardingFinalizeResponse,
    OnboardingStartRequest,
    OnboardingStartResponse,
)
from app.services.central_engine import (
    compile_career_context,
    initialize_career_os_for_user,
    log_journey_event,
    run_weekly_career_cycle,
    serialize_journey_event,
)
from app.services.onboarding_pipeline import finalize_onboarding, start_onboarding
from app.services.profile_store import profile_as_context_string, load_profile
from app.services.agent2_memory import (
    append_chat_turn,
    append_progress_event,
    load_agent2_memory,
    memory_context_text,
    sync_current_week,
    sync_user_context,
    upsert_upcoming_event,
)
from app.limiter import limiter
from app.dependencies.auth import require_owner, verify_resource_owner

router = APIRouter(prefix="/api/chat", tags=["chat"])

WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

MONTH_INDEX = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _as_json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _extract_updated_actions(response_text: str) -> tuple[str, list[dict] | None]:
    """Extract the last JSON object/array from an LLM response without losing prose."""
    if not response_text:
        return "", None

    from app.services.ai_service import sanitize_llm_json_text

    blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", response_text, flags=re.IGNORECASE)
    candidates = blocks + [response_text.strip()]
    for candidate in reversed(candidates):
        text = sanitize_llm_json_text(candidate.strip())
        try:
            parsed = json.loads(text)
        except Exception:
            match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])\s*$", text)
            if not match:
                continue
            try:
                parsed = json.loads(match.group(1))
            except Exception:
                continue

        if isinstance(parsed, dict):
            actions = parsed.get("updated_actions") or parsed.get("primary_actions")
        else:
            actions = parsed
        if isinstance(actions, list):
            cleaned = response_text
            for block in blocks:
                cleaned = cleaned.replace(f"```json\n{block}\n```", "").replace(f"```\n{block}\n```", "")
            cleaned = re.sub(r"```(?:json)?\s*[\s\S]*?```", "", cleaned, flags=re.IGNORECASE).strip()
            if cleaned.startswith("{") or cleaned.startswith("["):
                cleaned = "I updated this week's tasks from your instruction."
            return cleaned, actions
    return response_text.strip(), None


def _action_source(action: dict) -> str:
    source = action.get("source") or action.get("platform") or ""
    url = action.get("url") or action.get("resource_url") or ""
    if source and url:
        return f"{source}: {url}"
    return source or url or "No external source attached."


def _split_skills(profile: dict) -> list[str]:
    skills = profile.get("skills") or []
    if isinstance(skills, str):
        skills = [part.strip() for part in skills.split(",") if part.strip()]
    return [str(skill).strip() for skill in skills if str(skill).strip()]


def _domain_from_profile(profile: dict, user: User | None = None) -> str:
    text = " ".join([
        str(profile.get("target_role", "")),
        str(profile.get("major", "")),
        str(profile.get("past_experience", "")),
        " ".join(_split_skills(profile)),
        str(user.target_role if user else ""),
    ]).lower()
    domain_markers = [
        ("ai_agents", ["multi-agent", "multi agent", "agentic rag", "adversarial ai", "llm orchestration", "agent routing", "alpha.kore"]),
        ("commerce", ["commerce", "finance", "accounting", "business", "marketing", "economics", "audit", "tax", "sales"]),
        ("mechanical", ["mechanical", "cad", "solidworks", "autocad", "thermodynamics", "manufacturing", "ansys"]),
        ("electrical", ["electrical", "electronics", "circuit", "pcb", "arduino", "matlab", "power systems", "embedded", "iot"]),
        ("arts", ["arts", "design", "fine arts", "illustration", "animation", "writing", "music", "film", "portfolio"]),
    ]
    scores = {domain: sum(1 for marker in markers if marker in text) for domain, markers in domain_markers}
    best = max(scores, key=scores.get)
    return best if scores[best] else "general"


def _advanced_actions(profile: dict, user: User | None, difficulty: str = "tough") -> list[dict]:
    domain = _domain_from_profile(profile, user)
    project_context = profile.get("past_experience") or "your previous work"
    if difficulty == "normal":
        return [
            {
                "id": f"task-{domain}-audit",
                "type": "project",
                "title": "Audit one previous piece of work",
                "skill": "Applied Review",
                "description": f"Use {project_context}. Pick one existing project/work sample, list 3 strengths, 3 weak points, and one improvement you can finish this week.",
                "source": "Your existing project/resume work",
                "url": "",
            },
            {
                "id": f"task-{domain}-proof-note",
                "type": "project",
                "title": "Write a proof note for one upgraded skill",
                "skill": "Technical Communication",
                "description": "Create a short note with goal, method, output, one mistake, and one improvement. Keep it easy enough for this week.",
                "source": "Your existing portfolio/resume",
                "url": "",
            },
        ]
    templates = {
        "ai_agents": [
            {
                "id": "task-agent-memory-eval",
                "type": "project",
                "title": "Build a memory-quality evaluation for your agent system",
                "skill": "Long-Term Memory Systems",
                "description": f"Use {project_context}. Create 8-10 test prompts and score whether the agent remembers, forgets, and retrieves correctly.",
                "source": "Your existing Alpha.Kore / agentic systems work",
                "url": "",
            },
            {
                "id": "task-adversarial-agent-redteam",
                "type": "project",
                "title": "Red-team one agent workflow against prompt attacks",
                "skill": "Adversarial AI Architecture",
                "description": "Write 6 adversarial prompts, run them against one workflow, record failures, then add one guardrail or scoring rule.",
                "source": "OWASP LLM risk style practice",
                "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
            },
        ],
        "commerce": [
            {
                "id": "task-commerce-dashboard",
                "type": "project",
                "title": "Build a financial decision dashboard",
                "skill": "Financial Analysis",
                "description": f"Use {project_context}. Create a simple dashboard with revenue, cost, margin, and one recommendation.",
                "source": "Your existing commerce/business context",
                "url": "",
            },
            {
                "id": "task-commerce-case-study",
                "type": "project",
                "title": "Write a business case study with numbers",
                "skill": "Business Strategy",
                "description": "Pick one company, show 3 data points, identify one problem, and write one recommendation with risk.",
                "source": "Company reports / public business data",
                "url": "",
            },
        ],
        "mechanical": [
            {
                "id": "task-mech-cad-redesign",
                "type": "project",
                "title": "Redesign one mechanical part with trade-offs",
                "skill": "Mechanical Design",
                "description": f"Use {project_context}. Model/sketch one part, improve one constraint, and explain the trade-off.",
                "source": "Your existing CAD/mechanical work",
                "url": "",
            },
            {
                "id": "task-mech-analysis-note",
                "type": "project",
                "title": "Create a mechanism analysis note",
                "skill": "Mechanical Analysis",
                "description": "Pick one mechanism, calculate one load/speed/thermal constraint, and explain the design choice.",
                "source": "Engineering notes / CAD model",
                "url": "",
            },
        ],
        "electrical": [
            {
                "id": "task-electrical-sim",
                "type": "project",
                "title": "Simulate and explain one circuit",
                "skill": "Circuit Analysis",
                "description": f"Use {project_context}. Simulate one circuit, record behavior, and explain one limit or failure.",
                "source": "Falstad Circuit Simulator",
                "url": "https://www.falstad.com/circuit/",
            },
            {
                "id": "task-electrical-test-plan",
                "type": "project",
                "title": "Write a test plan for one electrical system",
                "skill": "Testing and Debugging",
                "description": "List 6 tests, expected readings, likely faults, and how you would debug one failed test.",
                "source": "Your existing electronics/IoT work",
                "url": "",
            },
        ],
        "arts": [
            {
                "id": "task-arts-case-study",
                "type": "project",
                "title": "Turn one artwork into a portfolio case study",
                "skill": "Portfolio Development",
                "description": f"Use {project_context}. Show goal, references, drafts, final piece, and what changed after critique.",
                "source": "Your existing arts/design portfolio",
                "url": "",
            },
            {
                "id": "task-arts-style-study",
                "type": "project",
                "title": "Create a focused style study",
                "skill": "Creative Direction",
                "description": "Choose one style, make a small piece, then write 5 critique notes and 3 improvements.",
                "source": "Portfolio/reference study",
                "url": "",
            },
        ],
    }
    return templates.get(domain, [
        {
            "id": "task-general-proof",
            "type": "project",
            "title": "Upgrade one previous work sample",
            "skill": "Applied Proof",
            "description": f"Use {project_context}. Choose one previous work sample, make it stronger, and write what improved.",
            "source": "Your existing resume/portfolio",
            "url": "",
        }
    ])


def _course_action(profile: dict, user: User | None = None, requested_topic: str = "") -> dict:
    domain = _domain_from_profile(profile, user)
    if domain == "ai_agents" and ("hugging" in requested_topic or "open source" in requested_topic):
        return {
            "id": "course-huggingface-agents",
            "type": "course",
            "title": "Complete one focused section of the Hugging Face Agents Course",
            "skill": "AI Agents",
            "description": "Do only one section this week. Notes required: what tool use is, how the agent decides actions, and one idea you can apply in Alpha.Kore.",
            "source": "Hugging Face",
            "url": "https://huggingface.co/learn/agents-course",
            "duration": "1 week section",
        }
    course_map = {
        "ai_agents": {
        "id": "course-deeplearningai-langgraph",
        "type": "course",
        "title": "Complete DeepLearning.AI's AI Agents in LangGraph course",
        "skill": "AI Agents / LangGraph",
        "description": "Watch the course, then write a small comparison: what LangGraph gives you that your current agent routing does not.",
        "source": "DeepLearning.AI",
        "url": "https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/",
        "duration": "1 week",
        },
        "commerce": {
            "id": "course-khan-accounting-finance",
            "type": "course",
            "title": "Complete one focused Khan Academy finance/accounting unit",
            "skill": "Finance / Accounting",
            "description": "Do one unit this week and make a one-page summary with formulas, example, and business use.",
            "source": "Khan Academy",
            "url": "https://www.khanacademy.org/economics-finance-domain",
            "duration": "1 week unit",
        },
        "mechanical": {
            "id": "course-autodesk-fusion-learning",
            "type": "course",
            "title": "Complete one Autodesk Fusion learning module",
            "skill": "CAD / Mechanical Design",
            "description": "Do one module this week and submit one model/screenshot plus a note explaining design constraints.",
            "source": "Autodesk",
            "url": "https://www.autodesk.com/learn",
            "duration": "1 week module",
        },
        "electrical": {
            "id": "course-allaboutcircuits",
            "type": "course",
            "title": "Complete one All About Circuits textbook chapter",
            "skill": "Circuit Fundamentals",
            "description": "Read one chapter, solve 3 examples, and simulate one circuit from it.",
            "source": "All About Circuits",
            "url": "https://www.allaboutcircuits.com/textbook/",
            "duration": "1 week chapter",
        },
        "arts": {
            "id": "course-khan-art-history",
            "type": "course",
            "title": "Complete one Khan Academy art history unit",
            "skill": "Visual Analysis",
            "description": "Do one unit this week and write a short critique connecting the style to your own portfolio.",
            "source": "Khan Academy",
            "url": "https://www.khanacademy.org/humanities/art-history",
            "duration": "1 week unit",
        },
        "general": {
            "id": "course-coursera-learning-how-to-learn",
            "type": "course",
            "title": "Complete one section of Learning How to Learn",
            "skill": "Learning Strategy",
            "description": "Do one section and write a short plan for applying it to your current weekly work.",
            "source": "Coursera",
            "url": "https://www.coursera.org/learn/learning-how-to-learn",
            "duration": "1 week section",
        },
    }
    return course_map.get(domain, course_map["general"])


def _latest_task_states(journey: list[dict], current_week_started_at=None) -> dict:
    states = {}
    for event in sorted(journey, key=lambda e: str(e.get("created_at") or "")):
        if current_week_started_at and event.get("created_at") and str(event.get("created_at")) < str(current_week_started_at):
            continue
        event_type = event.get("event_type")
        if event_type not in {"weekly_task_completed", "weekly_task_reopened", "weekly_task_skipped"}:
            continue
        evidence = event.get("evidence") or {}
        task_id = str(evidence.get("id") or evidence.get("title") or event.get("id"))
        states[task_id] = event_type
    return states


def _has_active_course(actions: list[dict], career_context: dict) -> dict | None:
    states = _latest_task_states(
        career_context.get("journey_until_today") or [],
        career_context.get("current_week_started_at"),
    )
    for action in actions:
        task_id = str(action.get("id") or action.get("title"))
        if action.get("type") == "course" and states.get(task_id) not in {"weekly_task_completed", "weekly_task_skipped"}:
            return action
    return None


def _format_action_bullets(actions: list[dict]) -> str:
    if not actions:
        return "No active task is saved yet."
    lines = []
    for index, action in enumerate(actions, start=1):
        lines.append(
            f"{index}. {action.get('title', 'Task')}: "
            f"{action.get('description') or action.get('detail') or 'No description saved.'}"
        )
    return "\n".join(lines)


def _save_weekly_actions(db: Session, roadmap: RoadmapState, actions: list[dict], phase_name: str):
    weekly_focus = _as_json(roadmap.weekly_focus, {})
    # Back up the tasks we are about to overwrite so the user can undo/restore them.
    existing = weekly_focus.get("primary_actions") or []
    if existing and existing != actions:
        weekly_focus["previous_actions"] = existing
        weekly_focus["previous_phase_name"] = weekly_focus.get("phase_name")
    weekly_focus["phase_name"] = phase_name
    weekly_focus["primary_actions"] = actions
    # Lock it: this list is what Agent 2 decided, so context-reload must NOT regenerate over it.
    weekly_focus["manual"] = True
    roadmap.weekly_focus = json.dumps(weekly_focus)
    db.commit()
    db.refresh(roadmap)


def _current_actions_from_roadmap(roadmap: RoadmapState | None) -> list[dict]:
    if not roadmap:
        return []
    weekly_focus = _as_json(roadmap.weekly_focus, {})
    actions = weekly_focus.get("primary_actions") or []
    return actions if isinstance(actions, list) else []


def _now_local() -> datetime.datetime:
    return datetime.datetime.now().astimezone()


def _today_local() -> datetime.date:
    return _now_local().date()


def _next_weekday(today: datetime.date, weekday: int, include_today: bool = False) -> datetime.date:
    days = (weekday - today.weekday()) % 7
    if days == 0 and not include_today:
        days = 7
    return today + datetime.timedelta(days=days)


def _safe_date(year: int, month: int, day: int) -> datetime.date | None:
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def _parse_date_reference(text: str, today: datetime.date | None = None) -> dict:
    today = today or _today_local()
    lowered = text.lower()
    candidates: list[tuple[datetime.date, str]] = []
    time_match = re.search(r"\b(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lowered)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        marker = time_match.group(3)
        if marker == "pm" and hour != 12:
            hour += 12
        if marker == "am" and hour == 12:
            hour = 0
        mentioned_time = f"{hour:02d}:{minute:02d}"
        mentioned_time_source = time_match.group(0)
    else:
        time24 = re.search(r"\b(?:at\s*)?([01]?\d|2[0-3]):([0-5]\d)\b", lowered)
        mentioned_time = f"{int(time24.group(1)):02d}:{int(time24.group(2)):02d}" if time24 else None
        mentioned_time_source = time24.group(0) if time24 else None

    if re.search(r"\btoday\b", lowered):
        candidates.append((today, "today"))
    if re.search(r"\btomorrow\b", lowered):
        candidates.append((today + datetime.timedelta(days=1), "tomorrow"))
    if re.search(r"\bday after tomorrow\b", lowered):
        candidates.append((today + datetime.timedelta(days=2), "day after tomorrow"))

    relative = re.search(r"\b(?:in|after)\s+(\d{1,3})\s+(day|days|week|weeks|month|months)\b", lowered)
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        if unit.startswith("day"):
            delta_days = amount
        elif unit.startswith("week"):
            delta_days = amount * 7
        else:
            delta_days = amount * 30
        candidates.append((today + datetime.timedelta(days=delta_days), relative.group(0)))

    iso = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", lowered)
    if iso:
        parsed = _safe_date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        if parsed:
            candidates.append((parsed, iso.group(0)))

    slash = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?\b", lowered)
    if slash and not iso:
        day = int(slash.group(1))
        month = int(slash.group(2))
        year = int(slash.group(3) or today.year)
        parsed = _safe_date(year, month, day)
        if parsed and parsed < today and slash.group(3) is None:
            parsed = _safe_date(year + 1, month, day)
        if parsed:
            candidates.append((parsed, slash.group(0)))

    month_name = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+("
        + "|".join(MONTH_INDEX.keys())
        + r")\b|\b("
        + "|".join(MONTH_INDEX.keys())
        + r")\s+(\d{1,2})(?:st|nd|rd|th)?\b",
        lowered,
    )
    if month_name:
        if month_name.group(1):
            day = int(month_name.group(1))
            month = MONTH_INDEX[month_name.group(2)]
            phrase = month_name.group(0)
        else:
            month = MONTH_INDEX[month_name.group(3)]
            day = int(month_name.group(4))
            phrase = month_name.group(0)
        parsed = _safe_date(today.year, month, day)
        if parsed and parsed < today:
            parsed = _safe_date(today.year + 1, month, day)
        if parsed:
            candidates.append((parsed, phrase))

    for weekday, weekday_index in WEEKDAY_INDEX.items():
        if re.search(rf"\bnext\s+{weekday}\b", lowered):
            candidates.append((_next_weekday(today, weekday_index, include_today=False), f"next {weekday}"))
            break
        if re.search(rf"\bthis\s+{weekday}\b", lowered):
            candidates.append((_next_weekday(today, weekday_index, include_today=True), f"this {weekday}"))
            break
        if re.search(rf"\b{weekday}\b", lowered):
            candidates.append((_next_weekday(today, weekday_index, include_today=False), weekday))
            break

    if not candidates:
        return {
            "today": today.isoformat(),
            "today_label": today.strftime("%A, %d %B %Y"),
            "mentioned_date": None,
            "mentioned_date_label": None,
            "days_until": None,
            "source_text": None,
            "mentioned_time": mentioned_time,
            "mentioned_time_source": mentioned_time_source,
        }

    target, source_text = sorted(candidates, key=lambda item: abs((item[0] - today).days))[0]
    return {
        "today": today.isoformat(),
        "today_label": today.strftime("%A, %d %B %Y"),
        "mentioned_date": target.isoformat(),
        "mentioned_date_label": target.strftime("%A, %d %B %Y"),
        "days_until": (target - today).days,
        "source_text": source_text,
        "mentioned_time": mentioned_time,
        "mentioned_time_source": mentioned_time_source,
    }


def _date_context_text(date_info: dict) -> str:
    now = _now_local()
    current_time = now.strftime("%H:%M %Z").strip()
    if not date_info.get("mentioned_date"):
        time_note = f" Current local time is {current_time}." if current_time else ""
        return f"Today is {date_info['today_label']}.{time_note}"
    days = date_info.get("days_until")
    if days == 0:
        distance = "today"
    elif days == 1:
        distance = "tomorrow"
    elif days is not None and days > 1:
        distance = f"in {days} days"
    elif days is not None:
        distance = f"{abs(days)} days ago"
    else:
        distance = "date mentioned"
    time_suffix = f" at {date_info['mentioned_time']}" if date_info.get("mentioned_time") else ""
    current_time_note = f" Current local time is {current_time}." if current_time else ""
    return (
        f"Today is {date_info['today_label']}. "
        f"The user mentioned {date_info['source_text']} -> {date_info['mentioned_date_label']}{time_suffix} ({distance})."
        f"{current_time_note}"
    )


_ACTION_TO_INTENT = {
    "reduce_tasks": "trim",
    "skip_task": "skip",
    "next_week": "next_week",
    "restore": "restore",
    "harder": "advanced",
    "easier": "normal",
    "add_course": "course",
    "constraint": "constraint",
    "permanent_preference": "permanent_preference",
    "next_week_request": "next_week_request",
    "web_search": "web_search",
    "chat": "tutor_chat",
}


def _intent_cache_key(user_message: str, current_actions: list[dict]) -> str:
    # Classification depends on the message AND the current task list (it can
    # reference tasks by number/title), so both must be part of the key.
    titles = "|".join(a.get("title", "") for a in (current_actions or []))
    return f"{str(user_message).strip().lower()}||{titles}"


@cached("intent", ttl=3600, key_fn=_intent_cache_key)  # 1h — deterministic routing decision
def _classify_intent_llm(user_message: str, current_actions: list[dict]) -> dict:
    """
    Ask the model to UNDERSTAND what the student wants (in any language or phrasing)
    and return a small structured decision. Deterministic code then executes it, so the
    model never has to regenerate the task list — it only has to understand intent.
    Returns {} on failure so the caller can fall back to keyword matching.
    """
    titles = [f"{i+1}. {a.get('title', '')}" for i, a in enumerate(current_actions or [])]
    titles_text = "\n".join(titles) if titles else "(no tasks yet)"
    prompt = f"""You are the intent router for delta's weekly study-plan assistant.
The student may write in ANY language, script, or style. Understand their meaning, then decide what they want.

The student's current week has {len(current_actions or [])} task(s):
{titles_text}

Student message:
\"\"\"{user_message}\"\"\"

Reply with ONLY a JSON object (no markdown), choosing exactly one action:
{{
  "action": "reduce_tasks | skip_task | next_week | restore | harder | easier | add_course | constraint | permanent_preference | next_week_request | chat",
  "count": <integer or null>,   // for reduce_tasks: how many tasks to KEEP. null if unspecified.
  "target": "<string or null>", // for skip_task: which task. null if unclear.
  "reply": "<one short, warm sentence to the student, written in the SAME language they used, confirming what you will do>"
}}

Meaning of each action:
- reduce_tasks: they feel overwhelmed and want fewer tasks this week.
- skip_task: they want to drop one specific task from this week.
- next_week: they are DONE and want to advance to a brand-new week RIGHT NOW. Only use when they explicitly say so (e.g. "I finished everything, give me next week", "advance", "I'm done").
- restore: they want their previous tasks back or to undo a recent change.
- harder: the work is too easy; they want tougher tasks.
- easier: the work is too hard; they want simpler tasks.
- add_course: they want a course assigned.
- constraint: an exam, deadline, travel, illness, or busy period should reshape THIS week's tasks.
- permanent_preference: the user is setting a firm, lasting rule about how ALL future weeks should be structured — things like "never give me more than 2 tasks", "stop giving me courses", "the pace is always too fast", "I don't want LeetCode ever", "always include a project". These rules must be remembered permanently.
- next_week_request: the user is requesting something specific for NEXT week's plan without advancing now (e.g. "for next week give me API tasks", "can next week include a project?", "I want DSA next week"). Save it — don't advance yet.
- web_search: the user explicitly wants current resources, course links, tutorials, documentation, or real-time info that would benefit from a live web search (e.g. "find me the best React course", "what are the best resources for FastAPI?", "search for system design resources").
- chat: everything else — a question, an explanation request, general conversation. When unsure, always choose chat.

Return only the JSON object."""
    try:
        from app.services.ai_service import generate_json, FAST_MODEL
        result = generate_json(prompt, temperature=0.1, model=FAST_MODEL)
        if isinstance(result, dict) and result.get("action") in _ACTION_TO_INTENT:
            return result
    except Exception as exc:
        logger.warning(f"LLM intent classification failed, using keyword fallback: {exc}")
    return {}


def _agent2_intent(text: str) -> str:
    lowered = text.lower().strip()
    clean = lowered.strip(" .!?")
    if clean in {"hi", "hello", "hey", "hii", "yo", "good morning", "good evening"}:
        return "tutor_chat"
    if any(phrase in lowered for phrase in [
        "previous task", "previous tasks", "earlier task", "earlier tasks", "old task", "old tasks",
        "original task", "original tasks", "restore", "undo", "bring back", "give them back",
        "revert", "tasks you gave me before", "tasks you gave me",
    ]):
        return "restore"
    if re.search(r"\b(give me next week|generate next week|advance to next week|next week('s)? tasks|next week('s)? plan|new week now|start next week|move to next week)\b", lowered):
        return "next_week"
    if any(phrase in lowered for phrase in [
        "too many task", "too many", "these many task", "these many", "cant do these",
        "can't do these", "cannot do these", "reduce it to", "reduce to", "reduce the number",
        "reduce the task", "reduce task", "fewer task", "fewer tasks", "less task", "less tasks",
        "shorten", "shorter", "trim", "cut it to", "cut down the", "keep only", "only keep",
        "lower the number", "make it 2", "make it 3", "just 2 task", "just 3 task",
    ]):
        return "trim"
    if any(phrase in lowered for phrase in [
        "skip this task", "skip the task", "skip it", "remove this task", "remove the task",
    ]):
        return "skip"
    if any(phrase in lowered for phrase in [
        "exam", "test", "quiz", "paper", "mid sem", "midsem", "viva", "deadline",
        "submission", "interview", "presentation", "practical", "travel", "sick",
        "low energy", "busy",
    ]):
        return "constraint"
    if any(phrase in lowered for phrase in [
        "replace with a course", "give me a course", "assign a course", "make this a course",
        "one course", "certification instead",
    ]):
        return "course"
    if any(phrase in lowered for phrase in [
        "make it advanced", "make this advanced", "make it harder", "make this harder",
        "give tougher tasks", "too basic", "low level", "i have done these",
        "ahead of what i have done", "replace with advanced", "not beginner task",
    ]):
        return "advanced"
    if any(phrase in lowered for phrase in [
        "make it easier", "make this easier", "make it normal", "normal task",
        "moderate task", "simpler task", "too hard", "reduce difficulty",
    ]):
        return "normal"
    if any(phrase in lowered for phrase in [
        "detail", "where should i start", "start from", "exactly should i do", "explain",
        "how should i do", "what should i do", "break down", "steps",
    ]):
        return "tutor_chat"
    return "tutor_chat"


def _event_from_user_message(text: str, date_info: dict) -> dict | None:
    lowered = text.lower()
    event_keywords = ["exam", "test", "quiz", "paper", "mid sem", "midsem", "viva", "deadline", "submission", "interview", "presentation", "function", "wedding", "travel"]
    if not any(keyword in lowered for keyword in event_keywords):
        return None
    start = date_info.get("mentioned_date") or _today_local().isoformat()
    end_date = None
    duration = re.search(r"\b(?:for|lasts?|lasting)\s+(\d{1,2})\s+(day|days|week|weeks|month|months)\b", lowered)
    if duration:
        amount = int(duration.group(1))
        unit = duration.group(2)
        if unit.startswith("day"):
            days = amount
        elif unit.startswith("week"):
            days = amount * 7
        else:
            days = amount * 30
        end_date = (datetime.date.fromisoformat(start) + datetime.timedelta(days=max(days - 1, 0))).isoformat()
    elif "for a month" in lowered or "for one month" in lowered:
        end_date = (datetime.date.fromisoformat(start) + datetime.timedelta(days=29)).isoformat()
    elif "for a week" in lowered or "for one week" in lowered:
        end_date = (datetime.date.fromisoformat(start) + datetime.timedelta(days=6)).isoformat()
    else:
        end_date = start

    kind = "exam" if any(word in lowered for word in ["exam", "test", "quiz", "paper", "mid sem", "midsem", "viva"]) else "blocked_event"
    title = "Exam period" if kind == "exam" else "Blocked personal event"
    return {
        "title": title,
        "kind": kind,
        "raw_text": text,
        "start_date": start,
        "end_date": end_date,
        "time": date_info.get("mentioned_time"),
        "blocks_normal_work": True,
        "impact": "Normal delta coursework should pause or reduce during this event.",
    }


def _resume_guidance(actions: list[dict]) -> str:
    if not actions:
        return (
            "This week should give you one resume signal: a small proof with a clear problem, method, result, and link. "
            "After you finish it, write one bullet in this shape: Built [project] to solve [problem], using [skills], measured by [result]."
        )

    skill_names = []
    for action in actions:
        skill = action.get("skill") or action.get("title")
        if skill and skill not in skill_names:
            skill_names.append(skill)

    first = actions[0]
    first_title = first.get("title") or "the first weekly task"
    second_title = actions[1].get("title") if len(actions) > 1 else ""

    bullets = [
        f"Built a memory-quality evaluation suite for an agent workflow with 8-10 test prompts covering recall, forgetting, retrieval accuracy, and failure cases.",
        "Red-teamed an agent workflow with adversarial prompts, documented failure patterns, and added one guardrail or scoring rule to improve reliability.",
    ]
    if second_title:
        task_line = f"Your two proof tasks are: {first_title}; {second_title}."
    else:
        task_line = f"Your proof task is: {first_title}."

    return (
        f"{task_line}\n\n"
        f"Skills you can gain: {', '.join(skill_names[:6])}, evaluation design, adversarial testing, reliability analysis, documentation, and proof-based project presentation.\n\n"
        "How to put it on your resume after you actually finish it:\n"
        f"- {bullets[0]}\n"
        f"- {bullets[1] if second_title else 'Documented the experiment setup, scoring rubric, results, and next improvements in a GitHub README.'}\n\n"
        "Do not write it as just 'learned AI agents'. Write it as proof: what you built, how you tested it, what failed, and what improved."
    )


def _explain_action(action: dict | None) -> str:
    action = action or {}
    title = action.get("title") or action.get("skill") or "this week's first task"
    description = action.get("description") or action.get("detail") or action.get("action") or "make one small proof and write what it proves"
    source_text = _action_source(action)
    return (
        f"Start with: {title}.\n\n"
        f"1. Create a small folder or GitHub repo for only this task.\n"
        f"2. Add a README with the goal in 2-3 lines.\n"
        f"3. Do the actual work: {description}\n"
        f"4. Use this source if attached: {source_text}\n"
        f"5. Add proof: screenshots, logs, notebook output, demo link, design notes, or a small results table.\n"
        f"6. Finish with 5 lines: what worked, what failed, what you improved, what is still weak, and what you will do next."
    )


def _target_task_count(text: str, current_count: int) -> int:
    """How many tasks to keep when the user asks to reduce. Handles '2-3', 'to 2', etc."""
    nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", text) if 0 < int(n) <= 12]
    target = max(nums) if nums else 2  # for "2-3" keep the higher so we don't over-trim
    if current_count:
        target = min(target, current_count)
    return max(1, target)


def _constraint_actions(
    profile: dict,
    user: User | None,
    text: str,
    date_info: dict | None = None,
    current_actions: list[dict] | None = None,
) -> list[dict]:
    domain = _domain_from_profile(profile, user)
    lowered = text.lower()
    exam_like = any(word in lowered for word in ["exam", "test", "quiz", "paper", "mid sem", "midsem", "viva", "practical"])
    date_info = date_info or _parse_date_reference(text)
    days_until = date_info.get("days_until")
    if exam_like:
        if days_until is not None and days_until > 14:
            description = (
                "Keep normal work light, but start exam prep now: list syllabus topics, mark weak areas, "
                "and spend one short block on the weakest topic. Do not add a new course this week."
            )
        else:
            description = (
                "Pause projects and courses this week. Make a topic list from your syllabus, revise the weakest 2 topics, "
                "solve past questions, and keep one mistake log."
            )
        return [{
            "id": f"task-{domain}-exam-support",
            "type": "practice",
            "title": "Exam-first study block",
            "skill": "Exam Preparation",
            "description": description,
            "source": "Your college syllabus and previous papers",
            "url": "",
            "due_date": date_info.get("mentioned_date"),
        }]

    # "Busy / low energy / shorten the list" — the user still wants to make progress,
    # just less of it. Keep their most important existing tasks (trimmed) instead of
    # replacing everything with one generic maintenance task.
    reduce_like = any(
        word in lowered
        for word in [
            "shorten", "shorter", "fewer", "reduce", "less", "lighter", "light",
            "trim", "busy", "little time", "low energy", "not much time", "cut down",
        ]
    )
    current_actions = current_actions or []
    if current_actions and reduce_like:
        kept = []
        for action in current_actions[:2]:
            trimmed = dict(action)
            base = (trimmed.get("description") or "").strip()
            trimmed["description"] = f"Reduced scope for a busy week — do a smaller version: {base}" if base else "Do a smaller version of this task this week."
            kept.append(trimmed)
        return kept

    # No existing tasks to trim, or a full block (travel/sick) — fall back to one light task.
    return [{
        "id": f"task-{domain}-light-week",
        "type": "practice",
        "title": "Light recovery week",
        "skill": "Consistency",
        "description": "Keep only one small maintenance task this week: 60-90 minutes of review, one note, and one check-in message to Agent 2.",
        "source": "delta pace adjustment",
        "url": "",
        "due_date": date_info.get("mentioned_date"),
    }]


@router.post("/message", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat_message(
    request: Request,
    data: ChatRequest,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None),
    authorization: str | None = Header(None),
):
    verify_resource_owner(data.user_id, x_user_id=x_user_id, authorization=authorization)
    user = db.query(User).filter(User.id == data.user_id).first()
    skills = db.query(SkillNode).filter(SkillNode.user_id == data.user_id).all()
    roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == data.user_id).first()
    user_context = f"User: {user.name if user else 'Unknown'}, Target: {user.target_role if user else 'N/A'}"
    is_weekly_agent = "Agent 2 weekly plan discussion" in data.message
    user_update = data.message.split("User update:", 1)[-1].strip() if "User update:" in data.message else data.message
    lowered_update = user_update.lower().strip(" .!?")
    current_actions = _current_actions_from_roadmap(roadmap)
    intent_obj = _classify_intent_llm(user_update, current_actions) if is_weekly_agent else {}
    if intent_obj:
        intent = _ACTION_TO_INTENT.get(intent_obj.get("action"), "tutor_chat")
    else:
        intent = "tutor_chat" if is_weekly_agent else "chat"
    llm_reply = intent_obj.get("reply") if intent_obj else None
    llm_count = intent_obj.get("count") if intent_obj else None
    llm_target = intent_obj.get("target") if intent_obj else None
    date_info = _parse_date_reference(user_update)
    date_context = _date_context_text(date_info)
    profile_file = load_profile(data.user_id) or {}
    _hours_per_week = int(profile_file.get("hours_per_week") or (user.hours_per_week if user else None) or 10)
    _raw_months = profile_file.get("planning_horizon_months") or None
    _raw_years = profile_file.get("planning_horizon_years") or None
    if _raw_months:
        _horizon_months = int(_raw_months)
        _horizon_years = _horizon_months / 12
    elif _raw_years:
        _horizon_years = float(_raw_years)
        _horizon_months = int(_horizon_years * 12)
    else:
        _horizon_months = 12
        _horizon_years = 1.0
    if _horizon_months >= 18:
        _pace_label = "relaxed"
        _task_cap = 2
    elif _horizon_months >= 6:
        _pace_label = "moderate"
        _task_cap = 3
    else:
        _pace_label = "intensive"
        _task_cap = 4
    # Intent over keywords: only treat a mentioned event as schedule-blocking when the AI
    # judged the user actually wants the week reshaped (constraint). A casual mention like
    # "a function at home this month" while asking to reduce tasks is context, NOT a command
    # to block the week. The old code created a blocking event purely from the word "function".
    persisted_event = (
        _event_from_user_message(user_update, date_info)
        if (is_weekly_agent and intent == "constraint")
        else None
    )
    if persisted_event:
        persisted_event = upsert_upcoming_event(data.user_id, persisted_event)

    if is_weekly_agent and intent == "tutor_chat":
        career_context = {
            "roadmap": {"weekly_focus": {"primary_actions": current_actions}},
            "journey_until_today": [],
        }
    else:
        try:
            career_context = compile_career_context(db, data.user_id)
        except Exception:
            career_context = {}

    if is_weekly_agent:
        sync_user_context(data.user_id, profile_file, career_context)
        sync_current_week(data.user_id, career_context, current_actions, reason="Agent 2 chat loaded current week.")

    skills_context = ", ".join([f"{s.name} ({s.proficiency}/10)" for s in skills]) if skills else "No skills yet"
    profile_context = profile_as_context_string(data.user_id)
    persistent_context = memory_context_text(data.user_id)
    context_json = json.dumps(career_context, default=str)[:8000]
    from app.services.user_context_store import read_current_week_context, read_profile_doc
    user_instructions_ctx = read_current_week_context(data.user_id) if is_weekly_agent else ""
    user_profile_doc = read_profile_doc(data.user_id) if is_weekly_agent else ""

    try:
        from app.services.ai_service import generate_response, quality_model

        lowered_update = user_update.lower()
        if is_weekly_agent:
            if intent == "restore":
                weekly_focus = _as_json(roadmap.weekly_focus, {}) if roadmap else {}
                previous = weekly_focus.get("previous_actions") or []
                if roadmap and previous:
                    restored_phase = weekly_focus.get("previous_phase_name") or "Restored week"
                    _save_weekly_actions(db, roadmap, previous, restored_phase)
                    sync_current_week(data.user_id, career_context, previous, reason="User asked Agent 2 to restore the previous tasks.")
                    response_text = (
                        f"Done — I brought back your previous {len(previous)} task"
                        f"{'s' if len(previous) != 1 else ''}.\n\n{_format_action_bullets(previous)}"
                    )
                else:
                    response_text = (
                        "I don't have a saved previous task list to restore. "
                        "I can generate a fresh set for this week instead — just say 'give me this week's tasks'."
                    )
                append_chat_turn(data.user_id, user_update, response_text, intent)
                return ChatResponse(
                    response=response_text, context=user_context,
                    updated_actions=(previous if (roadmap and previous) else None),
                )

            if intent == "permanent_preference":
                from app.services.user_context_store import append_permanent_instruction
                append_permanent_instruction(data.user_id, user_update)
                response_text = llm_reply or "Got it — I've saved that as a permanent preference. It will apply to every week going forward."
                append_chat_turn(data.user_id, user_update, response_text, intent)
                return ChatResponse(response=response_text, context=user_context)

            if intent == "next_week_request":
                from app.services.user_context_store import append_next_week_request
                # Try to extract weeks count from message ("for 3 weeks", "next 2 weeks", "for the next 4 weeks", etc.)
                import re as _re
                _weeks_match = _re.search(r"(?:for\s+(?:the\s+)?next\s+|for\s+)(\d+)\s+weeks?", user_update, _re.IGNORECASE)
                _weeks_count = int(_weeks_match.group(1)) if _weeks_match else 1
                _weeks_count = max(1, min(12, _weeks_count))
                append_next_week_request(data.user_id, user_update, weeks=_weeks_count)
                _weeks_note = f" (active for {_weeks_count} week{'s' if _weeks_count > 1 else ''})" if _weeks_count > 1 else ""
                response_text = llm_reply or f"Noted! I've saved that for your next weekly plan{_weeks_note}. When you're ready to advance, it will be factored in."
                append_chat_turn(data.user_id, user_update, response_text, intent)
                return ChatResponse(response=response_text, context=user_context)

            if intent == "web_search":
                try:
                    from app.services.web_search import get_web_search_service
                    svc = get_web_search_service()
                    results = svc.search(user_update, max_results=5)
                    search_context = "\n".join(
                        f"- {r.get('title', '')}: {r.get('url', '')} — {r.get('snippet', '')}"
                        for r in (results or [])[:5]
                    )
                except Exception as _se:
                    logger.warning(f"Web search failed for web_search intent: {_se}")
                    search_context = ""
                # Fall through to tutor_chat LLM with search results injected
                intent = "tutor_chat"
                if search_context:
                    user_update = f"{user_update}\n\n[Live web search results for your query:]\n{search_context}"

            if intent == "next_week":
                try:
                    next_context = run_weekly_career_cycle(db, data.user_id)
                    next_actions = ((next_context.get("roadmap") or {}).get("weekly_focus") or {}).get("primary_actions") or []
                    sync_user_context(data.user_id, profile_file, next_context)
                    sync_current_week(data.user_id, next_context, next_actions, reason="User asked Agent 2 for next week's tasks.")
                    next_phase = ((next_context.get("roadmap") or {}).get("weekly_focus") or {}).get("phase_name")
                    response_text = (
                        f"Here is your next week ({next_phase}). " if next_phase else "Here is your next week. "
                    ) + "These are the tasks I have set:\n\n" + _format_action_bullets(next_actions)
                    append_chat_turn(data.user_id, user_update, response_text, intent)
                    return ChatResponse(
                        response=response_text, context=user_context,
                        updated_actions=next_actions, week_phase=next_phase,
                    )
                except (ValueError, Exception) as exc:
                    logger.error("next_week via chat failed for %s: %s", data.user_id, exc, exc_info=True)
                    response_text = str(exc) if isinstance(exc, ValueError) else f"Something went wrong generating next week's plan. Please try the 'Request Next Week' button on the Roadmap page."
                    append_chat_turn(data.user_id, user_update, response_text, intent)
                    return ChatResponse(response=response_text, context=user_context)

            if intent == "skip" and roadmap and current_actions:
                target = current_actions[0]
                # Use the task the AI identified (number or keyword); fall back to text match.
                hint = str(llm_target or "").lower().strip()
                matched = False
                if hint:
                    if hint.isdigit():
                        idx = int(hint) - 1
                        if 0 <= idx < len(current_actions):
                            target = current_actions[idx]
                            matched = True
                    if not matched:
                        for action in current_actions:
                            if hint in action.get("title", "").lower() or hint in action.get("skill", "").lower():
                                target = action
                                matched = True
                                break
                if not matched:
                    for action in current_actions:
                        if action.get("title", "").lower() in lowered_update or action.get("skill", "").lower() in lowered_update:
                            target = action
                            break
                event = log_journey_event(
                    db=db,
                    user_id=data.user_id,
                    event_type="weekly_task_skipped",
                    summary=f"Skipped Agent 2 task: {target.get('title')}",
                    evidence=target,
                    impact={"user_chose_to_skip": True, "source": "agent_2_chat"},
                )
                append_progress_event(data.user_id, serialize_journey_event(event))
                response_text = f"Skipped: {target.get('title')}. It will no longer block this week. If you want, I can replace it with a normal task, a tougher task, or one course."
                append_chat_turn(data.user_id, user_update, response_text, intent)
                return ChatResponse(response=response_text, context=user_context)

            if intent == "course" and roadmap:
                profile = load_profile(data.user_id)
                active_course = _has_active_course(current_actions, career_context)
                if active_course:
                    response_text = (
                        f"You already have one course active: {active_course.get('title')}. "
                        f"Finish it or skip it before I add another course. Source: {_action_source(active_course)}"
                    )
                    return ChatResponse(response=response_text, context=user_context)
                course = _course_action(profile, user, lowered_update)
                _save_weekly_actions(db, roadmap, [course], "One-course weekly sprint")
                response_text = (
                    f"I replaced this week with one course only: {course['title']}. "
                    f"Source: {_action_source(course)}. Do not add another course until this is completed or skipped."
                )
                sync_current_week(data.user_id, career_context, [course], reason="Agent 2 assigned a one-course week.")
                event = log_journey_event(
                    db=db,
                    user_id=data.user_id,
                    event_type="assistant_guidance",
                    summary=f"Agent 2 assigned one course: {course['title']}",
                    evidence={"message": data.message, "response_text": response_text, "updated_actions": [course]},
                    impact={"weekly_tasks_updated": True, "active_course_guard": True},
                )
                append_progress_event(data.user_id, serialize_journey_event(event))
                append_chat_turn(data.user_id, user_update, response_text, intent)
                return ChatResponse(
                    response=response_text, context=user_context,
                    updated_actions=[course], week_phase="One-course weekly sprint",
                )

            if intent in {"advanced", "normal"} and roadmap:
                profile = load_profile(data.user_id)
                updated_actions = _advanced_actions(profile, user, "normal" if intent == "normal" else "tough")
                _save_weekly_actions(db, roadmap, updated_actions, "Normal profile proof sprint" if intent == "normal" else "Advanced profile proof sprint")
                response_text = (
                    "Updated this week immediately. I used your resume/profile evidence instead of beginner tasks.\n\n"
                    f"{_format_action_bullets(updated_actions)}"
                )
                sync_current_week(data.user_id, career_context, updated_actions, reason="Agent 2 changed task difficulty.")
                event = log_journey_event(
                    db=db,
                    user_id=data.user_id,
                    event_type="assistant_guidance",
                    summary=f"Agent 2 advanced weekly tasks: {user_update[:120]}",
                    evidence={"message": data.message, "response_text": response_text, "updated_actions": updated_actions},
                    impact={"context_used": True, "weekly_tasks_updated": True},
                )
                append_progress_event(data.user_id, serialize_journey_event(event))
                append_chat_turn(data.user_id, user_update, response_text, intent)
                return ChatResponse(
                    response=response_text, context=user_context,
                    updated_actions=updated_actions,
                    week_phase=("Normal profile proof sprint" if intent == "normal" else "Advanced profile proof sprint"),
                )

            if intent == "trim" and roadmap:
                if not current_actions:
                    response_text = "There are no tasks to reduce right now. Ask me for this week's tasks first."
                    append_chat_turn(data.user_id, user_update, response_text, intent)
                    return ChatResponse(response=response_text, context=user_context)
                # Prefer the count the AI understood from the message; fall back to regex.
                if isinstance(llm_count, (int, float)) and llm_count > 0:
                    keep = max(1, min(int(llm_count), len(current_actions)))
                else:
                    keep = _target_task_count(user_update, len(current_actions))
                updated_actions = current_actions[:keep]
                _save_weekly_actions(db, roadmap, updated_actions, "Reduced weekly load")
                sync_current_week(data.user_id, career_context, updated_actions, reason="User asked Agent 2 to reduce the number of tasks.")
                lead = (llm_reply or "").strip() or (
                    f"Done — I reduced this week to your {keep} most important task"
                    f"{'s' if keep != 1 else ''} so it stays manageable."
                )
                response_text = f"{lead}\n\n{_format_action_bullets(updated_actions)}"
                event = log_journey_event(
                    db=db,
                    user_id=data.user_id,
                    event_type="assistant_guidance",
                    summary=f"Agent 2 reduced weekly task count to {keep}: {user_update[:100]}",
                    evidence={"message": data.message, "response_text": response_text, "updated_actions": updated_actions},
                    impact={"weekly_tasks_updated": True, "task_count_reduced": True},
                )
                append_progress_event(data.user_id, serialize_journey_event(event))
                append_chat_turn(data.user_id, user_update, response_text, intent)
                return ChatResponse(
                    response=response_text, context=user_context,
                    updated_actions=updated_actions, week_phase="Reduced weekly load",
                )

            if intent == "constraint" and roadmap:
                profile = load_profile(data.user_id)
                updated_actions = _constraint_actions(profile, user, user_update, date_info, current_actions)
                _save_weekly_actions(db, roadmap, updated_actions, "Pace-adjusted week")
                count = len(updated_actions)
                lead = (
                    f"I trimmed this week to your {count} most important task{'s' if count != 1 else ''} so it stays manageable while you're busy."
                    if count > 1
                    else "I lightened this week to a single focused task."
                )
                response_text = (
                    f"{lead} {date_context}\n\n{_format_action_bullets(updated_actions)}"
                )
                sync_current_week(data.user_id, career_context, updated_actions, reason="Agent 2 adjusted for event or schedule constraint.")
                event = log_journey_event(
                    db=db,
                    user_id=data.user_id,
                    event_type="assistant_guidance",
                    summary=f"Agent 2 adjusted weekly pace: {user_update[:120]}",
                    evidence={"message": data.message, "response_text": response_text, "updated_actions": updated_actions},
                    impact={"weekly_tasks_updated": True, "constraint_adjustment": True},
                )
                append_progress_event(data.user_id, serialize_journey_event(event))
                append_chat_turn(data.user_id, user_update, response_text, intent)
                return ChatResponse(
                    response=response_text, context=user_context,
                    updated_actions=updated_actions, week_phase="Pace-adjusted week",
                )

            # Check if the user is CS / software-engineering oriented
            _pf = profile_file or {}
            _role_lower = (str(user.target_role or "") + " " + str(_pf.get("major", "") or "")).lower()
            _cs_keywords = {"software", "developer", "engineer", "cs", "computer science", "cse",
                            "data scientist", "machine learning", "ml", "ai", "backend", "frontend",
                            "fullstack", "sde", "swe", "programmer", "data engineer"}
            is_cs_user = any(kw in _role_lower for kw in _cs_keywords)

            # Build LeetCode context block — only for CS users whose current tasks include problems
            leetcode_block = ""
            if is_cs_user:
                for _action in current_actions:
                    _problems = _action.get("problems") or []
                    if _problems:
                        _lines = "\n".join(
                            f"  - #{p['id']} {p['title']} [{p['difficulty']}] → {p['url']}"
                            for p in _problems
                        )
                        leetcode_block = (
                            f"\nThis week's LeetCode problems (NeetCode 150 — {_action.get('title', 'LeetCode')}):\n"
                            f"{_lines}\n"
                            "When the user asks about any of these problems or how to approach LeetCode this week, "
                            "refer to the specific problems above by name, explain the pattern, hint the approach, "
                            "and link the exact problem URL. Do not invent other problems."
                        )
                        break

            leetcode_rule = (
                leetcode_block if leetcode_block
                else "\nDo NOT mention LeetCode, DSA practice, or coding interview problems. "
                     "This student is not pursuing CS/engineering."
                if not is_cs_user else ""
            )

            role_prompt = f"""You are Agent 2 inside delta Career OS — a personal weekly coach for students in any domain: CS, commerce, design, law, healthcare, arts, engineering, and more.
Today: {date_context}

━━ STUDENT PACE PROFILE (read this first, every time) ━━
Planning horizon: {_horizon_months} months ({_horizon_years:.1f} years)
Pace mode: {_pace_label.upper()}
Weekly hours available: {_hours_per_week}h TOTAL — this is shared across ALL tasks combined, not per task.
Max tasks this week: {_task_cap} (unless the student explicitly asks for more)

Pacing rules (HARD RULES — override any other instinct):
- {_pace_label.upper()} pace means: {"Do NOT pile on tasks. Keep it light and sustainable. 1–2 tasks maximum. If the student has 2+ years ahead, there is plenty of time — don't rush them. Only increase intensity if they explicitly ask." if _pace_label == "relaxed" else "Moderate load. 2–3 tasks. Match the weekly hours. Don't overload." if _pace_label == "moderate" else "Focused sprint. Up to 4 tasks. Use the full weekly hours. Student is in a time-pressured mode."}
- Estimated effort of ALL tasks combined must not exceed {_hours_per_week}h per week.
- If the user has NOT asked to go faster, default to the lighter end of the pace range.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PERMANENT INSTRUCTIONS (from user, apply every week — check the USER INSTRUCTIONS DOCUMENT):
These override everything except safety. Read them before answering.

━━ HOW TO RESPOND ━━
Chit-chat / casual messages (hi, thanks, how are you, etc.): reply naturally like a human tutor. Do NOT output JSON for these.
Questions about tasks: explain clearly, give steps, links, time estimates. No JSON unless a task needs updating.
Task changes requested: see pushback rules below before complying.
Live web results in the message ([Live web search results]): use those URLs in your answer.

━━ PUSHBACK RULES (critical — do not skip) ━━
You are not a yes-machine. You are a coach who cares about the student's actual outcome.
If the student asks to remove, skip, or avoid a task that is genuinely important for their goal:
  1. Push back directly and honestly. Tell them exactly why this task matters for their career.
  2. Be frank — not rude, but don't sugarcoat it. Say things like "I can remove it, but I want to be honest with you — this task is foundational for X, and skipping it will slow you down."
  3. If they insist a second time, respect their choice and comply. But make the case first, every time.
  4. If the task is genuinely replaceable or they have a valid reason (exam, burnout, better alternative), agree and adjust.
The goal: the student should feel you have their back, not just their approval.

━━ TASK MANAGEMENT ━━
Update tasks when you judge it would genuinely help — not just when explicitly asked.
When updating tasks, output ONLY at the very end of your response:
```json
{{
  "updated_actions": [
    {{
      "id": "action-0",
      "type": "course|project|practice",
      "title": "Short title",
      "skill": "Skill name",
      "description": "What to actually do this week (concrete, not vague)",
      "source": "Resource name if any",
      "url": "https://real-url.com"
    }}
  ]
}}
```
Rules: max one active course at a time · every course needs a real URL · if student already knows a skill, skip beginner content and assign a proof/project instead · unfinished tasks carry over · skipped tasks are removed.
"description" is displayed as plain text, not rendered math — never use LaTeX/math notation (no "\rightarrow", "\times", "$...$"); write step sequences with a plain arrow (→) or the word "then".
{leetcode_rule}
Current tasks:
{json.dumps(current_actions, indent=2)}"""
        else:
            role_prompt = """You are delta, the central AI assistant inside a personalized Career OS.
Use the user's Career Memory, Roadmap State, Market Pulse, Journey Log, Proof Projects, and Portfolio Assessment.
Be honest, specific, and action-oriented. If the user is drifting, say it clearly but supportively."""

        prompt = f"""{role_prompt}

━━ STUDENT ━━
{user_context}
Skills: {skills_context}

━━ FULL PROFILE ━━
{profile_context}

━━ USER INSTRUCTIONS DOCUMENT ━━
{user_instructions_ctx if user_instructions_ctx else "(no instructions yet)"}

━━ PROFILE HISTORY (skills + completed tasks) ━━
{user_profile_doc if user_profile_doc else "(not yet built)"}

━━ CONVERSATION MEMORY ━━
{persistent_context}

━━ USER MESSAGE ━━
{user_update}"""
        response = generate_response(
            prompt,
            temperature=0.5 if is_weekly_agent else 0.7,
            max_tokens=10000,
            model=quality_model(),
        )
        cleaned_response = response.strip()
        updated_actions = None
        returned_actions = None

        if is_weekly_agent:
            cleaned_response, updated_actions = _extract_updated_actions(response)

        if is_weekly_agent and updated_actions and roadmap:
            try:
                weekly_focus = _as_json(roadmap.weekly_focus, {})
                sanitized_actions = []
                for i, act in enumerate(updated_actions):
                    sanitized_actions.append({
                        "id": act.get("id") or f"action-{i}",
                        "type": act.get("type") or "project",
                        "title": act.get("title") or act.get("label") or act.get("skill") or f"Task {i+1}",
                        "skill": act.get("skill") or "Skill",
                        "description": act.get("description") or act.get("detail") or act.get("proof") or "Details...",
                        "source": act.get("source") or act.get("platform") or "",
                        "url": act.get("url") or act.get("resource_url") or "",
                    })
                weekly_focus["primary_actions"] = sanitized_actions
                weekly_focus["manual"] = True  # locked: this is the AI's decided list
                roadmap.weekly_focus = json.dumps(weekly_focus)
                db.commit()
                db.refresh(roadmap)
                returned_actions = sanitized_actions
            except Exception as db_err:
                db.rollback()
                print(f"Error updating roadmap actions in DB: {db_err}")

        # Fallback to hardcoded default text if the LLM output was completely empty
        if is_weekly_agent and not cleaned_response:
            weekly_focus = (career_context.get("roadmap") or {}).get("weekly_focus", {})
            actions = weekly_focus.get("primary_actions") or []
            action = actions[0] if actions else {}
            skill = action.get("skill") or "this week's roadmap skill"
            if "sql" in data.message.lower() or "relational" in data.message.lower() or "sql" in skill.lower():
                cleaned_response = (
                    "This week, make SQL concrete. Build a tiny SQLite project for a student task tracker: "
                    "tables for users, tasks, weekly_plans, and completions. Add 10 sample rows. Then write queries using "
                    "SELECT, WHERE, JOIN, GROUP BY, ORDER BY, and one indexed lookup. Your proof is a GitHub folder with "
                    "schema.sql, sample_data.sql, queries.sql, and a README explaining what each query proves."
                )
            else:
                cleaned_response = (
                    f"This week, focus on {skill}. Keep it to one proof task, finish it, then report whether the pace was easy, hard, or blocked."
                )

        event = log_journey_event(
            db=db,
            user_id=data.user_id,
            event_type="assistant_guidance",
            summary=f"delta answered career question: {data.message[:120]}",
            evidence={"message": data.message, "response_text": cleaned_response},
            impact={"context_used": bool(career_context)},
        )
        append_progress_event(data.user_id, serialize_journey_event(event))
        append_chat_turn(data.user_id, user_update, cleaned_response, intent)
        if is_weekly_agent and intent == "tutor_chat" and len(cleaned_response) > 80:
            from app.services.user_context_store import append_qa
            append_qa(data.user_id, user_update, cleaned_response)
        return ChatResponse(response=cleaned_response, context=user_context, updated_actions=returned_actions)
    except Exception as exc:
        logger.error("chat endpoint failed for %s: %s", data.user_id, exc, exc_info=True)
        error_msg = "Sorry, something went wrong on my end. Please try again in a moment."
        append_chat_turn(data.user_id, user_update, error_msg, intent)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stream")
@limiter.limit("20/minute")
def chat_stream(
    request: Request,
    data: ChatRequest,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(None),
    authorization: str | None = Header(None),
):
    """Server-Sent-Events variant of the general assistant chat.

    Streams the LLM reply token-by-token so the UI doesn't block on the full
    3-10s generation. Only the general (non weekly-agent) path is streamed; the
    action-capable Agent 2 path emits `event: fallback` so the client uses the
    unchanged /message endpoint. /message itself is not modified.
    """
    verify_resource_owner(data.user_id, x_user_id=x_user_id, authorization=authorization)

    # The weekly-agent path mutates the plan and parses action JSON — keep it on
    # the structured /message endpoint.
    if "Agent 2 weekly plan discussion" in data.message:
        def _fallback():
            yield "event: fallback\ndata: {}\n\n"
        return StreamingResponse(_fallback(), media_type="text/event-stream")

    user = db.query(User).filter(User.id == data.user_id).first()
    skills = db.query(SkillNode).filter(SkillNode.user_id == data.user_id).all()
    user_context = f"User: {user.name if user else 'Unknown'}, Target: {user.target_role if user else 'N/A'}"

    try:
        career_context = compile_career_context(db, data.user_id)
    except Exception:
        career_context = {}

    skills_context = ", ".join([f"{s.name} ({s.proficiency}/10)" for s in skills]) if skills else "No skills yet"
    profile_context = profile_as_context_string(data.user_id)
    persistent_context = memory_context_text(data.user_id)
    date_context = _date_context_text(_parse_date_reference(data.message))
    context_json = json.dumps(career_context, default=str)[:8000]

    # Same persona/prompt as the non-weekly branch of /message.
    role_prompt = """You are delta, the central AI assistant inside a personalized Career OS.
Use the user's Career Memory, Roadmap State, Market Pulse, Journey Log, Proof Projects, and Portfolio Assessment.
Be honest, specific, and action-oriented. If the user is drifting, say it clearly but supportively."""
    prompt = f"""{role_prompt}

The user is:
{user_context}
Skills: {skills_context}
Profile / resume context:
{profile_context}

Date/time context:
{date_context}

Persistent Agent 2 files:
{persistent_context}

Career OS Context JSON:
{context_json}

User message: {data.message}

Respond with a practical next step, mention relevant roadmap/project/market context when useful, and ask at most one follow-up question."""

    def _event_stream():
        from app.services.ai_service import generate_response_stream, quality_model
        chunks: list[str] = []
        try:
            for piece in generate_response_stream(prompt, temperature=0.7, max_tokens=10000, model=quality_model()):
                if piece:
                    chunks.append(piece)
                    yield f"data: {json.dumps({'delta': piece})}\n\n"
        except Exception as exc:
            logger.error("chat stream generation failed for %s: %s", data.user_id, exc)

        full = "".join(chunks).strip() or "Sorry, something went wrong on my end. Please try again in a moment."

        # Persist the turn identically to the /message non-weekly path.
        try:
            event = log_journey_event(
                db=db,
                user_id=data.user_id,
                event_type="assistant_guidance",
                summary=f"delta answered career question: {data.message[:120]}",
                evidence={"message": data.message, "response_text": full},
                impact={"context_used": bool(career_context)},
            )
            append_progress_event(data.user_id, serialize_journey_event(event))
            append_chat_turn(data.user_id, data.message, full, "chat")
        except Exception as exc:
            logger.error("chat stream persist failed for %s: %s", data.user_id, exc)

        yield f"event: done\ndata: {json.dumps({'response': full, 'context': user_context})}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@router.get("/history/{user_id}")
def chat_history(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    events = db.query(JourneyEvent).filter(
        JourneyEvent.user_id == user_id,
        JourneyEvent.event_type == "assistant_guidance",
    ).order_by(JourneyEvent.created_at.desc()).limit(10).all()
    messages = []
    for event in reversed(events):
        payload = json.loads(event.evidence or "{}")
        user_msg = payload.get("message", "")
        # Prefer stored response_text; fall back to summary only if it doesn't look like a meta-description
        assistant_msg = payload.get("response_text") or (
            event.summary if not event.summary.startswith("delta answered career question:") else ""
        )
        if user_msg:
            messages.append({"role": "user", "content": user_msg})
        if assistant_msg:
            messages.append({"role": "assistant", "content": assistant_msg})
    return {"messages": messages}


@router.post("/onboarding/start", response_model=OnboardingStartResponse)
def onboarding_start(data: OnboardingStartRequest):
    res = start_onboarding(data.raw_input, data.target_role)
    return OnboardingStartResponse(
        ambition_summary=res.get("ambition_summary", "Aspirations loaded."),
        adaptive_questions=res.get("adaptive_questions", []),
        market_demand_focus=res.get("market_demand_focus", ""),
        market_snapshot=res.get("market_snapshot", {}),
    )


@router.post("/onboarding/finalize", response_model=OnboardingFinalizeResponse)
def onboarding_finalize(data: OnboardingFinalizeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile_data = finalize_onboarding(data.raw_input, data.adaptive_questions, data.answers)

    user.target_role = profile_data.get("ambitions", user.target_role)
    user.hours_per_week = profile_data.get("hours_per_week", user.hours_per_week)
    user.learning_style = profile_data.get("learning_style", user.learning_style)
    user.updated_at = datetime.datetime.utcnow()

    profile = db.query(PersonalizationProfile).filter(PersonalizationProfile.user_id == data.user_id).first()
    raw_intake_payload = {
        "raw_input": data.raw_input,
        "adaptive_questions": data.adaptive_questions,
        "answers": data.answers,
    }

    if not profile:
        profile = PersonalizationProfile(
            id=str(uuid.uuid4()),
            user_id=data.user_id,
            raw_intake=json.dumps(raw_intake_payload),
            structured_profile=json.dumps(profile_data),
            ai_questions_asked=json.dumps(data.adaptive_questions),
            created_at=datetime.datetime.utcnow(),
            last_updated=datetime.datetime.utcnow(),
        )
        db.add(profile)
    else:
        profile.raw_intake = json.dumps(raw_intake_payload)
        profile.structured_profile = json.dumps(profile_data)
        profile.ai_questions_asked = json.dumps(data.adaptive_questions)
        profile.last_updated = datetime.datetime.utcnow()

    for skill_name in profile_data.get("extracted_skills", []):
        existing_skill = db.query(SkillNode).filter(
            SkillNode.user_id == data.user_id,
            SkillNode.name.ilike(skill_name),
        ).first()
        if not existing_skill:
            db.add(SkillNode(
                id=str(uuid.uuid4()),
                user_id=data.user_id,
                name=skill_name,
                category="core",
                proficiency=3,
                evidence_type="claimed",
                evidence_weight=0.4,
                last_updated=datetime.datetime.utcnow(),
                created_at=datetime.datetime.utcnow(),
            ))

    db.commit()
    db.refresh(user)
    career_os = initialize_career_os_for_user(
        db=db,
        user_id=data.user_id,
        source="ai_adaptive_onboarding",
        structured=profile_data,
    )

    return OnboardingFinalizeResponse(
        status="success",
        profile=profile_data,
        career_os=career_os,
    )
