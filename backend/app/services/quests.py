"""Daily quests and the weekly challenge.

Quests are read from today's verified XP events, so there is no separate
progress table and nothing can be ticked off by hand:
- Every day: Quick 5, plus two more picked per learner and day from a small pool.
- All three done: a one-off bonus (source "quests", one per day).
- Weekly challenge: all quests done on 4 days of the week (Monday start) earns a
  streak freeze, or XP if the learner already holds the maximum.
"""
from __future__ import annotations

import datetime
import hashlib

from sqlalchemy.orm import Session

from app.models.engagement import UserEngagement, XpEvent

QUEST_BONUS_XP = 15
CHALLENGE_DAYS = 4
CHALLENGE_XP = 30  # instead of a freeze when freezes are already full

QUESTS = {
    "quick5": "Finish today's Quick 5",
    "plan_task": "Tick one task from your plan",
    "practice": "Do one practice session (test, coding or interview)",
    "goal": "Meet your daily goal",
    "two_kinds": "Do two different kinds of learning today",
}
_ROTATING = ["plan_task", "practice", "goal", "two_kinds"]


def week_start(d: datetime.date) -> datetime.date:
    return d - datetime.timedelta(days=d.weekday())


def todays_quests(db: Session, user_id: str, today: datetime.date) -> list[str]:
    """Quick 5 plus two rotating quests, stable for the learner's whole day."""
    from app.services.engagement import _current_task_keys
    seed = int(hashlib.sha256(f"{user_id}:{today.isoformat()}".encode()).hexdigest(), 16)
    pool = list(_ROTATING)
    picked = []
    for _ in range(2):
        picked.append(pool.pop(seed % len(pool)))
        seed //= 7
    if "plan_task" in picked and not _current_task_keys(db, user_id):
        picked[picked.index("plan_task")] = pool[0]  # no plan yet: swap for another quest
    return ["quick5"] + picked


_LEARNING = {"quick_review", "weekly_task", "test", "coding", "interview", "recommendation"}


def _done(key: str, events: list[XpEvent]) -> bool:
    types = {e.source_type for e in events}
    if key == "quick5":
        return "quick_review" in types
    if key == "two_kinds":
        return len(types & _LEARNING) >= 2
    if key == "plan_task":
        return "weekly_task" in types
    if key == "practice":
        return bool(types & {"test", "coding", "interview"})
    if key == "goal":
        return "daily_goal" in types
    return False


def _events(db: Session, user_id: str, day: datetime.date) -> list[XpEvent]:
    return db.query(XpEvent).filter(XpEvent.user_id == user_id, XpEvent.local_date == day).all()


def evaluate(db: Session, eng: UserEngagement, today: datetime.date, award) -> dict:
    """Award the daily quest bonus and the weekly challenge, each at most once.
    `award(source_type, source_id, xp)` books an XP event for today. Caller
    flushes pending events first and commits afterwards."""
    out = {"quests_done": False, "challenge_won": None}
    keys = todays_quests(db, eng.user_id, today)
    if not all(_done(k, _events(db, eng.user_id, today)) for k in keys):
        return out
    if not award("quests", today.isoformat(), QUEST_BONUS_XP):
        return out  # already booked today
    out["quests_done"] = True
    db.flush()

    start = week_start(today)
    if db.query(XpEvent).filter_by(user_id=eng.user_id, source_type="weekly_challenge",
                                   source_id=start.isoformat()).first():
        return out
    days = (db.query(XpEvent)
            .filter(XpEvent.user_id == eng.user_id, XpEvent.source_type == "quests",
                    XpEvent.local_date >= start, XpEvent.local_date <= today).count())
    if days >= CHALLENGE_DAYS:
        from app.services.engagement import MAX_FREEZES
        if eng.streak_freezes < MAX_FREEZES:
            eng.streak_freezes += 1
            award("weekly_challenge", start.isoformat(), 0)
            out["challenge_won"] = "freeze"
        else:
            award("weekly_challenge", start.isoformat(), CHALLENGE_XP)
            out["challenge_won"] = "xp"
    return out


def state(db: Session, eng: UserEngagement, today: datetime.date) -> dict:
    events = _events(db, eng.user_id, today)
    keys = todays_quests(db, eng.user_id, today)
    start = week_start(today)
    week = (db.query(XpEvent)
            .filter(XpEvent.user_id == eng.user_id, XpEvent.local_date >= start,
                    XpEvent.local_date <= today,
                    XpEvent.source_type.in_(["quests", "weekly_challenge"])).all())
    won = next((e for e in week if e.source_type == "weekly_challenge"), None)
    return {
        "items": [{"key": k, "title": QUESTS[k], "done": _done(k, events)} for k in keys],
        "all_done": any(e.source_type == "quests" for e in events),
        "bonus_xp": QUEST_BONUS_XP,
        "challenge": {
            "days_done": sum(1 for e in week if e.source_type == "quests"),
            "needed": CHALLENGE_DAYS,
            "won": bool(won),
            "reward": ("freeze" if won.xp == 0 else "xp") if won else None,
            "reward_xp": CHALLENGE_XP,
            "days_left": 6 - today.weekday(),
        },
    }
