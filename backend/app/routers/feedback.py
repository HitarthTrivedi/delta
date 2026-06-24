from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
import uuid
import datetime

from app.database import get_db
from app.models.feedback import Feedback

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    message: str
    rating: Optional[int] = None
    source: str = "feedback"
    meta: Optional[dict] = None


@router.post("")
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    entry = Feedback(
        id=str(uuid.uuid4()),
        name=payload.name,
        email=payload.email,
        message=payload.message,
        rating=payload.rating,
        source=payload.source,
        meta=json.dumps(payload.meta) if payload.meta else None,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    return {"status": "received", "id": entry.id}


@router.get("")
def list_feedback(db: Session = Depends(get_db)):
    rows = db.query(Feedback).order_by(Feedback.created_at.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "email": r.email,
            "message": r.message,
            "rating": r.rating,
            "source": r.source,
            "meta": json.loads(r.meta) if r.meta else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
