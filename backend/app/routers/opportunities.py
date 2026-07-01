"""Opportunities router — AI-matched jobs & internships.

Owner-scoped. Persists per-user preferences and the last AI-generated board so
the page loads instantly, and regenerates on demand (or when preferences change).
"""
from __future__ import annotations

import datetime
import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.opportunity_board import OpportunityBoard
from app.dependencies.auth import require_owner
from app.services.opportunity_ai import generate_opportunities, profile_signature

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

DEFAULT_PREFERENCES = {
    "location": "",
    "role_types": ["internship", "full_time"],
    "work_mode": "any",
    "industries": "",
    "notes": "",
}


class PreferencesPayload(BaseModel):
    location: Optional[str] = None
    role_types: Optional[List[str]] = None
    work_mode: Optional[str] = None
    industries: Optional[str] = None
    notes: Optional[str] = None


def _get_or_create(db: Session, user_id: str) -> OpportunityBoard:
    board = db.query(OpportunityBoard).filter(OpportunityBoard.user_id == user_id).first()
    if not board:
        board = OpportunityBoard(
            id=str(uuid.uuid4()),
            user_id=user_id,
            preferences=json.dumps(DEFAULT_PREFERENCES),
        )
        db.add(board)
        db.commit()
        db.refresh(board)
    return board


def _load_prefs(board: OpportunityBoard) -> dict:
    try:
        return {**DEFAULT_PREFERENCES, **(json.loads(board.preferences) if board.preferences else {})}
    except Exception:
        return dict(DEFAULT_PREFERENCES)


def _serialize(board: OpportunityBoard, user_id: str) -> dict:
    try:
        opportunities = json.loads(board.opportunities) if board.opportunities else []
    except Exception:
        opportunities = []
    current_sig = profile_signature(user_id)
    return {
        "preferences": _load_prefs(board),
        "opportunities": opportunities,
        "generated_at": board.generated_at.isoformat() if board.generated_at else None,
        # True when the profile changed since these were generated (worth refreshing).
        "stale": bool(opportunities) and board.profile_signature != current_sig,
    }


@router.get("/{user_id}")
def get_board(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Return stored preferences + last generated suggestions (fast, no LLM call)."""
    board = _get_or_create(db, user_id)
    return _serialize(board, user_id)


@router.put("/{user_id}/preferences")
def update_preferences(
    user_id: str,
    payload: PreferencesPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    """Save the user's opportunity preferences."""
    board = _get_or_create(db, user_id)
    prefs = _load_prefs(board)
    incoming = {k: v for k, v in payload.model_dump().items() if v is not None}
    prefs.update(incoming)
    board.preferences = json.dumps(prefs)
    db.commit()
    db.refresh(board)
    return _serialize(board, user_id)


@router.post("/{user_id}/generate")
def generate_board(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Regenerate suggestions from the current profile + saved preferences (LLM call)."""
    board = _get_or_create(db, user_id)
    prefs = _load_prefs(board)
    opportunities = generate_opportunities(user_id, prefs)
    board.opportunities = json.dumps(opportunities)
    board.profile_signature = profile_signature(user_id)
    board.generated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(board)
    return _serialize(board, user_id)
