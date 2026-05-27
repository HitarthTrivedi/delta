from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.central_engine import (
    compile_career_context,
    initialize_career_os_for_user,
    log_journey_event,
    run_weekly_career_cycle,
    serialize_journey_event,
)
from app.services.domain_packs import get_domain_pack, list_domain_packs

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


@router.get("/domain-packs/{domain_id}")
def get_domain_pack_by_id(domain_id: str):
    return get_domain_pack(domain_id)


@router.get("/user/{user_id}/context")
def get_career_context(user_id: str, db: Session = Depends(get_db)):
    try:
        return compile_career_context(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/user/{user_id}/initialize")
def initialize_career_os(user_id: str, payload: CareerOSInitializeRequest, db: Session = Depends(get_db)):
    try:
        return initialize_career_os_for_user(
            db=db,
            user_id=user_id,
            source=payload.source,
            structured=payload.structured,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/user/{user_id}/journey")
def create_journey_event(user_id: str, payload: JourneyEventCreate, db: Session = Depends(get_db)):
    event = log_journey_event(
        db=db,
        user_id=user_id,
        event_type=payload.event_type,
        summary=payload.summary,
        evidence=payload.evidence,
        impact=payload.impact,
    )
    return serialize_journey_event(event)


@router.post("/user/{user_id}/weekly-cycle")
def run_weekly_cycle(user_id: str, db: Session = Depends(get_db)):
    try:
        return run_weekly_career_cycle(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
