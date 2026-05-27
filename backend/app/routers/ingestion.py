"""
Ingestion Router — API endpoints for multi-round ingestion, tensions, and personal data bridging.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional

from app.database import get_db
from app.services.ingestion_engine import IngestionEngine
from app.models.semantic_memory import IngestionSession
from app.services.memory_graph import MemoryGraph

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])
engine = IngestionEngine()

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
    source: str = "linkedin"  # linkedin, github, resume

@router.post("/start")
def start_ingestion_session(payload: StartSessionRequest, db: Session = Depends(get_db)):
    """Initializes a new multi-round onboarding intake session for a student."""
    try:
        session = engine.start_session(db, payload.user_id, payload.journey_type)
        return {
            "session_id": session.id,
            "user_id": session.user_id,
            "status": session.status,
            "journey_type": session.journey_type,
            "current_round": session.current_round,
            "confidence_score": session.confidence_score,
            "conversation": [session.conversation_log] if session.conversation_log else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion session: {str(e)}")

@router.post("/answer")
def submit_ingestion_answer(payload: AnswerRequest, db: Session = Depends(get_db)):
    """Submits the student's latest response, updates their graph, and retrieves the next question."""
    try:
        result = engine.process_answer(db, payload.user_id, payload.session_id, payload.answer)
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process ingestion answer: {str(e)}")

@router.get("/state/{user_id}")
def get_ingestion_state(user_id: str, db: Session = Depends(get_db)):
    """Retrieves the current state of ingestion, graph metrics, and active tensions for the student."""
    try:
        # Load latest active session
        session = db.query(IngestionSession).filter(
            IngestionSession.user_id == user_id
        ).order_by(IngestionSession.created_at.desc()).first()
        
        graph = MemoryGraph.load_from_db(db, user_id)
        summary = graph.to_summary()
        
        # Load active tensions
        from app.models.semantic_memory import TensionNodeModel
        active_tensions = db.query(TensionNodeModel).filter(
            TensionNodeModel.user_id == user_id,
            TensionNodeModel.status == "active"
        ).all()
        
        return {
            "has_active_session": session is not None and session.status == "active",
            "session": {
                "id": session.id if session else None,
                "status": session.status if session else "none",
                "current_round": session.current_round if session else 0,
                "confidence_score": session.confidence_score if session else 0.0,
                "journey_type": session.journey_type if session else "general"
            } if session else None,
            "graph_summary": {
                "nodes_count": summary.get("total_nodes") or summary.get("nodes_count") or 0,
                "edges_count": summary.get("total_edges") or summary.get("edges_count") or 0,
                "skills": summary.get("skills") or summary.get("skill", {}).get("labels") or [],
                "ambitions": summary.get("ambitions") or summary.get("ambition", {}).get("labels") or []
            },
            "active_tensions": [
                {
                    "id": t.id,
                    "type": t.tension_type,
                    "claim": t.user_claim,
                    "reality": t.market_reality,
                    "severity": t.severity,
                    "challenge_question": t.challenge_question
                } for t in active_tensions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load ingestion state: {str(e)}")

@router.post("/bridge")
def bridge_personal_data(payload: BridgeRequest, db: Session = Depends(get_db)):
    """Personal Data Bridge: Ingests unstructured resume/LinkedIn texts and populates the graph."""
    try:
        result = engine.ingest_personal_data(db, payload.user_id, payload.raw_text, payload.source)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest personal data: {str(e)}")

@router.post("/complete/{user_id}")
def force_complete_ingestion(user_id: str, db: Session = Depends(get_db)):
    """Forces early completion of ingestion and materializes profile snapshot."""
    try:
        session = db.query(IngestionSession).filter(
            IngestionSession.user_id == user_id,
            IngestionSession.status == "active"
        ).order_by(IngestionSession.created_at.desc()).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="No active ingestion session found for this user.")
            
        graph = MemoryGraph.load_from_db(db, user_id)
        
        session.status = "completed"
        import datetime
        session.completed_at = datetime.datetime.utcnow()
        
        # Materialize final snapshot
        engine._materialize_career_snapshot(db, user_id, graph, session.confidence_score)
        db.commit()
        
        return {
            "status": "completed",
            "confidence_score": session.confidence_score,
            "message": "Session completed successfully."
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to force complete session: {str(e)}")
