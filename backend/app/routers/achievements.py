"""Achievements router — the user's trophy cabinet.

Owner-scoped CRUD for manually tracked certificates, projects, and awards.
"""
from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.achievement import Achievement
from app.dependencies.auth import require_owner

router = APIRouter(prefix="/api/achievements", tags=["achievements"])

ALLOWED_TYPES = {"certificate", "project", "award", "course", "other"}


class AchievementPayload(BaseModel):
    type: str = "certificate"
    title: str = Field(..., min_length=1)
    organization: Optional[str] = None
    date_achieved: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None


def _serialize(a: Achievement) -> dict:
    return {
        "id": a.id,
        "type": a.type,
        "title": a.title,
        "organization": a.organization,
        "date_achieved": a.date_achieved,
        "url": a.url,
        "description": a.description,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/{user_id}")
def list_achievements(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """List a user's achievements, newest first."""
    rows = (
        db.query(Achievement)
        .filter(Achievement.user_id == user_id)
        .order_by(Achievement.created_at.desc())
        .all()
    )
    return {"achievements": [_serialize(r) for r in rows]}


@router.post("/{user_id}")
def create_achievement(
    user_id: str,
    payload: AchievementPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    """Add a new achievement to the user's trophy cabinet."""
    a_type = payload.type if payload.type in ALLOWED_TYPES else "other"
    entry = Achievement(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=a_type,
        title=payload.title.strip(),
        organization=(payload.organization or "").strip() or None,
        date_achieved=(payload.date_achieved or "").strip() or None,
        url=(payload.url or "").strip() or None,
        description=(payload.description or "").strip() or None,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"status": "created", "achievement": _serialize(entry)}


@router.delete("/{user_id}/{achievement_id}")
def delete_achievement(
    user_id: str,
    achievement_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    """Remove an achievement the user owns."""
    entry = (
        db.query(Achievement)
        .filter(Achievement.id == achievement_id, Achievement.user_id == user_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Achievement not found.")
    db.delete(entry)
    db.commit()
    return {"status": "deleted", "id": achievement_id}
