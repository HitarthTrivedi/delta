"""Opt-in weekly leagues, ranked by the XP learners earn that week (effort,
never test scores).

- Opt-in only, with its own recorded consent (`leaderboard_visibility`).
  Other members see a first name and last initial, weekly XP and rank; nothing else.
- Groups of up to 20 learners at the same tier. A new group is opened only
  when every group at that tier is full; same-field groups are preferred.
- Weeks start on Monday in each learner's own timezone. A finished week is
  settled lazily the first time the learner shows up in a later week.
- Forgiving: the top third (at most 5) move up; moving down only happens in
  groups of 10+, never in a learner's first 2 weeks, never if they studied on
  3 or more days that week, and a skipped week changes nothing.
- Opting out removes the learner from every league straight away.
"""
from __future__ import annotations

import datetime
import uuid

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.engagement import DailyActivity, LeagueCohort, LeagueMember, UserEngagement, XpEvent
from app.models.user import User

TIERS = ["Bronze", "Silver", "Gold", "Emerald", "Diamond"]
GROUP_SIZE = 20
MAX_MOVES = 5
DEMOTE_MIN_GROUP = 10
NEW_MEMBER_WEEKS = 2
SAFE_ACTIVE_DAYS = 3


def week_start(d: datetime.date) -> datetime.date:
    return d - datetime.timedelta(days=d.weekday())


def zones(size: int) -> tuple[int, int]:
    """(places that move up, places that may move down) for a group size."""
    up = min(MAX_MOVES, max(1, size // 3))
    down = min(MAX_MOVES, size // 3) if size >= DEMOTE_MIN_GROUP else 0
    return up, down


def display_name(name: str | None) -> str:
    parts = (name or "").split()
    if not parts:
        return "Learner"
    return f"{parts[0]} {parts[-1][0].upper()}." if len(parts) > 1 else parts[0]


def _standings(db: Session, cohort_id: str, start: datetime.date) -> list[tuple[str, int]]:
    """[(user_id, weekly XP)], best first."""
    members = [m.user_id for m in db.query(LeagueMember).filter(LeagueMember.cohort_id == cohort_id).all()]
    if not members:
        return []
    end = start + datetime.timedelta(days=6)
    xp = dict(db.query(XpEvent.user_id, func.coalesce(func.sum(XpEvent.xp), 0))
              .filter(XpEvent.user_id.in_(members), XpEvent.local_date >= start, XpEvent.local_date <= end)
              .group_by(XpEvent.user_id).all())
    return sorted(((uid, int(xp.get(uid, 0))) for uid in members), key=lambda r: (-r[1], r[0]))


def _settle(db: Session, member: LeagueMember) -> int:
    """Decide a finished week's outcome; returns the learner's next tier."""
    rows = _standings(db, member.cohort_id, member.week_start)
    rank = next(i for i, (uid, _) in enumerate(rows, 1) if uid == member.user_id)
    week_xp = rows[rank - 1][1]
    up, down = zones(len(rows))
    weeks_in = db.query(LeagueMember).filter(LeagueMember.user_id == member.user_id).count()
    active_days = (db.query(DailyActivity)
                   .filter(DailyActivity.user_id == member.user_id, DailyActivity.actions > 0,
                           DailyActivity.local_date >= member.week_start,
                           DailyActivity.local_date <= member.week_start + datetime.timedelta(days=6)).count())
    tier = member.tier
    if rank <= up and week_xp > 0 and tier < len(TIERS) - 1:
        member.outcome, tier = "promoted", tier + 1
    elif (down and rank > len(rows) - down and tier > 0
          and weeks_in > NEW_MEMBER_WEEKS and active_days < SAFE_ACTIVE_DAYS):
        member.outcome, tier = "demoted", tier - 1
    else:
        member.outcome = "stayed"
    return tier


def _claim_place(db: Session, start: datetime.date, field: str, tier: int) -> str:
    """Take a place in a group with room (atomic size check), or open a new one."""
    candidates = (db.query(LeagueCohort)
                  .filter(LeagueCohort.week_start == start, LeagueCohort.tier == tier,
                          LeagueCohort.size < GROUP_SIZE)
                  .all())
    candidates.sort(key=lambda c: (c.field != field, -c.size))
    for c in candidates:
        claimed = (db.query(LeagueCohort)
                   .filter(LeagueCohort.id == c.id, LeagueCohort.size < GROUP_SIZE)
                   .update({LeagueCohort.size: LeagueCohort.size + 1}, synchronize_session=False))
        if claimed:
            return c.id
    cohort = LeagueCohort(id=str(uuid.uuid4()), week_start=start, field=field, tier=tier, size=1)
    db.add(cohort)
    return cohort.id


def ensure_membership(db: Session, eng: UserEngagement) -> LeagueMember | None:
    """This week's place for an opted-in learner (joining and settling last
    week as needed). Commits."""
    from app.services.domain_packs import field_for_user
    from app.services.engagement import local_today
    if not eng.leagues_opt_in:
        return None
    start = week_start(local_today(eng))
    member = db.get(LeagueMember, (eng.user_id, start))
    if member:
        return member
    previous = (db.query(LeagueMember)
                .filter(LeagueMember.user_id == eng.user_id, LeagueMember.week_start < start)
                .order_by(LeagueMember.week_start.desc()).first())
    if previous and previous.outcome is None:
        eng.league_tier = _settle(db, previous)
    field = field_for_user(eng.user_id, db=db).get("id") or "general"
    cohort_id = _claim_place(db, start, field, eng.league_tier)
    db.add(LeagueMember(user_id=eng.user_id, week_start=start, cohort_id=cohort_id, tier=eng.league_tier))
    try:
        db.commit()
    except IntegrityError:  # a parallel request joined first; its place stands
        db.rollback()
    return db.get(LeagueMember, (eng.user_id, start))


def set_opt_in(db: Session, user_id: str, enabled: bool) -> dict:
    """Join or leave leagues. Every switch is a recorded consent event."""
    from app.services import compliance
    from app.services.engagement import get_or_create
    if enabled and not compliance.has_current_terms_consent(db, user_id):
        raise ValueError("Accept the Terms of Use and Privacy Policy first.")
    eng = get_or_create(db, user_id)
    if bool(eng.leagues_opt_in) != bool(enabled):
        compliance.record_consent(db, user_id, compliance.LEADERBOARD_VISIBILITY, enabled)
    eng.leagues_opt_in = enabled
    if not enabled:
        for m in db.query(LeagueMember).filter(LeagueMember.user_id == user_id).all():
            if m.outcome is None:  # free the place in a group that is still running
                (db.query(LeagueCohort).filter(LeagueCohort.id == m.cohort_id)
                 .update({LeagueCohort.size: LeagueCohort.size - 1}, synchronize_session=False))
            db.delete(m)
        eng.league_tier = 0
    db.commit()
    return board(db, user_id)


def board(db: Session, user_id: str) -> dict:
    """The learner's league this week, ready to show."""
    from app.services.engagement import get_or_create, local_today
    eng = get_or_create(db, user_id)
    if not eng.leagues_opt_in:
        db.commit()
        return {"opted_in": False}
    member = ensure_membership(db, eng)
    today = local_today(eng)
    rows = _standings(db, member.cohort_id, member.week_start)
    names = dict(db.query(User.id, User.name).filter(User.id.in_([uid for uid, _ in rows])).all())
    up, down = zones(len(rows))
    last = (db.query(LeagueMember)
            .filter(LeagueMember.user_id == user_id, LeagueMember.week_start < member.week_start)
            .order_by(LeagueMember.week_start.desc()).first())
    return {
        "opted_in": True,
        "tier": member.tier,
        "tier_name": TIERS[member.tier],
        "tiers": TIERS,
        "week_start": member.week_start.isoformat(),
        "days_left": (member.week_start + datetime.timedelta(days=6) - today).days,
        "move_up": up if member.tier < len(TIERS) - 1 else 0,
        "move_down": down if member.tier > 0 else 0,
        "rows": [{"rank": i, "name": display_name(names.get(uid)), "xp": xp, "you": uid == user_id}
                 for i, (uid, xp) in enumerate(rows, 1)],
        "last_week": {"outcome": last.outcome, "tier_name": TIERS[last.tier]} if last and last.outcome else None,
    }
