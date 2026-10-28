"""Delta for College API: platform admin, college staff (TPO/faculty), and
the student side (join / leave). Staff and students only ever reach their
own college; platform admins (ADMIN_EMAILS) can reach every college."""
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import current_identity, require_owner
from app.limiter import limiter
from app.services import college, college_analytics, compliance

router = APIRouter(prefix="/api/college", tags=["college"])


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def require_platform_admin(identity=Depends(current_identity)) -> str:
    if not compliance.is_admin(identity[1]):
        raise HTTPException(status_code=403, detail="Admin only.")
    return identity[0]


def _staff(db: Session, identity, college_id: str, write: bool = False) -> str:
    return _run(college.require_staff, db, identity[0], identity[1], college_id, write)


# ── platform admin ───────────────────────────────────────────────────────────

class CollegePayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    email_domains: list[str] = Field(default_factory=list, max_length=10)
    seat_limit: int = Field(ge=1, le=100000)
    licence_valid_until: Optional[datetime.date] = None
    allow_minors: bool = False
    first_tpo_email: str = Field(min_length=3, max_length=200)


class CollegeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    email_domains: Optional[list[str]] = Field(default=None, max_length=10)
    seat_limit: Optional[int] = Field(default=None, ge=1, le=100000)
    licence_valid_until: Optional[datetime.date] = None
    allow_minors: Optional[bool] = None
    status: Optional[str] = Field(default=None, pattern="^(active|suspended|ended)$")


class EmailPayload(BaseModel):
    email: str = Field(min_length=3, max_length=200)


@router.post("/admin/colleges")
@limiter.limit("20/minute")
def admin_create(request: Request, payload: CollegePayload, admin: str = Depends(require_platform_admin),
                 db: Session = Depends(get_db)):
    return _run(college.create_college, db, created_by=admin, **payload.model_dump())


@router.get("/admin/colleges")
def admin_list(_: str = Depends(require_platform_admin), db: Session = Depends(get_db)):
    return {"colleges": college.list_colleges(db)}


@router.patch("/admin/colleges/{college_id}")
def admin_update(college_id: str, payload: CollegeUpdate, _: str = Depends(require_platform_admin),
                 db: Session = Depends(get_db)):
    return _run(college.update_college, db, college_id, **payload.model_dump())


@router.post("/admin/colleges/{college_id}/recruiters")
def admin_link_recruiter(college_id: str, payload: EmailPayload, _: str = Depends(require_platform_admin),
                         db: Session = Depends(get_db)):
    return {"recruiters": _run(college.link_recruiter, db, college_id, payload.email, "delta")}


@router.post("/admin/sweep")
def admin_sweep(_: str = Depends(require_platform_admin), db: Session = Depends(get_db)):
    return {"expired": college.expire_ended_licences(db)}


# ── staff account ────────────────────────────────────────────────────────────

class AcceptPayload(BaseModel):
    policy_version: str


@router.get("/me")
def staff_me(identity=Depends(current_identity), db: Session = Depends(get_db)):
    invites = college.pending_invites(db, identity[1])
    return {
        "colleges": college.my_colleges(db, identity[0]),
        "pending_invites": [{"college": (db.get(college.College, i.college_id).name), "role": i.role} for i in invites],
        "is_admin": compliance.is_admin(identity[1]),
        "policy_version": compliance.POLICY_VERSION,
    }


@router.post("/me/accept")
@limiter.limit("10/minute")
def staff_accept(request: Request, payload: AcceptPayload, identity=Depends(current_identity),
                 db: Session = Depends(get_db)):
    return {"colleges": _run(college.accept_invites, db, identity[0], identity[1], payload.policy_version)}


# ── student side (declared before /{college_id} routes) ─────────────────────

class JoinPayload(BaseModel):
    code: Optional[str] = Field(default=None, max_length=16)
    via_domain: bool = False
    roll_no: Optional[str] = Field(default=None, max_length=40)


@router.get("/student/{user_id}")
def student_state(user_id: str, _: str = Depends(require_owner), identity=Depends(current_identity),
                  db: Session = Depends(get_db)):
    return college.student_state(db, user_id, identity[1])


@router.get("/join/{code}/preview")
@limiter.limit("30/minute")
def join_preview(request: Request, code: str, _=Depends(current_identity), db: Session = Depends(get_db)):
    found = college.preview_code(db, code)
    if not found:
        raise HTTPException(status_code=404, detail="This join code isn't valid any more. Ask your placement office for a new one.")
    return found


@router.post("/student/{user_id}/join")
@limiter.limit("10/minute")
def student_join(request: Request, user_id: str, payload: JoinPayload, _: str = Depends(require_owner),
                 identity=Depends(current_identity), db: Session = Depends(get_db)):
    if not compliance.has_current_terms_consent(db, user_id):
        raise HTTPException(status_code=400, detail="Accept the Terms of Use and Privacy Policy first.")
    return _run(college.join, db, user_id, identity[1], code=payload.code, via_domain=payload.via_domain,
                roll_no=payload.roll_no)


@router.post("/student/{user_id}/leave")
@limiter.limit("10/minute")
def student_leave(request: Request, user_id: str, _: str = Depends(require_owner), db: Session = Depends(get_db)):
    return college.leave(db, user_id)


# ── college staff ────────────────────────────────────────────────────────────

class StaffPayload(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    role: str = Field(default="faculty", pattern="^(tpo|faculty)$")


class BatchPayload(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    course: Optional[str] = Field(default=None, max_length=60)
    grad_year: Optional[int] = Field(default=None, ge=2000, le=2100)
    branch: Optional[str] = Field(default=None, max_length=80)
    section: Optional[str] = Field(default=None, max_length=20)
    program: str = Field(default="none", pattern="^(first_year_4y|placement_6m|none)$")
    duration_years: int = Field(default=4, ge=1, le=6)


class BatchUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    course: Optional[str] = Field(default=None, max_length=60)
    grad_year: Optional[int] = Field(default=None, ge=2000, le=2100)
    branch: Optional[str] = Field(default=None, max_length=80)
    section: Optional[str] = Field(default=None, max_length=20)
    program: Optional[str] = Field(default=None, pattern="^(first_year_4y|placement_6m|none)$")
    join_code_active: Optional[bool] = None
    archived: Optional[bool] = None


class RosterPayload(BaseModel):
    csv: str = Field(min_length=1, max_length=college.ROSTER_MAX_BYTES)
    dry_run: bool = True
    create_batches: bool = True
    minors_consent_ref: Optional[str] = Field(default=None, max_length=200)


@router.get("/{college_id}")
def get_college(college_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    role = _staff(db, identity, college_id)
    return {**college.college_dict(db, _run(college._college, db, college_id)), "role": role}


@router.get("/{college_id}/admins")
def get_team(college_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id)
    return {"admins": college.team(db, college_id)}


@router.post("/{college_id}/admins")
@limiter.limit("20/minute")
def add_staff(request: Request, college_id: str, payload: StaffPayload, identity=Depends(current_identity),
              db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    return {"admins": _run(college.invite_staff, db, college_id, payload.email, payload.role, identity[0])}


@router.delete("/{college_id}/admins/{admin_id}")
def remove_staff(college_id: str, admin_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    return {"admins": _run(college.remove_staff, db, college_id, admin_id)}


@router.get("/{college_id}/batches")
def get_batches(college_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id)
    return {"batches": college.list_batches(db, college_id)}


@router.post("/{college_id}/batches")
def add_batch(college_id: str, payload: BatchPayload, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    return _run(college.create_batch, db, college_id, **payload.model_dump())


@router.patch("/{college_id}/batches/{batch_id}")
def edit_batch(college_id: str, batch_id: str, payload: BatchUpdate, identity=Depends(current_identity),
               db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    return _run(college.update_batch, db, college_id, batch_id, **payload.model_dump())


@router.post("/{college_id}/batches/{batch_id}/join-code")
def new_join_code(college_id: str, batch_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    return _run(college.rotate_code, db, college_id, batch_id)


@router.post("/{college_id}/roster")
@limiter.limit("20/minute")
def upload_roster(request: Request, college_id: str, payload: RosterPayload, identity=Depends(current_identity),
                  db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    return _run(college.import_roster, db, college_id, payload.csv.encode("utf-8"), dry_run=payload.dry_run,
                create_batches=payload.create_batches, minors_consent_ref=payload.minors_consent_ref, by=identity[0])


@router.get("/{college_id}/roster")
def get_roster(college_id: str, batch_id: Optional[str] = None, joined: Optional[bool] = None,
               identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id)
    return {"roster": college.roster(db, college_id, batch_id, joined)}


@router.get("/{college_id}/members")
def get_members(college_id: str, batch_id: Optional[str] = None, status: Optional[str] = None,
                identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id)
    return {"members": college.members(db, college_id, batch_id, status)}


@router.post("/{college_id}/members/{member_id}/approve")
def approve_member(college_id: str, member_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    return _run(college.approve_member, db, college_id, member_id)


@router.delete("/{college_id}/members/{member_id}")
def remove_member(college_id: str, member_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    _run(college.remove_member, db, college_id, member_id)
    return {"ok": True}


@router.get("/{college_id}/recruiters")
def get_recruiters(college_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id)
    return {"recruiters": college.recruiter_links(db, college_id)}


@router.post("/{college_id}/recruiters")
@limiter.limit("20/minute")
def add_recruiter(request: Request, college_id: str, payload: EmailPayload, identity=Depends(current_identity),
                  db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    return {"recruiters": _run(college.link_recruiter, db, college_id, payload.email)}


@router.delete("/{college_id}/recruiters/{link_id}")
def revoke_recruiter(college_id: str, link_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id, write=True)
    return {"recruiters": _run(college.revoke_recruiter, db, college_id, link_id)}


# ── analytics + exports (staff, read-only) ───────────────────────────────────

@router.get("/{college_id}/overview")
def get_overview(college_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id)
    return college_analytics.overview(db, college_id)


@router.get("/{college_id}/batches/{batch_id}/dashboard")
def get_batch_dashboard(college_id: str, batch_id: str, identity=Depends(current_identity),
                        db: Session = Depends(get_db)):
    _staff(db, identity, college_id)
    return _run(college_analytics.batch_dashboard, db, college_id, batch_id)


@router.get("/{college_id}/students/{user_id}")
def get_student(college_id: str, user_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id)
    return _run(college_analytics.student_view, db, college_id, user_id)


@router.get("/{college_id}/exports/{kind}.csv")
@limiter.limit("30/minute")
def export(request: Request, college_id: str, kind: str, batch_id: Optional[str] = None,
           identity=Depends(current_identity), db: Session = Depends(get_db)):
    _staff(db, identity, college_id)
    body = _run(college_analytics.export_csv, db, college_id, kind, batch_id)
    name = f"{kind}-{datetime.date.today().isoformat()}.csv"
    return Response(content="﻿" + body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})
