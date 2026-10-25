"""DPDP compliance helpers: consent state, data export, account erasure.

POLICY_VERSION must match the "Last updated" date of the published Privacy
Policy / Terms (frontend/public/legal/*.md). Bumping it makes every user
re-accept on their next visit — do that for any material change.
"""
from __future__ import annotations

import datetime
import json
import logging
import uuid

import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models.compliance import ConsentRecord, Recruiter, RecruiterProfileView
from app.models.user import User
from app.services.reminder_service import _supabase_base_url

logger = logging.getLogger("delta.compliance")

POLICY_VERSION = "2026-10-24"

TERMS = "terms_privacy"
RECRUITER_VISIBILITY = "recruiter_visibility"
RECRUITER_TERMS = "recruiter_terms"
ACCOUNT_DELETED = "account_deleted"
PARENTAL_CONSENT = "parental_consent"
LEARNING_REMINDERS = "learning_reminders"  # opt-in study reminders (email / browser push)

# Tables that are deliberately kept (pseudonymous) after erasure, or handled separately.
_RETAINED_TABLES = {"consent_records", "recruiter_profile_views", "users"}
# Secrets that are useless (and risky) in an export file.
_EXPORT_EXCLUDED_COLUMNS = {"pin_hash"}


def record_consent(db: Session, user_id: str, purpose: str, granted: bool, version: str | None = POLICY_VERSION, subject_id: str | None = None) -> ConsentRecord:
    rec = ConsentRecord(
        id=str(uuid.uuid4()),
        user_id=user_id,
        purpose=purpose,
        subject_id=subject_id,
        action="granted" if granted else "withdrawn",
        policy_version=version,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(rec)
    db.commit()
    return rec


def latest_consent(db: Session, user_id: str, purpose: str) -> ConsentRecord | None:
    return db.query(ConsentRecord).filter(
        ConsentRecord.user_id == user_id,
        ConsentRecord.purpose == purpose,
    ).order_by(ConsentRecord.created_at.desc()).first()


def has_current_terms_consent(db: Session, user_id: str) -> bool:
    rec = latest_consent(db, user_id, TERMS)
    return bool(rec and rec.action == "granted" and rec.policy_version == POLICY_VERSION)


def visible_student_ids(db: Session) -> set[str]:
    """Students whose latest recruiter-visibility event is 'granted' AND who
    have accepted the current Terms/Privacy version."""
    rows = db.query(ConsentRecord).filter(
        ConsentRecord.purpose.in_([RECRUITER_VISIBILITY, TERMS])
    ).order_by(ConsentRecord.created_at.asc()).all()
    latest: dict[tuple[str, str], ConsentRecord] = {}
    for r in rows:
        latest[(r.user_id, r.purpose)] = r
    visible = set()
    for (uid, purpose), rec in latest.items():
        if purpose != RECRUITER_VISIBILITY or rec.action != "granted":
            continue
        terms = latest.get((uid, TERMS))
        if terms and terms.action == "granted" and terms.policy_version == POLICY_VERSION:
            visible.add(uid)
    return visible


def _email_set(raw: str) -> set[str]:
    return {e.strip().lower() for e in (raw or "").split(",") if e.strip()}


def is_admin(email: str | None) -> bool:
    return bool(email) and email.lower() in _email_set(settings.ADMIN_EMAILS)


def is_content_reviewer(email: str | None) -> bool:
    """School lesson reviewers: CONTENT_REVIEWER_EMAILS, plus all admins."""
    return is_admin(email) or (bool(email) and email.lower() in _email_set(settings.CONTENT_REVIEWER_EMAILS))


def _row_to_dict(row) -> dict:
    out = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if isinstance(val, (datetime.datetime, datetime.date)):
            val = val.isoformat()
        elif isinstance(val, str) and val[:1] in ("{", "["):
            try:
                val = json.loads(val)
            except ValueError:
                pass
        out[col.name] = val
    return out


def _user_tables():
    return [t for t in Base.metadata.sorted_tables if "user_id" in t.c and t.name not in _RETAINED_TABLES]


def export_user_data(db: Session, user_id: str) -> dict:
    """Everything Delta stores about a student (DPDP §11 right to access)."""
    user = db.query(User).filter(User.id == user_id).first()
    data = {
        "exported_at": datetime.datetime.utcnow().isoformat(),
        "policy_version": POLICY_VERSION,
        "account": _row_to_dict(user) if user else None,
    }
    for table in _user_tables():
        rows = db.execute(table.select().where(table.c.user_id == user_id)).mappings().all()
        data[table.name] = [
            {k: (v.isoformat() if isinstance(v, (datetime.datetime, datetime.date)) else v)
             for k, v in r.items() if k not in _EXPORT_EXCLUDED_COLUMNS}
            for r in rows
        ]
    data["consent_history"] = [
        _row_to_dict(r) for r in db.query(ConsentRecord).filter(ConsentRecord.user_id == user_id)
        .order_by(ConsentRecord.created_at.asc()).all()
    ]
    data["recruiter_profile_views"] = [
        {"company": v.recruiter_company, "viewed_at": v.viewed_at.isoformat() if v.viewed_at else None}
        for v in db.query(RecruiterProfileView).filter(RecruiterProfileView.student_id == user_id).all()
    ]
    return data


def delete_auth_user(user_id: str) -> bool:
    """Remove the Supabase auth account (email/password login). Needs the
    service-role key; returns False if it isn't configured or the call fails."""
    base = _supabase_base_url()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not base or not key:
        logger.warning("Supabase service key not configured — auth user %s not deleted", user_id)
        return False
    try:
        resp = requests.delete(
            f"{base}/auth/v1/admin/users/{user_id}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=10,
        )
    except Exception as exc:
        logger.error("Supabase auth delete failed for %s: %s", user_id, exc)
        return False
    if resp.status_code not in (200, 204, 404):
        logger.error("Supabase auth delete for %s returned %s", user_id, resp.status_code)
        return False
    return True


def _erase_user_rows(db: Session, user_id: str) -> None:
    for table in reversed(_user_tables()):  # dependents before parents
        db.execute(table.delete().where(table.c.user_id == user_id))
    db.query(User).filter(User.id == user_id).delete()


def erase_student(db: Session, user_id: str) -> None:
    """Erase all of a student's personal data (DPDP §8(7), §12). Keeps only the
    pseudonymous consent log, plus an 'account_deleted' event, as proof."""
    _erase_user_rows(db, user_id)
    db.query(RecruiterProfileView).filter(RecruiterProfileView.student_id == user_id).delete()
    db.commit()
    record_consent(db, user_id, RECRUITER_VISIBILITY, granted=False)
    record_consent(db, user_id, ACCOUNT_DELETED, granted=False)


def erase_recruiter(db: Session, recruiter_id: str) -> None:
    db.query(Recruiter).filter(Recruiter.id == recruiter_id).delete()
    # The student app auto-creates a placeholder `users` row on any visit; drop it too.
    _erase_user_rows(db, recruiter_id)
    db.commit()
    record_consent(db, recruiter_id, ACCOUNT_DELETED, granted=False)
