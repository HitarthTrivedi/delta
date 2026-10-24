"""Privacy router — the student's DPDP rights, in-app.

Consent (give / withdraw recruiter visibility), access (export), erasure
(delete account) and transparency (which recruiters viewed my profile).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.limiter import limiter
from app.dependencies.auth import require_owner, GUEST_ID
from app.models.compliance import ConsentRecord, Recruiter, RecruiterProfileView
from app.services import compliance

router = APIRouter(prefix="/api/privacy", tags=["privacy"])

CONSENTABLE = {compliance.TERMS, compliance.RECRUITER_VISIBILITY, compliance.LEARNING_REMINDERS}


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


def _consent_state(db: Session, user_id: str) -> dict:
    terms = compliance.latest_consent(db, user_id, compliance.TERMS)
    vis = compliance.latest_consent(db, user_id, compliance.RECRUITER_VISIBILITY)
    reminders = compliance.latest_consent(db, user_id, compliance.LEARNING_REMINDERS)
    history = db.query(ConsentRecord).filter(ConsentRecord.user_id == user_id) \
        .order_by(ConsentRecord.created_at.desc()).limit(50).all()
    return {
        "current_policy_version": compliance.POLICY_VERSION,
        "terms_accepted": compliance.has_current_terms_consent(db, user_id),
        "terms_accepted_version": terms.policy_version if terms and terms.action == "granted" else None,
        "recruiter_visible": bool(vis and vis.action == "granted"),
        "learning_reminders": bool(reminders and reminders.action == "granted"),
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

    if payload.purpose == compliance.LEARNING_REMINDERS:
        # Records the consent and switches reminders on/off in one place.
        from app.services import engagement
        engagement.set_reminders(db, user_id, payload.granted)
    else:
        compliance.record_consent(db, user_id, payload.purpose, payload.granted)
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
