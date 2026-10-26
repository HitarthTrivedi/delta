"""Privacy router — the student's DPDP rights, in-app.

Consent (give / withdraw recruiter visibility), access (export), erasure
(delete account) and transparency (which recruiters viewed my profile).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
import datetime

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.limiter import limiter
from app.dependencies.auth import require_owner, GUEST_ID
from app.models.compliance import ConsentRecord, Recruiter, RecruiterProfileView
from app.models.engagement import CircleMember, Referral
from app.services import compliance

router = APIRouter(prefix="/api/privacy", tags=["privacy"])

CONSENTABLE = {compliance.TERMS, compliance.RECRUITER_VISIBILITY, compliance.LEARNING_REMINDERS,
               compliance.LEADERBOARD_VISIBILITY, compliance.RECRUITER_HABIT_BADGE,
               compliance.STUDY_CIRCLES, compliance.REFERRAL_LINK, compliance.ADULT_RECONSENT}
# Granted only through their own flows (they need an invite code); here they can only be withdrawn.
WITHDRAW_ONLY = {compliance.STUDY_CIRCLES, compliance.REFERRAL_LINK}


def _not_guest(user_id: str) -> None:
    # The shared demo account needs no auth, so nobody may change its consent or delete it.
    if user_id == GUEST_ID:
        raise HTTPException(status_code=403, detail="Not available for the demo account.")


class ConsentPayload(BaseModel):
    purpose: str
    granted: bool
    policy_version: Optional[str] = None
    age_confirmed: bool = False


class DeletePayload(BaseModel):
    confirm: str


class MinorStartPayload(BaseModel):
    dob: datetime.date
    code: str = Field(min_length=4, max_length=16)
    roll_no: Optional[str] = Field(default=None, max_length=40)
    parent_name: Optional[str] = Field(default=None, max_length=120)
    parent_email: Optional[str] = Field(default=None, max_length=200)
    policy_version: Optional[str] = None
    assent: bool = False


# Why a learner can't opt in to recruiters (shown as-is).
POOL_REASONS = {
    "professional": "Working professionals aren't shown to recruiters on Delta.",
    "minor": "Recruiters can see you once you turn 18.",
    "college_pending": "Your college still has to confirm your seat.",
    "staff": "Staff and recruiter accounts aren't shown to recruiters.",
    "no_account": "Finish setting up your profile first.",
}


def _consent_state(db: Session, user_id: str) -> dict:
    terms = compliance.latest_consent(db, user_id, compliance.TERMS)
    vis = compliance.latest_consent(db, user_id, compliance.RECRUITER_VISIBILITY)
    reminders = compliance.latest_consent(db, user_id, compliance.LEARNING_REMINDERS)
    leagues = compliance.latest_consent(db, user_id, compliance.LEADERBOARD_VISIBILITY)
    habit_badge = compliance.latest_consent(db, user_id, compliance.RECRUITER_HABIT_BADGE)
    history = db.query(ConsentRecord).filter(ConsentRecord.user_id == user_id) \
        .order_by(ConsentRecord.created_at.desc()).limit(50).all()
    from app.config import settings
    from app.models.user import User
    from app.services import college, minors
    user = db.get(User, user_id)
    pool, reason = compliance.recruiter_pool_for(db, user_id)
    return {
        "recruiter_pool": pool,
        "recruiter_pool_reason": None if pool else POOL_REASONS.get(reason),
        "college": college.student_state(db, user_id, None)["membership"],
        "is_college_admin": college.is_staff(db, user_id),
        "is_minor": compliance.is_minor(user),
        "parental_consent": minors.status(db, user_id),
        "needs_adult_reconsent": bool(user and compliance.needs_adult_reconsent(db, user)),
        "access_ok": compliance.access_ok(db, user) if user else compliance.has_current_terms_consent(db, user_id),
        "minor_accounts_enabled": bool(settings.MINOR_ACCOUNTS_ENABLED),
        "current_policy_version": compliance.POLICY_VERSION,
        "terms_accepted": compliance.has_current_terms_consent(db, user_id),
        "terms_accepted_version": terms.policy_version if terms and terms.action == "granted" else None,
        "recruiter_visible": bool(vis and vis.action == "granted"),
        "learning_reminders": bool(reminders and reminders.action == "granted"),
        "leaderboard_visibility": bool(leagues and leagues.action == "granted"),
        "recruiter_habit_badge": bool(habit_badge and habit_badge.action == "granted"),
        "study_circles": db.query(CircleMember).filter(CircleMember.user_id == user_id).count(),
        "referral_link": db.get(Referral, user_id) is not None,
        "is_recruiter": db.query(Recruiter).filter(Recruiter.id == user_id).first() is not None,
        "history": [
            {"purpose": h.purpose, "action": h.action, "policy_version": h.policy_version,
             "at": h.created_at.isoformat() if h.created_at else None}
            for h in history
        ],
    }


@router.get("/{user_id}/consent")
def get_consent(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return _consent_state(db, user_id)


@router.post("/{user_id}/consent")
@limiter.limit("20/minute")
def set_consent(
    request: Request,
    user_id: str,
    payload: ConsentPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    _not_guest(user_id)
    if payload.purpose not in CONSENTABLE:
        raise HTTPException(status_code=400, detail="Unknown consent purpose.")
    if payload.purpose in WITHDRAW_ONLY and payload.granted:
        raise HTTPException(status_code=400, detail="Join a circle or use an invite link to switch this on.")

    if payload.purpose == compliance.TERMS:
        if not payload.granted:
            # Withdrawing consent to core processing means we must stop
            # processing and erase — that is the delete-account flow.
            raise HTTPException(status_code=400, detail="To withdraw this consent, delete your account from Privacy settings.")
        if payload.policy_version != compliance.POLICY_VERSION:
            raise HTTPException(status_code=409, detail="The policy was updated. Please review the latest version.")
        if not payload.age_confirmed:
            raise HTTPException(status_code=400, detail="Delta is currently available only to users aged 18 or older.")
    elif payload.granted and not compliance.has_current_terms_consent(db, user_id):
        raise HTTPException(status_code=400, detail="Accept the Terms of Use and Privacy Policy first.")
    if payload.granted and payload.purpose in (compliance.RECRUITER_VISIBILITY, compliance.RECRUITER_HABIT_BADGE):
        pool, reason = compliance.recruiter_pool_for(db, user_id)
        if pool is None:
            raise HTTPException(status_code=400, detail=POOL_REASONS.get(reason, "Not available for your account."))

    if payload.purpose == compliance.ADULT_RECONSENT:
        from app.services import minors
        try:
            minors.reconsent(db, user_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif payload.purpose == compliance.LEARNING_REMINDERS:
        # Records the consent and switches reminders on/off in one place.
        from app.services import engagement
        engagement.set_reminders(db, user_id, payload.granted)
    elif payload.purpose == compliance.STUDY_CIRCLES:
        from app.services import circles
        circles.leave_all(db, user_id)
    elif payload.purpose == compliance.REFERRAL_LINK:
        from app.services import referrals
        referrals.unlink(db, user_id)
    elif payload.purpose == compliance.LEADERBOARD_VISIBILITY:
        # Records the consent and joins/leaves leagues in one place.
        from app.services import leagues
        leagues.set_opt_in(db, user_id, payload.granted)
    else:
        compliance.record_consent(db, user_id, payload.purpose, payload.granted)
    return _consent_state(db, user_id)


@router.post("/{user_id}/minor-start")
@limiter.limit("5/minute")
def minor_start(request: Request, user_id: str, payload: MinorStartPayload, db: Session = Depends(get_db),
                _: str = Depends(require_owner)):
    """Under-18 college student: date of birth + college code + parent's email (or the college's attestation)."""
    _not_guest(user_id)
    if not payload.assent:
        raise HTTPException(status_code=400, detail="Please confirm you've read what Delta does and agree to use it.")
    from app.services import minors
    try:
        minors.start(db, user_id, dob=payload.dob, code=payload.code, roll_no=payload.roll_no,
                     parent_name=payload.parent_name, parent_email=payload.parent_email,
                     policy_version=payload.policy_version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _consent_state(db, user_id)


@router.post("/{user_id}/parent-consent/resend")
@limiter.limit("5/minute")
def resend_parent_consent(request: Request, user_id: str, db: Session = Depends(get_db),
                          _: str = Depends(require_owner)):
    from app.services import minors
    try:
        minors.resend(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _consent_state(db, user_id)


@router.get("/{user_id}/profile-views")
def profile_views(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    rows = db.query(RecruiterProfileView).filter(RecruiterProfileView.student_id == user_id) \
        .order_by(RecruiterProfileView.viewed_at.desc()).limit(100).all()
    return {"views": [
        {"company": r.recruiter_company, "viewed_at": r.viewed_at.isoformat() if r.viewed_at else None}
        for r in rows
    ]}


@router.get("/{user_id}/export")
@limiter.limit("5/minute")
def export_data(request: Request, user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return compliance.export_user_data(db, user_id)


@router.delete("/{user_id}")
@limiter.limit("3/minute")
def delete_account(
    request: Request,
    user_id: str,
    payload: DeletePayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    _not_guest(user_id)
    if payload.confirm != "DELETE":
        raise HTTPException(status_code=400, detail='Type DELETE to confirm.')
    compliance.erase_student(db, user_id)
    auth_deleted = compliance.delete_auth_user(user_id)
    return {"deleted": True, "login_removed": auth_deleted}
