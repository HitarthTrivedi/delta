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
        from app.services.ai_service import generate_json
        user = db.query(User).filter(User.id == user_id).first()
        target_role = (user.target_role if user else None) or "Software Engineer"

        context = f"{payload.task_description[:300]}" if payload.task_description else ""
        prompt = (
            f"Task: {payload.task_title}. Skill: {payload.skill or 'General'}. Role: {target_role}. {context}\n\n"
            "Return ONLY this JSON, no markdown:\n"
            '{"how_to_start":"one sentence","steps":["s1","s2","s3"],'
            '"resources":[{"title":"name","url":"https://real.com","type":"course","duration":"Xh","why":"reason"}],'
            '"estimated_hours":5,"timeline_note":"which part this week if long","proof_output":"what exists when done",'
            '"pro_tip":"expert insight"}\n\n'
            "Use real URLs (leetcode.com, coursera.org, roadmap.sh, docs.python.org). Steps must be concrete actions."
        )

        detail = generate_json(prompt, temperature=0.3)

        if not detail or not isinstance(detail, dict):
            raise HTTPException(status_code=500, detail="AI returned an empty response. Try again.")

        return detail
    except HTTPException:
        raise
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


# ── Context Docs (permanent rules + next-week requests) ───────────────────────

class TimedRequest(BaseModel):
    text: str
    weeks_remaining: int = 1


class ContextDocsUpdate(BaseModel):
    permanent: list[str] = Field(default_factory=list)
    next_week: list[TimedRequest] = Field(default_factory=list)


@router.get("/user/{user_id}/context-docs")
def get_context_docs(user_id: str, _: str = Depends(require_owner)):
    try:
        from app.services.user_context_store import get_permanent_instructions, get_next_week_requests
        return {
            "permanent": get_permanent_instructions(user_id),
            "next_week": get_next_week_requests(user_id),  # [{text, weeks_remaining}]
        }
    except Exception as exc:
        _log.error("get_context_docs failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/user/{user_id}/context-docs")
def update_context_docs(user_id: str, payload: ContextDocsUpdate, _: str = Depends(require_owner)):
    try:
        from app.services.user_context_store import set_permanent_instructions, set_next_week_requests
        set_permanent_instructions(user_id, [s.strip() for s in payload.permanent if s.strip()])
        set_next_week_requests(user_id, [r.dict() for r in payload.next_week if r.text.strip()])
        return {"status": "saved"}
    except Exception as exc:
        _log.error("update_context_docs failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Manual weekly-task override ────────────────────────────────────────────────

class WeeklyTasksUpdate(BaseModel):
    tasks: list[dict]


@router.put("/user/{user_id}/weekly-tasks")
def update_weekly_tasks(user_id: str, payload: WeeklyTasksUpdate, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    try:
        roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == user_id).first()
        if not roadmap:
            raise HTTPException(status_code=404, detail="No roadmap found for user.")
        import json as _json
        weekly_focus = json.loads(roadmap.weekly_focus) if roadmap.weekly_focus else {}
        weekly_focus["primary_actions"] = payload.tasks
        roadmap.weekly_focus = _json.dumps(weekly_focus)
        db.commit()
        from app.services.agent2_memory import sync_current_week
        sync_current_week(user_id, {"roadmap": {"weekly_focus": weekly_focus}}, payload.tasks, reason="Manual task edit by user.")
        return {"status": "saved", "tasks": payload.tasks}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        _log.error("update_weekly_tasks failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
