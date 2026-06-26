import logging
from fastapi import APIRouter, Depends, HTTPException

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


@router.post("/user/{user_id}/consolidate-memory")
def run_memory_consolidation(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    try:
        return run_memory_consolidation_cycle(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _log.error("consolidate-memory failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Memory consolidation failed: {exc}") from exc
