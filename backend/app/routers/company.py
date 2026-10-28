"""Company roadmaps API: approved recruiters build roadmaps and tests, Delta
admins review them, and students in that company's pool follow them."""
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_owner
from app.limiter import limiter
from app.models.compliance import Recruiter
from app.routers.recruiter import require_admin, require_approved_recruiter
from app.services import company_roadmaps as cr

router = APIRouter(prefix="/api/company", tags=["company"])


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class SkillsDraft(BaseModel):
    skills: list[str] = Field(min_length=1, max_length=cr.MAX_SKILLS)
    weeks: int = 8


class TextDraft(BaseModel):
    text: str = Field(min_length=40, max_length=20000)
    weeks: int = 8


class Milestone(BaseModel):
    id: Optional[str] = Field(default=None, max_length=80)
    title: str = Field(max_length=120)
    skill: str = Field(max_length=60)
    detail: str = Field(max_length=400)
    kind: str = "practice"
    url: Optional[str] = Field(default=None, max_length=500)
    link: Optional[str] = Field(default=None, max_length=200)


class RoadmapPayload(BaseModel):
    title: str = Field(max_length=120)
    role: Optional[str] = Field(default=None, max_length=120)
    summary: Optional[str] = Field(default=None, max_length=600)
    skills: list[str] = Field(min_length=1, max_length=cr.MAX_SKILLS)
    milestones: Optional[list[Milestone]] = Field(default=None, max_length=60)
    weeks: int = 8


class RoadmapUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)
    role: Optional[str] = Field(default=None, max_length=120)
    summary: Optional[str] = Field(default=None, max_length=600)
    skills: Optional[list[str]] = Field(default=None, max_length=cr.MAX_SKILLS)
    milestones: Optional[list[Milestone]] = Field(default=None, max_length=60)
    weeks: Optional[int] = None


class ReviewPayload(BaseModel):
    approve: bool
    note: Optional[str] = Field(default=None, max_length=600)


class TestPayload(BaseModel):
    topic: Optional[str] = Field(default=None, max_length=120)
    title: Optional[str] = Field(default=None, max_length=120)
    category: str = "technical"
    area: Optional[str] = None
    difficulty: str = "medium"
    num_questions: int = 10
    timed: bool = True
    due_date: Optional[datetime.date] = None


def _milestones(items):
    return [m.model_dump() for m in items] if items is not None else None


# ── recruiter ────────────────────────────────────────────────────────────────

@router.post("/drafts/skills")
def draft_from_skills(payload: SkillsDraft, _: Recruiter = Depends(require_approved_recruiter)):
    return _run(cr.draft_from_skills, payload.skills, payload.weeks)


@router.post("/drafts/text")
@limiter.limit("10/minute")
def draft_from_text(request: Request, payload: TextDraft, _: Recruiter = Depends(require_approved_recruiter),
                    db: Session = Depends(get_db)):
    return _run(cr.draft_from_text, db, payload.text, payload.weeks)


@router.get("/roadmaps")
def my_roadmaps(rec: Recruiter = Depends(require_approved_recruiter), db: Session = Depends(get_db)):
    return {"roadmaps": cr.my_roadmaps(db, rec)}


@router.post("/roadmaps")
@limiter.limit("20/minute")
def create_roadmap(request: Request, payload: RoadmapPayload, rec: Recruiter = Depends(require_approved_recruiter),
                   db: Session = Depends(get_db)):
    return _run(cr.create, db, rec, title=payload.title, role=payload.role, summary=payload.summary,
                skills=payload.skills, milestones=_milestones(payload.milestones), weeks=payload.weeks)


@router.get("/roadmaps/{roadmap_id}")
def get_roadmap(roadmap_id: str, rec: Recruiter = Depends(require_approved_recruiter), db: Session = Depends(get_db)):
    return _run(cr.get, db, rec, roadmap_id)


@router.patch("/roadmaps/{roadmap_id}")
def update_roadmap(roadmap_id: str, payload: RoadmapUpdate, rec: Recruiter = Depends(require_approved_recruiter),
                   db: Session = Depends(get_db)):
    fields = payload.model_dump()
    fields["milestones"] = _milestones(payload.milestones)
    return _run(cr.update, db, rec, roadmap_id, **fields)


@router.post("/roadmaps/{roadmap_id}/submit")
def submit_roadmap(roadmap_id: str, rec: Recruiter = Depends(require_approved_recruiter), db: Session = Depends(get_db)):
    return _run(cr.submit, db, rec, roadmap_id)


@router.post("/roadmaps/{roadmap_id}/archive")
def archive_roadmap(roadmap_id: str, rec: Recruiter = Depends(require_approved_recruiter), db: Session = Depends(get_db)):
    return _run(cr.archive, db, rec, roadmap_id)


@router.post("/roadmaps/{roadmap_id}/duplicate")
def duplicate_roadmap(roadmap_id: str, rec: Recruiter = Depends(require_approved_recruiter),
                      db: Session = Depends(get_db)):
    return _run(cr.duplicate, db, rec, roadmap_id)


@router.get("/roadmaps/{roadmap_id}/students")
def roadmap_students(roadmap_id: str, rec: Recruiter = Depends(require_approved_recruiter),
                     db: Session = Depends(get_db)):
    return _run(cr.members_for, db, rec, roadmap_id)


@router.get("/roadmaps/{roadmap_id}/students.csv")
@limiter.limit("30/minute")
def roadmap_students_csv(request: Request, roadmap_id: str, rec: Recruiter = Depends(require_approved_recruiter),
                         db: Session = Depends(get_db)):
    body = _run(cr.members_csv, db, rec, roadmap_id)
    return Response(content="﻿" + body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="roadmap-students.csv"',
                             "Cache-Control": "no-store"})


@router.get("/roadmaps/{roadmap_id}/tests")
def roadmap_tests(roadmap_id: str, rec: Recruiter = Depends(require_approved_recruiter), db: Session = Depends(get_db)):
    return {"tests": _run(cr.list_tests, db, rec, roadmap_id)}


@router.post("/roadmaps/{roadmap_id}/tests")
@limiter.limit("10/minute")
def add_test(request: Request, roadmap_id: str, payload: TestPayload, rec: Recruiter = Depends(require_approved_recruiter),
             db: Session = Depends(get_db)):
    return _run(cr.create_test, db, rec, roadmap_id, **payload.model_dump())


@router.post("/tests/{test_id}/close")
def close_test(test_id: str, rec: Recruiter = Depends(require_approved_recruiter), db: Session = Depends(get_db)):
    return _run(cr.close_test, db, rec, test_id)


# ── Delta admin ──────────────────────────────────────────────────────────────

@router.get("/admin/roadmaps")
def review_queue(_: str = Depends(require_admin), db: Session = Depends(get_db)):
    return {"roadmaps": cr.pending(db)}


@router.post("/admin/roadmaps/{roadmap_id}/review")
def review_roadmap(roadmap_id: str, payload: ReviewPayload, admin: str = Depends(require_admin),
                   db: Session = Depends(get_db)):
    return _run(cr.review, db, roadmap_id, payload.approve, payload.note, admin)


# ── students ─────────────────────────────────────────────────────────────────

@router.get("/student/{user_id}/roadmaps")
def visible_roadmaps(user_id: str, _: str = Depends(require_owner), db: Session = Depends(get_db)):
    return {**cr.visible_to(db, user_id), **cr.my_tracks(db, user_id)}


@router.post("/student/{user_id}/roadmaps/{roadmap_id}/join")
@limiter.limit("10/minute")
def join_roadmap(request: Request, user_id: str, roadmap_id: str, _: str = Depends(require_owner),
                 db: Session = Depends(get_db)):
    return _run(cr.join, db, user_id, roadmap_id)


@router.post("/student/{user_id}/roadmaps/{roadmap_id}/leave")
def leave_roadmap(user_id: str, roadmap_id: str, _: str = Depends(require_owner), db: Session = Depends(get_db)):
    return cr.leave(db, user_id, roadmap_id)


@router.get("/student/{user_id}/tests")
def company_tests(user_id: str, _: str = Depends(require_owner), db: Session = Depends(get_db)):
    return {"tests": cr.student_tests(db, user_id)}
