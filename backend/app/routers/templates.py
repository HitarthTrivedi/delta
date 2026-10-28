"""Predefined role roadmaps: the catalog, an outline of each, and starting or
stopping one for yourself. A college-assigned roadmap can't be stopped."""
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import current_identity, require_owner
from app.limiter import limiter
from app.models import MarketSnapshot, RoadmapState, User
from app.services import roadmap_templates
from app.services.domain_packs import field_for_user

router = APIRouter(prefix="/api/templates", tags=["templates"])


class StartPayload(BaseModel):
    template_id: str
    target_date: Optional[datetime.date] = None


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _state(db: Session, user_id: str) -> dict:
    e = roadmap_templates.active_enrollment(db, user_id)
    return {
        "catalog": roadmap_templates.catalog(field_for_user(user_id, db=db)["id"]),
        "current": roadmap_templates.progress(db, e),
        "can_change": not (e and e.assigned_by_batch_id),
    }


def _replan_this_week(db: Session, user_id: str) -> None:
    """Rebuild the current week from the roadmap (no AI call), if a plan exists yet."""
    from app.services.central_engine import get_or_create_roadmap_state
    user = db.get(User, user_id)
    market = (db.query(MarketSnapshot).filter(MarketSnapshot.user_id == user_id)
              .order_by(MarketSnapshot.created_at.desc()).first())
    if user and market and db.query(RoadmapState).filter(RoadmapState.user_id == user_id).first():
        get_or_create_roadmap_state(db, user, market, regenerate=True)


@router.get("")
def all_templates(_=Depends(current_identity)):
    return {"catalog": roadmap_templates.catalog()}


@router.get("/user/{user_id}")
def my_roadmap(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return _state(db, user_id)


@router.get("/{template_id}")
def template_outline(template_id: str, _=Depends(current_identity)):
    return _run(roadmap_templates.outline, template_id)


@router.post("/user/{user_id}/start")
@limiter.limit("10/minute")
def start_roadmap(request: Request, user_id: str, payload: StartPayload, db: Session = Depends(get_db),
                  _: str = Depends(require_owner)):
    _run(roadmap_templates.start, db, user_id, payload.template_id, payload.target_date)
    _replan_this_week(db, user_id)
    return _state(db, user_id)


@router.post("/user/{user_id}/stop")
def stop_roadmap(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    _run(roadmap_templates.stop, db, user_id)
    return _state(db, user_id)
