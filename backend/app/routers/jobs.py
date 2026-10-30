"""Job match API: analyse a pasted job description, keep it, and turn gaps into tasks."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_owner
from app.limiter import limiter
from app.services import job_match, usage_caps

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class AnalysePayload(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class AddPayload(BaseModel):
    skills: list[str] = Field(min_length=1, max_length=job_match.ADD_TO_WEEK_MAX)


class PlanPayload(BaseModel):
    on: bool = True


def _run(fn, *args):
    try:
        return fn(*args)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{user_id}")
def my_jobs(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return {"jobs": job_match.listing(db, user_id)}


@router.post("/{user_id}/analyse")
@limiter.limit("10/hour")  # each new job text costs one model call
def analyse(request: Request, user_id: str, payload: AnalysePayload, db: Session = Depends(get_db),
            _: str = Depends(require_owner)):
    with usage_caps.using(db, user_id, "job_match"):
        return _run(job_match.analyse, db, user_id, payload.text)


@router.get("/{user_id}/{target_id}")
def one_job(user_id: str, target_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return _run(job_match.get, db, user_id, target_id)


@router.post("/{user_id}/{target_id}/add-to-week")
@limiter.limit("20/minute")
def add_to_week(request: Request, user_id: str, target_id: str, payload: AddPayload, db: Session = Depends(get_db),
                _: str = Depends(require_owner)):
    return _run(job_match.add_to_week, db, user_id, target_id, payload.skills)


@router.post("/{user_id}/{target_id}/plan")
@limiter.limit("20/minute")
def plan_around(request: Request, user_id: str, target_id: str, payload: PlanPayload, db: Session = Depends(get_db),
                _: str = Depends(require_owner)):
    return _run(job_match.plan_around, db, user_id, target_id, payload.on)


@router.delete("/{user_id}/{target_id}")
def delete_job(user_id: str, target_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    _run(job_match.delete, db, user_id, target_id)
    return {"ok": True}
