"""Under-18 college students (DPDP §9). Off unless MINOR_ACCOUNTS_ENABLED.

- Only through a college seat (a college with allow_minors), never solo.
- Verifiable parental consent before the account is usable: either the
  college attests it holds consent (recorded on the roster at upload), or we
  email the parent a one-time link (only its hash is stored, 7-day expiry).
- Minors never reach AI features that process their own data, recruiters,
  leagues, circles, referrals or public badge links (each enforced where the
  feature lives). At 18 they give their own consent again.
"""
from __future__ import annotations

import datetime
import hashlib
import html
import secrets
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models.college import Batch, College, ParentalConsentRequest, RosterEntry
from app.models.user import User
from app.services import compliance

MIN_AGE = 15
LINK_DAYS = 7
MINOR_BLOCKED = "This opens up when you turn 18. Your plan, practice tests and coding problems are all available."


def enabled() -> bool:
    return bool(settings.MINOR_ACCOUNTS_ENABLED)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def assert_adult(db: Session, user_id: str) -> None:
    """For features minors can't use (leagues, circles, referrals, sharing)."""
    if compliance.is_minor(db.get(User, user_id)):
        raise ValueError(MINOR_BLOCKED)


def start(db: Session, user_id: str, *, dob: datetime.date, code: str, roll_no: str | None,
          parent_name: str | None, parent_email: str | None, policy_version: str | None) -> dict:
    from app.services import college
    if not enabled():
        raise ValueError("Under-18 accounts aren't available yet. Please check back soon.")
    if policy_version != compliance.POLICY_VERSION:
        raise ValueError("The policy was updated. Please review the latest version.")
    today = datetime.date.today()
    age = compliance.age_on(dob, today)
    if age >= compliance.ADULT_AGE:
        raise ValueError("You're 18 or older, so choose \"I'm 18 or older\" instead.")
    if age < MIN_AGE:
        raise ValueError("Delta for College is for students aged 15 and over.")
    batch = db.query(Batch).filter(Batch.join_code == (code or "").strip().upper(), Batch.join_code_active.is_(True)).first()
    c = db.get(College, batch.college_id) if batch else None
    if not c or not c.allow_minors:
        raise ValueError("Your college hasn't set Delta up for under-18 students. Please ask your placement office.")
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, name="Student")
        db.add(user)
    if user.date_of_birth and user.date_of_birth != dob:
        raise ValueError("Your date of birth is already on file. Ask your placement office to correct it.")
    user.date_of_birth = dob
    db.commit()
    compliance.record_consent(db, user_id, compliance.TERMS, True)  # the student's own assent
    college.join(db, user_id, None, code=code, roll_no=roll_no, joined_via="minor")

    m = college.membership(db, user_id)
    entry = db.get(RosterEntry, m.roster_entry_id) if m and m.roster_entry_id else None
    if entry and entry.minor_consent_ref and entry.attested_at:
        db.add(ParentalConsentRequest(id=str(uuid.uuid4()), user_id=user_id, college_id=c.id,
                                      method="college_attestation", status="granted",
                                      responded_at=datetime.datetime.utcnow()))
        db.commit()
        compliance.record_consent(db, user_id, compliance.PARENTAL_CONSENT_MINOR, True,
                                  subject_id=f"college:{c.id}:{entry.id}")
        return status(db, user_id)
    if not parent_email or "@" not in parent_email:
        raise ValueError("Enter your parent's or guardian's email so they can give consent.")
    request_parent_consent(db, user_id, c, parent_name, parent_email)
    return status(db, user_id)


def request_parent_consent(db: Session, user_id: str, c: College, parent_name: str | None, parent_email: str) -> None:
    token = secrets.token_urlsafe(32)
    db.add(ParentalConsentRequest(
        id=str(uuid.uuid4()), user_id=user_id, college_id=c.id, parent_name=(parent_name or "").strip() or None,
        parent_email=parent_email.strip().lower(), token_hash=_hash(token), method="parent_link",
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=LINK_DAYS)))
    db.commit()
    _email_parent(db, user_id, c, parent_name, parent_email, token)


def resend(db: Session, user_id: str) -> dict:
    last = (db.query(ParentalConsentRequest).filter(ParentalConsentRequest.user_id == user_id,
                                                    ParentalConsentRequest.method == "parent_link")
            .order_by(ParentalConsentRequest.created_at.desc()).first())
    if not last or last.status == "granted":
        raise ValueError("There's no pending consent request.")
    since = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    recent = db.query(ParentalConsentRequest).filter(ParentalConsentRequest.user_id == user_id,
                                                     ParentalConsentRequest.created_at >= since).count()
    if recent >= 3:
        raise ValueError("We've sent the email three times today. Please try again tomorrow.")
    last.status = "expired"
    db.commit()
    request_parent_consent(db, user_id, db.get(College, last.college_id), last.parent_name, last.parent_email)
    return status(db, user_id)


def _email_parent(db: Session, user_id: str, c: College, parent_name, parent_email, token: str) -> None:
    from app.services.email_service import _dispatch, email_configured
    if not email_configured():
        return
    link = f"{settings.FRONTEND_URL.rstrip('/')}/parent-consent/{token}"
    student = (db.get(User, user_id).name or "Your child").split()[0]
    body = f"""<p>Hello{(' ' + html.escape(parent_name)) if parent_name else ''},</p>
<p>{html.escape(student)} is joining <strong>Delta</strong> through {html.escape(c.name)} to prepare for placements.
Because they are under 18, we need your consent first.</p>
<p><a href="{html.escape(link)}">Review and give consent</a> (the link works for {LINK_DAYS} days).</p>
<p>You can say no, and you can withdraw consent later; their account is then deleted.</p>"""
    _dispatch(parent_email, parent_name or "Parent", f"Consent for {student} to use Delta at {c.name}", body)


def _request_by_token(db: Session, token: str) -> ParentalConsentRequest:
    req = db.query(ParentalConsentRequest).filter(ParentalConsentRequest.token_hash == _hash(token or "")).first()
    if not req:
        raise LookupError("This link isn't valid.")
    if req.status == "pending" and req.expires_at and req.expires_at < datetime.datetime.utcnow():
        req.status = "expired"
        db.commit()
    return req


def parent_view(db: Session, token: str) -> dict:
    req = _request_by_token(db, token)
    user = db.get(User, req.user_id)
    c = db.get(College, req.college_id) if req.college_id else None
    return {"student": (user.name or "Your child").split()[0] if user else "Your child",
            "college": c.name if c else None, "status": req.status,
            "expires_at": req.expires_at.isoformat() if req.expires_at else None}


def parent_respond(db: Session, token: str, grant: bool, is_guardian: bool) -> dict:
    req = _request_by_token(db, token)
    if req.status != "pending":
        raise ValueError("This link has already been used or has expired.")
    if grant and not is_guardian:
        raise ValueError("Please confirm you are the parent or legal guardian.")
    req.status, req.responded_at = ("granted" if grant else "declined"), datetime.datetime.utcnow()
    db.commit()
    compliance.record_consent(db, req.user_id, compliance.PARENTAL_CONSENT_MINOR, grant,
                              subject_id=f"parent_link:{req.id}")
    if not grant:
        from app.services import college
        college.leave(db, req.user_id)
    return parent_view(db, token)


def status(db: Session, user_id: str) -> dict | None:
    user = db.get(User, user_id)
    if not user or not user.date_of_birth:
        return None
    rec = compliance.latest_consent(db, user_id, compliance.PARENTAL_CONSENT_MINOR)
    last = (db.query(ParentalConsentRequest).filter(ParentalConsentRequest.user_id == user_id)
            .order_by(ParentalConsentRequest.created_at.desc()).first())
    masked = None
    if last and last.parent_email:
        name, _, domain = last.parent_email.partition("@")
        masked = f"{name[:1]}***@{domain}"
    return {"granted": bool(rec and rec.action == "granted"), "method": last.method if last else None,
            "request_status": last.status if last else None, "parent_email": masked}


def reconsent(db: Session, user_id: str) -> None:
    user = db.get(User, user_id)
    if not user or not compliance.needs_adult_reconsent(db, user):
        raise ValueError("Nothing to confirm.")
    compliance.record_consent(db, user_id, compliance.ADULT_RECONSENT, True)
    compliance.record_consent(db, user_id, compliance.TERMS, True)
