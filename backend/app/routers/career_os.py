import json
import logging
import re
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

_log = logging.getLogger("delta.career_os")
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_owner
from app.models import (
    CareerMemoryProfile,
    IngestionSession,
    JourneyEvent,
    MarketSnapshot,
    RoadmapState,
    SemanticNodeModel,
    TensionNodeModel,
    User,
)
from app.services.central_engine import (
    compile_career_context,
    initialize_career_os_for_user,
    log_journey_event,
    refresh_roadmap_with_ai,
    run_memory_consolidation_cycle,
    run_weekly_career_cycle,
    serialize_journey_event,
)
from app.services.domain_packs import get_domain_pack, list_domain_packs
from app.services.agent2_memory import append_progress_event

router = APIRouter(prefix="/api/career-os", tags=["career-os"])


class JourneyEventCreate(BaseModel):
    event_type: str = Field(..., examples=["task_completed", "user_reflection", "ai_decision"])
    summary: str
    evidence: dict = Field(default_factory=dict)
    impact: dict = Field(default_factory=dict)


class CareerOSInitializeRequest(BaseModel):
    source: str = "manual_onboarding"
    structured: dict = Field(default_factory=dict)


@router.get("/domain-packs")
def get_domain_packs():
    return list_domain_packs()


@router.get("/system-status")
def get_system_status(db: Session = Depends(get_db)):
    active_tensions = db.query(TensionNodeModel).filter(
        TensionNodeModel.status.in_(["active", "challenged"])
    ).count()
    return {
        "status": "operational",
        "users": db.query(User).count(),
        "modules": {
            "adaptive_ingestion": {
                "ready": True,
                "sessions": db.query(IngestionSession).count(),
            },
            "semantic_memory": {
                "ready": True,
                "nodes": db.query(SemanticNodeModel).count(),
                "active_tensions": active_tensions,
            },
            "career_os": {
                "ready": True,
                "memory_profiles": db.query(CareerMemoryProfile).count(),
                "roadmaps": db.query(RoadmapState).count(),
                "journey_events": db.query(JourneyEvent).count(),
            },
            "market_pulse": {
                "ready": True,
                "snapshots": db.query(MarketSnapshot).count(),
            },
            "opportunity_engine": {
                "ready": True,
                "domain_packs": len(list_domain_packs()),
            },
        },
    }


@router.get("/domain-packs/{domain_id}")
def get_domain_pack_by_id(domain_id: str):
    return get_domain_pack(domain_id)


@router.get("/user/{user_id}/context")
def get_career_context(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    try:
        return compile_career_context(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        _log.error("compile_career_context failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not load career context: {exc}") from exc


@router.post("/user/{user_id}/initialize")
def initialize_career_os(user_id: str, payload: CareerOSInitializeRequest, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    try:
        return initialize_career_os_for_user(
            db=db,
            user_id=user_id,
            source=payload.source,
            structured=payload.structured,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _log.error("initialize_career_os failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Career OS initialization failed: {exc}") from exc


@router.post("/user/{user_id}/journey")
def create_journey_event(user_id: str, payload: JourneyEventCreate, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    try:
        event = log_journey_event(
            db=db,
            user_id=user_id,
            event_type=payload.event_type,
            summary=payload.summary,
            evidence=payload.evidence,
            impact=payload.impact,
        )
        serialized = serialize_journey_event(event)
        append_progress_event(user_id, serialized)
        return serialized
    except Exception as exc:
        _log.error("log_journey_event failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not save event: {exc}") from exc


@router.post("/user/{user_id}/weekly-cycle")
def run_weekly_cycle(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    try:
        return run_weekly_career_cycle(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _log.error("weekly-cycle failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent 2 hit an error generating your next week: {exc}") from exc


class TaskDetailRequest(BaseModel):
    task_title: str
    task_description: str = ""
    skill: str = ""


@router.post("/user/{user_id}/task-detail")
def get_task_detail(user_id: str, payload: TaskDetailRequest, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Generate a detailed how-to breakdown for a specific task using AI."""
    try:
        from app.services.ai_service import generate_response
        user = db.query(User).filter(User.id == user_id).first()
        target_role = (user.target_role if user else None) or "Software Engineer"

        prompt = f"""You are Delta's task execution guide. A student needs a specific, actionable breakdown to complete this career task.

TASK: {payload.task_title}
CONTEXT: {payload.task_description}
SKILL FOCUS: {payload.skill or "General"}
USER'S TARGET ROLE: {target_role}

Return ONLY a raw JSON object (no markdown, no code fences, no explanation):
{{
  "how_to_start": "One specific sentence: what to open, install, or do in the next 5 minutes",
  "steps": [
    "Step 1: exact action with a tool/platform/command",
    "Step 2: ...",
    "Step 3: ...",
    "Step 4: ..."
  ],
  "resources": [
    {{
      "title": "Exact resource name",
      "url": "https://real-url.com",
      "type": "course|docs|video|practice|tool",
      "duration": "e.g. 8 hours, 3 weeks, 2 months",
      "why": "One sentence on why this resource for this task"
    }}
  ],
  "estimated_hours": 6,
  "timeline_note": "If any resource is long (weeks/months), specify exactly which sections or modules to complete THIS week. E.g. 'This course is 8 weeks — complete Week 1 and 2 only (approx 6 hours).'",
  "proof_output": "Exactly what should exist when this task is done: a file, a GitHub repo, a running app, a written note, etc.",
  "pro_tip": "One non-obvious expert insight specific to this task that most beginners miss"
}}

Critical rules:
- ALL resource URLs must be real and specific (coursera.org, roadmap.sh, docs.python.org, leetcode.com, neetcode.io, kaggle.com, etc.)
- If a course takes more than 2 weeks, set timeline_note to tell the student exactly which part to do this week
- Steps must be concrete (what to type, what to click, what to build) not vague
- estimated_hours should reflect one week of honest work at the stated skill level"""

        raw = generate_response(prompt, temperature=0.4, max_tokens=1500)
        clean = raw.strip()
        # Strip markdown code fences if the model adds them
        clean = re.sub(r"^```[a-z]*\n?", "", clean)
        clean = re.sub(r"\n?```$", "", clean.strip())
        return json.loads(clean.strip())
    except json.JSONDecodeError as exc:
        _log.warning("task-detail JSON parse error for %s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="AI returned malformed detail. Try again.") from exc
    except Exception as exc:
        _log.error("task-detail failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not generate task detail: {exc}") from exc


@router.post("/user/{user_id}/consolidate-memory")
def run_memory_consolidation(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    try:
        return run_memory_consolidation_cycle(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _log.error("consolidate-memory failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Memory consolidation failed: {exc}") from exc
