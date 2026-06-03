"""
Ingestion Router v2 — Clean API endpoints for the new ingestion engine.
Uses IngestionEngineV2 which reads/writes from profile_store JSON files.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
import json
import logging
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional

logger = logging.getLogger("delta.ingestion_router")

from app.database import get_db
from app.services.ingestion_engine_v2 import engine
from app.services.profile_store import load_profile, save_profile, profile_as_context_string

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


class StartSessionRequest(BaseModel):
    user_id: str
    journey_type: str = "general"


class AnswerRequest(BaseModel):
    user_id: str
    session_id: str
    answer: str


class BridgeRequest(BaseModel):
    user_id: str
    raw_text: str
    source: str = "resume"


class ResumeIngestionRequest(BaseModel):
    user_id: str
    session_id: str
    resume_text: str


@router.post("/start")
def start_ingestion_session(payload: StartSessionRequest, db: Session = Depends(get_db)):
    """Start or resume an intake session for a user."""
    try:
        session = engine.start_session(db, payload.user_id, payload.journey_type)
        conversation = json.loads(session.conversation_log or "[]")
        initial_question = next(
            (m["content"] for m in conversation if m["role"] == "assistant"), None
        )
        return {
            "session_id": session.id,
            "user_id": session.user_id,
            "status": session.status,
            "journey_type": session.journey_type,
            "current_round": session.current_round,
            "confidence_score": session.confidence_score,
            "initial_question": initial_question,
            "message": initial_question,
            "conversation": [m for m in conversation if m["role"] in ("assistant", "user")]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.post("/answer")
def submit_ingestion_answer(payload: AnswerRequest, db: Session = Depends(get_db)):
    """Submit one user reply and get the next question or completion."""
    try:
        result = engine.process_answer(db, payload.user_id, payload.session_id, payload.answer)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {str(e)}")


@router.post("/resume")
def ingest_resume(payload: ResumeIngestionRequest, db: Session = Depends(get_db)):
    """Dedicated endpoint for resume text ingestion — extracts all fields and returns follow-up."""
    try:
        result = engine.ingest_resume(db, payload.user_id, payload.session_id, payload.resume_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume ingestion failed: {str(e)}")


@router.post("/bridge")
def bridge_personal_data(payload: BridgeRequest, db: Session = Depends(get_db)):
    """Personal Data Bridge: ingest unstructured text (resume, LinkedIn) into profile."""
    try:
        from app.models.semantic_memory import IngestionSession
        session = db.query(IngestionSession).filter(
            IngestionSession.user_id == payload.user_id,
            IngestionSession.status == "active"
        ).order_by(IngestionSession.created_at.desc()).first()

        if not session:
            # Auto-create a session for bridge use
            session = engine.start_session(db, payload.user_id)

        result = engine.ingest_resume(db, payload.user_id, session.id, payload.raw_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bridge failed: {str(e)}")


@router.get("/state/{user_id}")
def get_ingestion_state(user_id: str, db: Session = Depends(get_db)):
    """Get current ingestion state, profile completeness, and collected data."""
    try:
        return engine.get_state(db, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load state: {str(e)}")


@router.get("/profile/{user_id}")
def get_profile(user_id: str):
    """Get the full profile JSON for a user (read by all agents)."""
    profile = load_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found for this user.")
    return profile


@router.put("/profile/{user_id}")
def update_profile(user_id: str, updates: Dict[str, Any] = Body(...)):
    """Manually update specific profile fields."""
    try:
        merged = save_profile(user_id, updates)
        return {"status": "updated", "profile": merged}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")


@router.post("/complete/{user_id}")
def force_complete_ingestion(user_id: str, db: Session = Depends(get_db)):
    """Force-complete intake and save whatever has been collected."""
    try:
        result = engine.force_complete(db, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Force complete failed: {str(e)}")


@router.post("/reset/{user_id}")
def reset_ingestion(user_id: str, db: Session = Depends(get_db)):
    """
    Fully reset a user's intake profile:
      1. Delete the profile JSON file from disk.
      2. Mark all existing IngestionSessions as 'reset' (closed).
      3. Start a brand-new session and return the opening question.
    """
    import pathlib

    # 1. Delete profile JSON
    try:
        from app.services.profile_store import _profile_path
        profile_path = _profile_path(user_id)
        if profile_path.exists():
            profile_path.unlink()
            logger.info(f"[RESET] Deleted profile file for user {user_id}")
    except Exception as e:
        logger.warning(f"[RESET] Could not delete profile file: {e}")

    # 2. Close existing sessions
    try:
        from app.models.semantic_memory import IngestionSession
        old_sessions = db.query(IngestionSession).filter(
            IngestionSession.user_id == user_id
        ).all()
        for s in old_sessions:
            s.status = "reset"
        db.commit()
        logger.info(f"[RESET] Closed {len(old_sessions)} old sessions for user {user_id}")
    except Exception as e:
        logger.warning(f"[RESET] Could not close old sessions: {e}")
        db.rollback()

    # 3. Start fresh session
    try:
        session = engine.start_session(db, user_id, "general")
        conversation = json.loads(session.conversation_log or "[]")
        initial_question = next(
            (m["content"] for m in conversation if m["role"] == "assistant"), None
        )
        return {
            "status": "reset_complete",
            "session_id": session.id,
            "user_id": user_id,
            "message": initial_question,
            "conversation": [m for m in conversation if m["role"] in ("assistant", "user")]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed during session creation: {str(e)}")

