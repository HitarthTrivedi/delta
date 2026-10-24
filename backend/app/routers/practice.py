"""Quick 5: the 5-question daily spaced review."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_owner
from app.limiter import limiter
from app.services import quick_practice

router = APIRouter(prefix="/api/practice/quick", tags=["quick-practice"])


class AnswerPayload(BaseModel):
    item_id: str = Field(min_length=1, max_length=64)
    choice: int = Field(ge=0, le=3)


@router.get("/{user_id}")
@limiter.limit("20/minute")
def get_today(request: Request, user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    try:
        return quick_practice.todays_set(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{user_id}/answer")
@limiter.limit("60/minute")
def post_answer(request: Request, user_id: str, payload: AnswerPayload, db: Session = Depends(get_db),
                _: str = Depends(require_owner)):
    try:
        return quick_practice.answer(db, user_id, payload.item_id, payload.choice)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
