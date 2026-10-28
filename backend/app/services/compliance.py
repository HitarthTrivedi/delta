"""DPDP compliance helpers: consent state, data export, account erasure.

POLICY_VERSION must match the "Policy version" of the published Privacy
Policy (frontend/public/legal/privacy-policy.md): its "Last updated" date, plus
".2", ".3"... for a second change on the same day. Bumping it makes every user
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

POLICY_VERSION = "2026-10-26"

TERMS = "terms_privacy"
RECRUITER_VISIBILITY = "recruiter_visibility"
RECRUITER_TERMS = "recruiter_terms"
ACCOUNT_DELETED = "account_deleted"
PARENTAL_CONSENT = "parental_consent"
LEARNING_REMINDERS = "learning_reminders"  # opt-in study reminders (email / browser push)
LEADERBOARD_VISIBILITY = "leaderboard_visibility"  # opt-in weekly leagues
STUDY_CIRCLES = "study_circles"  # opt-in private study groups
REFERRAL_LINK = "referral_link"  # invited learner agrees to be linked to their inviter
RECRUITER_HABIT_BADGE = "recruiter_habit_badge"  # opt-in "Consistent learner" badge for recruiters
COLLEGE_ENROLLMENT = "college_enrollment"  # student joins a college (subject_id = college id)
COMPANY_ROADMAP = "company_roadmap"  # share progress + scores on one company's roadmap (subject_id = roadmap id)
COLLEGE_ADMIN_TERMS = "college_admin_terms"  # college staff accept their duties
PARENTAL_CONSENT_MINOR = "parental_consent_minor"  # under-18 college student's parent/college consent
ADULT_RECONSENT = "adult_reconsent"  # a former minor's own consent after turning 18

ADULT_AGE = 18
# Membership states that tie a student to a college (and keep them out of the open pool).
IN_COLLEGE_STATES = ("pending", "active")

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


def opted_in_ids(db: Session) -> set[str]:
    """Users whose latest recruiter-visibility event is 'granted' AND who have
    accepted the current Terms/Privacy version. Recruiters never search this
    directly: they go through `recruiter_visible_ids` (pools)."""
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


# ── recruiter pools ──────────────────────────────────────────────────────────
# Two separate pools, never mixed:
#   campus: opted-in active students of live colleges that linked this recruiter
#   open:   opted-in solo students (in no college, not a working professional)
# Minors, professionals, recruiters and college staff are never in any pool.

def age_on(dob: datetime.date, today: datetime.date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def is_minor(user: User | None, today: datetime.date | None = None) -> bool:
    dob = getattr(user, "date_of_birth", None)
    return bool(dob) and age_on(dob, today or datetime.date.today()) < ADULT_AGE


def college_is_live(college, today: datetime.date | None = None) -> bool:
    today = today or datetime.date.today()
    return bool(college) and college.status == "active" and (
        college.licence_valid_until is None or college.licence_valid_until >= today)


def _staff_ids(db: Session, ids: set[str]) -> set[str]:
    from app.models.college import CollegeAdmin
    if not ids:
        return set()
    recruiters = {r.id for r in db.query(Recruiter.id).filter(Recruiter.id.in_(ids)).all()}
    admins = {a.user_id for a in db.query(CollegeAdmin.user_id)
              .filter(CollegeAdmin.user_id.in_(ids), CollegeAdmin.status != "removed").all()}
    return recruiters | admins


def _pool_facts(db: Session, ids: set[str]) -> dict[str, dict]:
    """For each id: is_minor, professional, membership (status, college live, college id)."""
    from app.models.college import College, CollegeMember
    if not ids:
        return {}
    today = datetime.date.today()
    facts = {}
    for u in db.query(User).filter(User.id.in_(ids)).all():
        try:
            profile = json.loads(u.profile_data or "{}")
        except ValueError:
            profile = {}
        facts[u.id] = {"minor": is_minor(u, today), "professional": profile.get("audience") == "professional",
                       "member": None}
    rows = (db.query(CollegeMember, College).join(College, College.id == CollegeMember.college_id)
            .filter(CollegeMember.user_id.in_(ids), CollegeMember.status.in_(IN_COLLEGE_STATES)).all())
    for m, c in rows:
        if m.user_id in facts:
            facts[m.user_id]["member"] = {"status": m.status, "college_id": c.id, "live": college_is_live(c, today)}
    return facts


def recruiter_pool_for(db: Session, user_id: str) -> tuple[str | None, str]:
    """Which pool a learner would be in if they opt in, and why (for the UI)."""
    if _staff_ids(db, {user_id}):
        return None, "staff"
    facts = _pool_facts(db, {user_id}).get(user_id)
    if facts is None:
        return None, "no_account"
    if facts["minor"]:
        return None, "minor"
    member = facts["member"]
    if member:
        if member["status"] == "active" and member["live"]:
            return "campus", "college"
        return None, "college_pending"
    if facts["professional"]:
        return None, "professional"
    return "open", "solo"


def recruiter_visible_ids(db: Session, recruiter: Recruiter) -> set[str]:
    """The only way a recruiter reaches students: the opted-in learners in
    this recruiter's pool."""
    return in_recruiter_pool(db, recruiter, opted_in_ids(db) - {recruiter.id})


def in_recruiter_pool(db: Session, recruiter: Recruiter, user_ids: set[str]) -> set[str]:
    """Which of these learners are in this recruiter's pool (campus: active
    students of live colleges that linked the recruiter; open: solo students).
    Never staff, minors or professionals."""
    from app.models.college import CollegeRecruiter
    base = set(user_ids)
    base -= _staff_ids(db, base)
    facts = _pool_facts(db, base)
    if (recruiter.pool or "open") == "campus":
        linked = {link.college_id for link in db.query(CollegeRecruiter).filter(
            CollegeRecruiter.recruiter_id == recruiter.id, CollegeRecruiter.status == "active").all()}
        return {uid for uid, f in facts.items()
                if not f["minor"] and f["member"] and f["member"]["status"] == "active"
                and f["member"]["live"] and f["member"]["college_id"] in linked}
    return {uid for uid, f in facts.items() if not f["minor"] and not f["member"] and not f["professional"]}


def can_recruiter_see(db: Session, recruiter: Recruiter, student_id: str) -> bool:
    return student_id in recruiter_visible_ids(db, recruiter)


def withdraw_recruiter_visibility(db: Session, user_id: str) -> None:
    """Pool changed (joined/left a college, seat removed, licence ended): the
    learner's opt-in was for a different audience, so it switches off."""
    for purpose in (RECRUITER_VISIBILITY, RECRUITER_HABIT_BADGE):
        rec = latest_consent(db, user_id, purpose)
        if rec and rec.action == "granted":
            record_consent(db, user_id, purpose, False)
    from app.services.company_roadmaps import leave_all
    leave_all(db, user_id)  # company roadmaps were joined for the old audience too


def access_ok(db: Session, user: User | None) -> bool:
    """Current terms, plus: a minor needs current parental consent; a former
    minor who has turned 18 needs their own consent given after their birthday."""
    if not user or not has_current_terms_consent(db, user.id):
        return False
    dob = user.date_of_birth
    if not dob:
        return True
    if is_minor(user):
        rec = latest_consent(db, user.id, PARENTAL_CONSENT_MINOR)
        return bool(rec and rec.action == "granted")
    return not needs_adult_reconsent(db, user)


def needs_adult_reconsent(db: Session, user: User) -> bool:
    dob = user.date_of_birth
    if not dob or is_minor(user):
        return False
    try:
        birthday = dob.replace(year=dob.year + ADULT_AGE)
    except ValueError:  # 29 February
        birthday = dob.replace(year=dob.year + ADULT_AGE, day=28)
    rec = latest_consent(db, user.id, ADULT_RECONSENT)
    return not (rec and rec.action == "granted" and rec.created_at.date() >= birthday)


def granted_user_ids(db: Session, purpose: str, user_ids) -> set[str]:
    """Of `user_ids`, those whose latest consent event for `purpose` is 'granted'."""
    user_ids = list(user_ids)
    if not user_ids:
        return set()
    rows = db.query(ConsentRecord).filter(
        ConsentRecord.purpose == purpose, ConsentRecord.user_id.in_(user_ids)
    ).order_by(ConsentRecord.created_at.asc()).all()
    latest = {r.user_id: r for r in rows}
    return {uid for uid, rec in latest.items() if rec.action == "granted"}


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
    from app.models.college import College, RosterEntry
    data["college_roster"] = [
        {k: v for k, v in _row_to_dict(r).items() if k not in ("minor_consent_ref", "attested_by")}
        | {"college": (db.get(College, r.college_id).name if db.get(College, r.college_id) else None)}
        for r in db.query(RosterEntry).filter(RosterEntry.claimed_user_id == user_id).all()
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
    from app.models.college import RosterEntry
    from app.models.engagement import Referral
    # The one row keyed to another learner: invitations this user sent.
    db.query(Referral).filter(Referral.referrer_id == user_id).delete()
    # The college keeps its roster row (its own record); only the link to this account goes.
    db.query(RosterEntry).filter(RosterEntry.claimed_user_id == user_id).update(
        {RosterEntry.claimed_user_id: None, RosterEntry.claimed_at: None}, synchronize_session=False)
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
    from app.models.college import CollegeRecruiter
    from app.models.company import CompanyRoadmap, CompanyRoadmapMember, CompanyTest
    db.query(CollegeRecruiter).filter(CollegeRecruiter.recruiter_id == recruiter_id).delete()
    roadmap_ids = [r.id for r in db.query(CompanyRoadmap.id).filter(CompanyRoadmap.recruiter_id == recruiter_id)]
    if roadmap_ids:
        db.query(CompanyTest).filter(CompanyTest.roadmap_id.in_(roadmap_ids)).delete(synchronize_session=False)
        db.query(CompanyRoadmapMember).filter(CompanyRoadmapMember.roadmap_id.in_(roadmap_ids)).delete(
            synchronize_session=False)
        db.query(CompanyRoadmap).filter(CompanyRoadmap.id.in_(roadmap_ids)).delete(synchronize_session=False)
    db.query(Recruiter).filter(Recruiter.id == recruiter_id).delete()
    # The student app auto-creates a placeholder `users` row on any visit; drop it too.
    _erase_user_rows(db, recruiter_id)
    db.commit()
    record_consent(db, recruiter_id, ACCOUNT_DELETED, granted=False)
