"""Study circles: small private groups (up to 6) that keep each other going.

- Opt-in: creating or joining records a `study_circles` consent; leaving the
  last circle withdraws it. Joining needs the circle's invite link.
- Members see each other's first name and last initial, whether each studied
  today, and their study days this week. Nothing else (no XP, no scores).
- Circle streak: days in a row on which every member kept their day (studied,
  or was covered by a streak freeze or break mode). Read from daily activity.
- Weekly circle goal: together, 3 study days per member. When it is met, every
  member earns a bonus once that week (booked on their own next visit or study).
"""
from __future__ import annotations

import datetime
import secrets
import uuid

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.engagement import CircleMember, DailyActivity, StudyCircle, UserEngagement, XpEvent
from app.models.user import User

MAX_MEMBERS = 6
MAX_CIRCLES = 3
GOAL_DAYS_PER_MEMBER = 3
GOAL_XP = 25
NAME_MAX = 40
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I look-alikes


def _utcnow() -> datetime.datetime:
    """Naive UTC from the engagement clock (one source of time for streaks)."""
    from app.services.engagement import _now
    return _now().astimezone(datetime.timezone.utc).replace(tzinfo=None)


def _new_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


def _week_start(d: datetime.date) -> datetime.date:
    return d - datetime.timedelta(days=d.weekday())


def _memberships(db: Session, user_id: str) -> list[CircleMember]:
    return db.query(CircleMember).filter(CircleMember.user_id == user_id).all()


def _consent(db: Session, user_id: str) -> None:
    from app.services import compliance
    from app.services.minors import assert_adult
    if not compliance.has_current_terms_consent(db, user_id):
        raise ValueError("Accept the Terms of Use and Privacy Policy first.")
    assert_adult(db, user_id)
    rec = compliance.latest_consent(db, user_id, compliance.STUDY_CIRCLES)
    if not rec or rec.action != "granted":
        compliance.record_consent(db, user_id, compliance.STUDY_CIRCLES, True)


def _withdraw_if_none_left(db: Session, user_id: str) -> None:
    from app.services import compliance
    if not _memberships(db, user_id):
        rec = compliance.latest_consent(db, user_id, compliance.STUDY_CIRCLES)
        if rec and rec.action == "granted":
            compliance.record_consent(db, user_id, compliance.STUDY_CIRCLES, False)


def _check_room_for_another(db: Session, user_id: str) -> None:
    if len(_memberships(db, user_id)) >= MAX_CIRCLES:
        raise ValueError(f"You can be in up to {MAX_CIRCLES} circles.")


def create(db: Session, user_id: str, name: str) -> dict:
    name = " ".join((name or "").split())[:NAME_MAX]
    if not name:
        raise ValueError("Give your circle a name.")
    _check_room_for_another(db, user_id)
    _consent(db, user_id)
    circle = StudyCircle(id=str(uuid.uuid4()), name=name, invite_code=_new_code())
    db.add(circle)
    db.flush()
    db.add(CircleMember(id=str(uuid.uuid4()), circle_id=circle.id, user_id=user_id, role="owner", joined_at=_utcnow()))
    db.commit()
    return board(db, user_id)


def preview(db: Session, code: str) -> dict | None:
    circle = db.query(StudyCircle).filter(StudyCircle.invite_code == (code or "").strip().upper()).first()
    if not circle:
        return None
    size = db.query(CircleMember).filter(CircleMember.circle_id == circle.id).count()
    return {"name": circle.name, "members": size, "full": size >= MAX_MEMBERS, "max_members": MAX_MEMBERS}


def join(db: Session, user_id: str, code: str) -> dict:
    circle = (db.query(StudyCircle).filter(StudyCircle.invite_code == (code or "").strip().upper())
              .with_for_update().first())  # serialises joins on Postgres
    if not circle:
        raise ValueError("This invite link is not valid any more. Ask for a new one.")
    if db.query(CircleMember).filter_by(circle_id=circle.id, user_id=user_id).first():
        return board(db, user_id)
    if db.query(CircleMember).filter(CircleMember.circle_id == circle.id).count() >= MAX_MEMBERS:
        raise ValueError(f"This circle is full ({MAX_MEMBERS} people).")
    _check_room_for_another(db, user_id)
    _consent(db, user_id)
    db.add(CircleMember(id=str(uuid.uuid4()), circle_id=circle.id, user_id=user_id, role="member", joined_at=_utcnow()))
    try:
        db.commit()
    except IntegrityError:  # the same person joining twice at once
        db.rollback()
    return board(db, user_id)


def _drop(db: Session, member: CircleMember) -> None:
    """Remove a member; hand ownership on, or close an empty circle."""
    circle_id = member.circle_id
    db.delete(member)
    db.flush()
    rest = (db.query(CircleMember).filter(CircleMember.circle_id == circle_id)
            .order_by(CircleMember.joined_at.asc()).all())
    if not rest:
        db.query(StudyCircle).filter(StudyCircle.id == circle_id).delete()
    elif not any(m.role == "owner" for m in rest):
        rest[0].role = "owner"


def leave(db: Session, user_id: str, circle_id: str) -> dict:
    member = db.query(CircleMember).filter_by(circle_id=circle_id, user_id=user_id).first()
    if member:
        _drop(db, member)
        _withdraw_if_none_left(db, user_id)
        db.commit()
    return board(db, user_id)


def leave_all(db: Session, user_id: str) -> None:
    for m in _memberships(db, user_id):
        _drop(db, m)
    _withdraw_if_none_left(db, user_id)
    db.commit()


def _owned(db: Session, user_id: str, circle_id: str) -> StudyCircle:
    me = db.query(CircleMember).filter_by(circle_id=circle_id, user_id=user_id).first()
    if not me or me.role != "owner":
        raise PermissionError("Only the circle's owner can do that.")
    return db.get(StudyCircle, circle_id)


def remove_member(db: Session, user_id: str, circle_id: str, member_id: str) -> dict:
    _owned(db, user_id, circle_id)
    target = db.query(CircleMember).filter_by(id=member_id, circle_id=circle_id).first()
    if target and target.user_id != user_id:
        removed = target.user_id
        _drop(db, target)
        _withdraw_if_none_left(db, removed)
        db.commit()
    return board(db, user_id)


def new_invite_code(db: Session, user_id: str, circle_id: str) -> dict:
    """Old links stop working (for example if one was shared too widely)."""
    circle = _owned(db, user_id, circle_id)
    circle.invite_code = _new_code()
    db.commit()
    return board(db, user_id)


# ── progress ─────────────────────────────────────────────────────────────────

def _engs(db: Session, user_ids: list[str]) -> dict[str, UserEngagement]:
    from app.services.engagement import get_or_create
    return {uid: get_or_create(db, uid) for uid in user_ids}


def _kept(db: Session, user_ids: list[str], since: datetime.date) -> dict[str, set[datetime.date]]:
    """Days each member kept (studied, or protected by a freeze or a break)."""
    out: dict[str, set[datetime.date]] = {uid: set() for uid in user_ids}
    rows = (db.query(DailyActivity)
            .filter(DailyActivity.user_id.in_(user_ids), DailyActivity.local_date >= since,
                    or_(DailyActivity.actions > 0, DailyActivity.freeze_used.is_(True),
                        DailyActivity.on_break.is_(True))).all())
    for r in rows:
        out[r.user_id].add(r.local_date)
    return out


def _progress(db: Session, circle: StudyCircle, members: list[CircleMember]) -> dict:
    from app.services.engagement import local_today
    ids = [m.user_id for m in members]
    engs = _engs(db, ids)
    todays = {uid: local_today(engs[uid]) for uid in ids}
    newest = max(todays.values())
    started = max(m.joined_at.date() for m in members)
    kept = _kept(db, ids, min(started, newest - datetime.timedelta(days=60)))

    # Circle streak: today counts once everyone has kept it; until then, from yesterday.
    day = newest if all(newest in kept[uid] for uid in ids) else newest - datetime.timedelta(days=1)
    streak = 0
    while day >= started and all(day in kept[uid] for uid in ids):
        streak += 1
        day -= datetime.timedelta(days=1)

    active: dict[str, int] = {}
    for uid in ids:
        start = _week_start(todays[uid])
        active[uid] = (db.query(DailyActivity)
                       .filter(DailyActivity.user_id == uid, DailyActivity.actions > 0,
                               DailyActivity.local_date >= start, DailyActivity.local_date <= todays[uid]).count())
    studied_today = {uid: bool((r := db.get(DailyActivity, (uid, todays[uid]))) and r.actions > 0) for uid in ids}
    return {"streak": streak, "active": active, "studied_today": studied_today,
            "target": GOAL_DAYS_PER_MEMBER * len(ids), "done": sum(active.values())}


def claim_rewards(db: Session, eng: UserEngagement, today: datetime.date, award) -> list[str]:
    """Book this learner's weekly circle bonus for every circle whose goal is met.
    Returns the names of circles that paid out now. Caller commits."""
    paid = []
    for m in _memberships(db, eng.user_id):
        circle = db.get(StudyCircle, m.circle_id)
        members = db.query(CircleMember).filter(CircleMember.circle_id == m.circle_id).all()
        if not circle or len(members) < 2:
            continue  # a circle of one has no shared goal
        p = _progress(db, circle, members)
        if p["done"] >= p["target"] and award("circle_goal", f"{circle.id}@{_week_start(today).isoformat()}", GOAL_XP):
            paid.append(circle.name)
    return paid


def _display(name: str | None) -> str:
    from app.services.leagues import display_name
    return display_name(name)


def board(db: Session, user_id: str) -> dict:
    """Every circle the learner is in, ready to show. Also books their weekly
    circle bonus if a goal was met while they were away."""
    from app.services.engagement import book_bonus, get_or_create, local_today
    eng = get_or_create(db, user_id)
    today = local_today(eng)
    claim_rewards(db, eng, today, lambda kind, sid, xp: book_bonus(db, eng, kind, sid, xp))
    db.commit()

    out = []
    for m in sorted(_memberships(db, user_id), key=lambda m: m.joined_at):
        circle = db.get(StudyCircle, m.circle_id)
        members = (db.query(CircleMember).filter(CircleMember.circle_id == m.circle_id)
                   .order_by(CircleMember.joined_at.asc()).all())
        if not circle:
            continue
        if not any(x.role == "owner" for x in members):  # owner's account was deleted
            members[0].role = "owner"
            db.commit()
        p = _progress(db, circle, members)
        names = dict(db.query(User.id, User.name).filter(User.id.in_([x.user_id for x in members])).all())
        rewarded = db.query(XpEvent).filter_by(
            user_id=user_id, source_type="circle_goal",
            source_id=f"{circle.id}@{_week_start(today).isoformat()}").first() is not None
        out.append({
            "id": circle.id,
            "name": circle.name,
            "invite_code": circle.invite_code,
            "you_own": m.role == "owner",
            "streak": p["streak"],
            "week": {"done": min(p["done"], p["target"]), "target": p["target"],
                     "met": p["done"] >= p["target"] and len(members) > 1, "rewarded": rewarded, "reward_xp": GOAL_XP},
            "members": [{
                "id": x.id,
                "name": _display(names.get(x.user_id)),
                "you": x.user_id == user_id,
                "owner": x.role == "owner",
                "studied_today": p["studied_today"][x.user_id],
                "days_this_week": p["active"][x.user_id],
            } for x in members],
        })
    return {"circles": out, "max_circles": MAX_CIRCLES, "max_members": MAX_MEMBERS}
