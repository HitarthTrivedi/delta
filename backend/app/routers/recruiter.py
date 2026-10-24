"""Recruiter portal router.

Recruiters are separate accounts (table `recruiters`) on the same Supabase
auth. They see nothing until an admin approves them, and even then only
students who have opted in (latest `recruiter_visibility` consent = granted,
on the current policy version). Every full-profile view is logged and shown
to the student.
"""
import datetime
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.limiter import limiter
from app.dependencies.auth import current_identity
from app.models.compliance import Recruiter, RecruiterProfileView
from app.models.sandbox_session import SandboxSession
from app.models.skill_node import SkillNode
from app.models.user import User
from app.services import compliance
from app.services.reminder_service import _supabase_admin_email
from app.services.readiness import compute_readiness
from app.services.domain_packs import resolve_field

router = APIRouter(prefix="/api/recruiter", tags=["recruiter"])

# Fit-score weights; components a recruiter didn't ask about are dropped and
# the rest renormalised.
WEIGHTS = {"skills": 0.5, "sandbox": 0.35, "role": 0.15}


class RegisterPayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    company: str = Field(min_length=1, max_length=160)
    designation: Optional[str] = Field(default=None, max_length=120)
    company_website: Optional[str] = Field(default=None, max_length=300)
    accepted_terms: bool = False
    policy_version: Optional[str] = None


class Preferences(BaseModel):
    target_role: Optional[str] = Field(default=None, max_length=160)
    skills: list[str] = Field(default_factory=list, max_length=20)
    min_score: Optional[int] = Field(default=None, ge=0, le=100)


class ReviewPayload(BaseModel):
    approve: bool


# ── Guards ──────────────────────────────────────────────────────────────────

def _recruiter_or_404(db: Session, recruiter_id: str) -> Recruiter:
    rec = db.query(Recruiter).filter(Recruiter.id == recruiter_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="No recruiter account. Complete registration first.")
    return rec


def require_approved_recruiter(identity=Depends(current_identity), db: Session = Depends(get_db)) -> Recruiter:
    rec = _recruiter_or_404(db, identity[0])
    if rec.status != "approved":
        raise HTTPException(status_code=403, detail="Your recruiter account is awaiting approval.")
    return rec


def require_admin(identity=Depends(current_identity)) -> str:
    if not compliance.is_admin(identity[1]):
        raise HTTPException(status_code=403, detail="Admin only.")
    return identity[0]


def _recruiter_dict(rec: Recruiter) -> dict:
    return {
        "id": rec.id, "email": rec.email, "name": rec.name, "company": rec.company,
        "designation": rec.designation, "company_website": rec.company_website,
        "status": rec.status,
        "preferences": json.loads(rec.preferences) if rec.preferences else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


# ── Account ─────────────────────────────────────────────────────────────────

@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterPayload, identity=Depends(current_identity), db: Session = Depends(get_db)):
    user_id, email = identity
    if not payload.accepted_terms or payload.policy_version != compliance.POLICY_VERSION:
        raise HTTPException(status_code=400, detail="You must accept the current Terms of Use (including the Recruiter Terms) and Privacy Policy.")
    if db.query(Recruiter).filter(Recruiter.id == user_id).first():
        raise HTTPException(status_code=409, detail="Recruiter account already registered.")
    student = db.query(User).filter(User.id == user_id).first()
    if student and student.profile_data:
        raise HTTPException(status_code=409, detail="This login is a student account. Please register as a recruiter with a separate work email.")

    rec = Recruiter(
        id=user_id, email=email, name=payload.name.strip(), company=payload.company.strip(),
        designation=(payload.designation or "").strip() or None,
        company_website=(payload.company_website or "").strip() or None,
        status="pending",
    )
    db.add(rec)
    db.commit()
    compliance.record_consent(db, user_id, compliance.TERMS, granted=True)
    compliance.record_consent(db, user_id, compliance.RECRUITER_TERMS, granted=True)
    return _recruiter_dict(rec)


@router.get("/me")
def me(identity=Depends(current_identity), db: Session = Depends(get_db)):
    rec = _recruiter_or_404(db, identity[0])
    out = _recruiter_dict(rec)
    out["is_admin"] = compliance.is_admin(identity[1])
    return out


@router.put("/preferences")
def save_preferences(payload: Preferences, rec: Recruiter = Depends(require_approved_recruiter), db: Session = Depends(get_db)):
    rec.preferences = json.dumps(payload.model_dump())
    db.commit()
    return _recruiter_dict(rec)


@router.delete("/me")
@limiter.limit("3/minute")
def delete_me(request: Request, identity=Depends(current_identity), db: Session = Depends(get_db)):
    _recruiter_or_404(db, identity[0])
    compliance.erase_recruiter(db, identity[0])
    return {"deleted": True, "login_removed": compliance.delete_auth_user(identity[0])}


# ── Matching ────────────────────────────────────────────────────────────────

def _sandbox_summary(sessions: list[SandboxSession]) -> tuple[dict, dict]:
    """Returns ({type: {average, best, count}}, {theory skill: {correct, total}})."""
    by_type: dict[str, list[int]] = {}
    theory_skills: dict[str, dict] = {}
    for s in sessions:
        if s.score is None:
            continue
        by_type.setdefault(s.type, []).append(s.score)
        if s.type == "theory":
            try:
                breakdown = (json.loads(s.data or "{}").get("result") or {}).get("skill_breakdown") or {}
            except ValueError:
                breakdown = {}
            for skill, st in breakdown.items():
                agg = theory_skills.setdefault(skill, {"correct": 0, "total": 0})
                agg["correct"] += st.get("correct", 0)
                agg["total"] += st.get("total", 0)
    summary = {
        t: {"average": round(sum(v) / len(v)), "best": max(v), "count": len(v)}
        for t, v in by_type.items()
    }
    return summary, theory_skills


def _overall(summary: dict) -> Optional[int]:
    if not summary:
        return None
    return round(sum(v["average"] for v in summary.values()) / len(summary))


def _public_profile(user: User, profile: dict) -> dict:
    return {
        "id": user.id,
        "name": profile.get("name") or user.name,
        "target_role": profile.get("target_role") or user.target_role,
        "audience": profile.get("audience") or "student",
        "field_label": resolve_field({**profile, "target_role": profile.get("target_role") or user.target_role})["label"],
        "work": {
            "current_role": profile.get("current_role"),
            "industry": profile.get("industry"),
            "years_experience": profile.get("years_experience"),
        } if profile.get("audience") == "professional" else None,
        "education": {
            "institution": profile.get("university"),
            "major": profile.get("major"),
            "year": profile.get("study_year"),
            "stage": profile.get("education_stage"),
        },
    }


def _score_candidate(prefs: Preferences, target_role: str, skills: list[SkillNode], summary: dict, theory_skills: dict) -> dict:
    components: dict[str, Optional[float]] = {"skills": None, "sandbox": None, "role": None}
    matched = []

    wanted = [s.strip().lower() for s in prefs.skills if s.strip()]
    if wanted:
        pool: dict[str, float] = {}
        for sk in skills:
            pool[sk.name.lower()] = max(pool.get(sk.name.lower(), 0), (sk.proficiency or 0) / 10)
        for name, st in theory_skills.items():
            if st["total"]:
                pool[name.lower()] = max(pool.get(name.lower(), 0), st["correct"] / st["total"])
        per_skill = []
        for w in wanted:
            best = max((v for k, v in pool.items() if w in k or k in w), default=0.0)
            per_skill.append(best)
            if best > 0:
                matched.append(w)
        components["skills"] = sum(per_skill) / len(per_skill)

    overall = _overall(summary)
    if overall is not None:
        components["sandbox"] = overall / 100

    if prefs.target_role and prefs.target_role.strip():
        words = [w for w in prefs.target_role.lower().split() if len(w) > 2]
        role = (target_role or "").lower()
        components["role"] = 1.0 if words and any(w in role for w in words) else 0.0

    used = {k: v for k, v in components.items() if v is not None}
    fit = None
    if used:
        total_w = sum(WEIGHTS[k] for k in used)
        fit = round(100 * sum(WEIGHTS[k] * v for k, v in used.items()) / total_w)
    return {
        "fit": fit,
        "components": {k: (round(v * 100) if v is not None else None) for k, v in components.items()},
        "matched_skills": matched,
        "overall_sandbox_score": overall,
    }


@router.post("/search")
@limiter.limit("30/minute")
def search(request: Request, prefs: Preferences, rec: Recruiter = Depends(require_approved_recruiter), db: Session = Depends(get_db)):
    ids = compliance.visible_student_ids(db)
    ids.discard(rec.id)
    if not ids:
        return {"candidates": [], "total_visible": 0}

    users = db.query(User).filter(User.id.in_(ids)).all()
    skills_by_user: dict[str, list[SkillNode]] = {}
    for sk in db.query(SkillNode).filter(SkillNode.user_id.in_(ids)).all():
        skills_by_user.setdefault(sk.user_id, []).append(sk)
    sessions_by_user: dict[str, list[SandboxSession]] = {}
    for s in db.query(SandboxSession).filter(SandboxSession.user_id.in_(ids), SandboxSession.status == "completed").all():
        sessions_by_user.setdefault(s.user_id, []).append(s)

    results = []
    for user in users:
        try:
            profile = json.loads(user.profile_data or "{}")
        except ValueError:
            profile = {}
        summary, theory_skills = _sandbox_summary(sessions_by_user.get(user.id, []))
        card = _public_profile(user, profile)
        match = _score_candidate(prefs, card["target_role"], skills_by_user.get(user.id, []), summary, theory_skills)
        overall = match["overall_sandbox_score"]
        if prefs.min_score is not None and (overall is None or overall < prefs.min_score):
            continue
        top_skills = sorted(skills_by_user.get(user.id, []), key=lambda s: -(s.proficiency or 0))[:8]
        results.append({
            **card,
            **match,
            "sandbox": summary,
            "top_skills": [{"name": s.name, "proficiency": s.proficiency} for s in top_skills],
        })

    results.sort(key=lambda r: (r["fit"] is not None, r["fit"] or 0, r["overall_sandbox_score"] or 0), reverse=True)
    return {"candidates": results[:50], "total_visible": len(ids)}


@router.get("/candidates/{student_id}")
@limiter.limit("60/minute")
def candidate_detail(request: Request, student_id: str, rec: Recruiter = Depends(require_approved_recruiter), db: Session = Depends(get_db)):
    if student_id not in compliance.visible_student_ids(db):
        raise HTTPException(status_code=404, detail="This candidate is not available.")
    user = db.query(User).filter(User.id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="This candidate is not available.")

    db.add(RecruiterProfileView(
        id=str(uuid.uuid4()), recruiter_id=rec.id, recruiter_company=rec.company,
        student_id=student_id, viewed_at=datetime.datetime.utcnow(),
    ))
    db.commit()

    try:
        profile = json.loads(user.profile_data or "{}")
    except ValueError:
        profile = {}
    sessions = db.query(SandboxSession).filter(
        SandboxSession.user_id == student_id, SandboxSession.status == "completed",
    ).order_by(SandboxSession.completed_at.desc()).all()
    summary, theory_skills = _sandbox_summary(sessions)
    skills = db.query(SkillNode).filter(SkillNode.user_id == student_id).order_by(SkillNode.proficiency.desc()).all()

    return {
        **_public_profile(user, profile),
        "email": profile.get("email") or _supabase_admin_email(student_id),
        "links": {label: profile.get(key) for label, key in (("LinkedIn", "linkedin_url"), ("GitHub", "github_url"), ("Portfolio", "portfolio_url")) if profile.get(key)},
        "skills": [{"name": s.name, "proficiency": s.proficiency} for s in skills],
        "sandbox": summary,
        "overall_sandbox_score": _overall(summary),
        "theory_skill_breakdown": theory_skills,
        "readiness": {k: v for k, v in compute_readiness(db, student_id).items() if k in ("readiness", "label", "coverage", "coverage_total", "by_type", "rubric", "applicable_types")},
        "recent_sessions": [
            {"type": s.type, "title": s.title, "score": s.score,
             "completed_at": s.completed_at.isoformat() if s.completed_at else None}
            for s in sessions[:20]
        ],
    }


# ── Admin: approve / reject recruiters ──────────────────────────────────────

@router.get("/admin/recruiters")
def admin_list(status: str = "pending", _: str = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Recruiter).filter(Recruiter.status == status).order_by(Recruiter.created_at.asc()).all()
    return {"recruiters": [_recruiter_dict(r) for r in rows]}


@router.post("/admin/recruiters/{recruiter_id}/review")
def admin_review(recruiter_id: str, payload: ReviewPayload, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    rec = _recruiter_or_404(db, recruiter_id)
    rec.status = "approved" if payload.approve else "rejected"
    rec.reviewed_at = datetime.datetime.utcnow()
    db.commit()
    return _recruiter_dict(rec)
