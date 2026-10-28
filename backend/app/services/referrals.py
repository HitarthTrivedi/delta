"""Referrals: invite a friend; once they have studied on 3 days, you both get a
streak freeze (or XP if your freezes are already full).

- Every learner has a personal invite code (made on first use).
- The invited learner links up themselves, with a recorded `referral_link`
  consent, from a new account only (first 14 days). Their inviter then sees
  their first name and last initial and whether the reward is unlocked.
- Limits: no self-invites, no inviting back the person who invited you, and an
  inviter's rewards are capped at 5 a month.
"""
from __future__ import annotations

import datetime
import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.engagement import DailyActivity, Referral, UserEngagement, XpEvent
from app.models.user import User

ACTIVE_DAYS_TO_REWARD = 3
NEW_ACCOUNT_DAYS = 14
MONTHLY_CAP = 5
REWARD_XP = 30  # instead of a freeze when the learner already holds the maximum
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _display(name: str | None) -> str:
    from app.services.leagues import display_name
    return display_name(name)


def code_for(db: Session, eng: UserEngagement) -> str:
    """The learner's invite code, created once. Commits when new."""
    while not eng.referral_code:
        eng.referral_code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
        try:
            db.commit()
        except IntegrityError:  # astronomically rare collision: try another
            db.rollback()
            eng.referral_code = None
    return eng.referral_code


def _inviter(db: Session, code: str) -> UserEngagement | None:
    code = (code or "").strip().upper()
    return db.query(UserEngagement).filter(UserEngagement.referral_code == code).first() if code else None


def _why_not(db: Session, user_id: str, inviter: UserEngagement | None) -> str | None:
    """Why this learner can't link to this invite, or None if they can."""
    if inviter is None:
        return "This invite link is not valid."
    from app.services.compliance import is_minor
    if is_minor(db.get(User, user_id)) or is_minor(db.get(User, inviter.user_id)):
        return "Invite links open up when you turn 18."
    if inviter.user_id == user_id:
        return "That's your own invite link. Share it with a friend!"
    if db.get(Referral, user_id):
        return "Your account is already linked to an invite."
    back = db.get(Referral, inviter.user_id)
    if back and back.referrer_id == user_id:
        return "You invited this person, so you can't use their link."
    user = db.get(User, user_id)
    if not user or not user.created_at or \
            datetime.datetime.utcnow() - user.created_at > datetime.timedelta(days=NEW_ACCOUNT_DAYS):
        return "Invite links are for new accounts."
    return None


def preview(db: Session, user_id: str, code: str) -> dict:
    inviter = _inviter(db, code)
    reason = _why_not(db, user_id, inviter)
    name = _display(db.get(User, inviter.user_id).name) if inviter and db.get(User, inviter.user_id) else None
    return {"inviter": name, "eligible": reason is None, "reason": reason, "days_needed": ACTIVE_DAYS_TO_REWARD}


def claim(db: Session, user_id: str, code: str) -> dict:
    from app.services import compliance
    if not compliance.has_current_terms_consent(db, user_id):
        raise ValueError("Accept the Terms of Use and Privacy Policy first.")
    inviter = _inviter(db, code)
    reason = _why_not(db, user_id, inviter)
    if reason:
        raise ValueError(reason)
    compliance.record_consent(db, user_id, compliance.REFERRAL_LINK, True)
    db.add(Referral(user_id=user_id, referrer_id=inviter.user_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return overview(db, user_id)


def unlink(db: Session, user_id: str) -> dict:
    """Withdraw the link: the inviter no longer sees this learner. Rewards
    already earned stay."""
    from app.services import compliance
    ref = db.get(Referral, user_id)
    if ref:
        db.delete(ref)
        compliance.record_consent(db, user_id, compliance.REFERRAL_LINK, False)
        db.commit()
    return overview(db, user_id)


def _give(eng: UserEngagement, book, source_id: str) -> None:
    from app.services.engagement import MAX_FREEZES
    if eng.streak_freezes < MAX_FREEZES:
        if book("referral", source_id, 0):
            eng.streak_freezes += 1
    else:
        book("referral", source_id, REWARD_XP)


def check(db: Session, eng: UserEngagement, award) -> bool:
    """After the invited learner's activity: reward both once they have studied
    on 3 days. `award` books on the invited learner's day. Caller commits."""
    from app.services.engagement import book_bonus, get_or_create, local_today
    ref = db.get(Referral, eng.user_id)
    if not ref or ref.rewarded_at:
        return False
    db.flush()
    days = db.query(DailyActivity).filter(DailyActivity.user_id == eng.user_id, DailyActivity.actions > 0).count()
    if days < ACTIVE_DAYS_TO_REWARD:
        return False
    ref.rewarded_at = datetime.datetime.utcnow()
    _give(eng, award, f"invited:{eng.user_id}")

    inviter = get_or_create(db, ref.referrer_id)
    month_start = local_today(inviter).replace(day=1)
    this_month = (db.query(XpEvent)
                  .filter(XpEvent.user_id == inviter.user_id, XpEvent.source_type == "referral",
                          XpEvent.source_id.like("inviter:%"), XpEvent.local_date >= month_start).count())
    if this_month < MONTHLY_CAP:
        _give(inviter, lambda kind, sid, xp: book_bonus(db, inviter, kind, sid, xp), f"inviter:{eng.user_id}")
    return True


def overview(db: Session, user_id: str) -> dict:
    from app.services.engagement import get_or_create
    eng = get_or_create(db, user_id)
    code = code_for(db, eng)
    invited = db.query(Referral).filter(Referral.referrer_id == user_id).order_by(Referral.created_at.desc()).all()
    names = dict(db.query(User.id, User.name).filter(User.id.in_([r.user_id for r in invited])).all()) if invited else {}
    mine = db.get(Referral, user_id)
    inviter_name = None
    if mine:
        inviter_user = db.get(User, mine.referrer_id)
        inviter_name = _display(inviter_user.name) if inviter_user else None
    return {
        "code": code,
        "days_needed": ACTIVE_DAYS_TO_REWARD,
        "monthly_cap": MONTHLY_CAP,
        "invited": [{"name": _display(names.get(r.user_id)), "rewarded": bool(r.rewarded_at)} for r in invited],
        "linked_to": {"name": inviter_name, "rewarded": bool(mine.rewarded_at)} if mine else None,
    }
