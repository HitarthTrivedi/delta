"""Daily habit API: streak, XP, level, daily goal, break mode."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_owner
from app.limiter import limiter
from app.services import engagement

router = APIRouter(prefix="/api/engagement", tags=["engagement"])


class SettingsPayload(BaseModel):
    timezone: Optional[str] = Field(default=None, max_length=64)
    goal_minutes: Optional[int] = None
    study_time: Optional[str] = Field(default=None, max_length=5)  # "HH:MM", "" clears
    reminder_channel: Optional[str] = None


class BreakPayload(BaseModel):
    days: int = Field(ge=1, le=engagement.BREAK_DAYS_PER_MONTH)


@router.get("/{user_id}")
def get_engagement(user_id: str, tz: Optional[str] = None, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    # `tz` (the browser's timezone) is only used the first time, to set up the account.
    return engagement.summary(db, user_id, timezone=tz)


@router.put("/{user_id}")
@limiter.limit("30/minute")
def put_settings(request: Request, user_id: str, payload: SettingsPayload, db: Session = Depends(get_db),
                 _: str = Depends(require_owner)):
    try:
        return engagement.update_settings(
            db, user_id, timezone=payload.timezone, goal_minutes=payload.goal_minutes,
            study_time=payload.study_time, reminder_channel=payload.reminder_channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{user_id}/break")
@limiter.limit("10/minute")
def start_break(request: Request, user_id: str, payload: BreakPayload, db: Session = Depends(get_db),
                _: str = Depends(require_owner)):
    try:
        return engagement.start_break(db, user_id, payload.days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{user_id}/break")
def end_break(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return engagement.end_break(db, user_id)
