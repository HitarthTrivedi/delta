from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, SkillNode
from app.services.calendar_service import generate_upcoming_events
from app.services.opportunity_adapters import get_source_statuses

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/sources", response_model=list)
def get_calendar_sources():
    return get_source_statuses()

@router.get("/events", response_model=list)
def get_calendar_events(
    user_id: str,
    days_ahead: int = 30,
    sources: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Exposes a dynamic calendar of coding contests, hackathons, and machine learning sprints.
    Matches events against the student's active SkillNode list and ranks them by skill-match percent.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    user_skill_names = [s.name for s in skills]

    source_list = [source.strip() for source in sources.split(",")] if sources else None
    events = generate_upcoming_events(
        user_skill_names,
        days_ahead=days_ahead,
        target_role=user.target_role,
        sources=source_list,
    )
    return events
