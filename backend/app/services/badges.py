"""Achievement badges, earned automatically from verified activity.

Each badge has three tiers. Counts come from XP events (which only exist for
verified actions) and, for skill mastery, from skills at 8/10 or more that are
backed by practice or proof rather than only claimed. A badge, once earned,
is kept.
"""
from __future__ import annotations

import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.engagement import UserBadge, UserEngagement, XpEvent
from app.models.skill_node import SkillNode

MASTERY_LEVEL = 8

# key -> tiers of (threshold, title, description)
BADGES = {
    "streak": [(7, "Week streak", "Study 7 days in a row"),
               (30, "Month streak", "Study 30 days in a row"),
               (100, "100-day streak", "Study 100 days in a row")],
    "quick5": [(1, "First Quick 5", "Finish your first Quick 5"),
               (10, "Quick 5 regular", "Finish Quick 5 on 10 days"),
               (50, "Quick 5 habit", "Finish Quick 5 on 50 days")],
    "plan": [(1, "First plan task", "Complete your first plan task"),
             (10, "Plan keeper", "Complete 10 plan tasks"),
             (50, "Plan finisher", "Complete 50 plan tasks")],
    "tests": [(1, "First test", "Finish your first knowledge test"),
              (10, "Test taker", "Finish 10 knowledge tests"),
              (25, "Test regular", "Finish 25 knowledge tests")],
    "coding": [(1, "First solve", "Solve your first coding problem"),
               (10, "Problem solver", "Solve 10 coding problems"),
               (25, "Code regular", "Solve 25 coding problems")],
    "interviews": [(1, "First interview", "Finish your first mock interview"),
                   (5, "Interview regular", "Finish 5 mock interviews"),
                   (20, "Interview veteran", "Finish 20 mock interviews")],
    "quests": [(1, "Quest day", "Finish all daily quests on a day"),
               (7, "Quest week", "Finish all daily quests on 7 days"),
               (30, "Quest master", "Finish all daily quests on 30 days")],
    "mastery": [(1, "Skill mastered", "Reach 8/10 in a skill, backed by practice or proof"),
                (3, "Three strong skills", "Reach 8/10 in 3 skills, backed by practice or proof"),
                (5, "Five strong skills", "Reach 8/10 in 5 skills, backed by practice or proof")],
}
_EVENT_COUNTS = {"quick5": "quick_review", "plan": "weekly_task", "tests": "test", "coding": "coding",
                 "interviews": "interview", "quests": "quests"}


def _progress(db: Session, eng: UserEngagement) -> dict[str, int]:
    counts = dict(db.query(XpEvent.source_type, func.count(XpEvent.id))
                  .filter(XpEvent.user_id == eng.user_id).group_by(XpEvent.source_type).all())
    out = {key: counts.get(source, 0) for key, source in _EVENT_COUNTS.items()}
    out["streak"] = eng.longest_streak or 0
    out["mastery"] = (db.query(SkillNode)
                      .filter(SkillNode.user_id == eng.user_id, SkillNode.proficiency >= MASTERY_LEVEL,
                              SkillNode.evidence_type != "claimed").count())
    return out


def _info(key: str, tier: int) -> dict:
    """Title and description of a tier (1-based); tier 0 describes the first."""
    _, title, description = BADGES[key][max(tier, 1) - 1]
    return {"title": title, "description": description}


def check(db: Session, eng: UserEngagement) -> list[dict]:
    """Award new badges and tier-ups. Returns what was just earned. Caller
    flushes pending events first and commits afterwards."""
    have = {b.badge_key: b for b in db.query(UserBadge).filter(UserBadge.user_id == eng.user_id).all()}
    progress = _progress(db, eng)
    earned = []
    for key, tiers in BADGES.items():
        tier = sum(1 for threshold, _, _ in tiers if progress[key] >= threshold)
        row = have.get(key)
        if tier == 0 or (row and row.tier >= tier):
            continue
        if row:
            row.tier, row.earned_at = tier, datetime.datetime.utcnow()
        else:
            db.add(UserBadge(user_id=eng.user_id, badge_key=key, tier=tier, earned_at=datetime.datetime.utcnow()))
        earned.append({"key": key, "tier": tier, **_info(key, tier)})
    return earned


def listing(db: Session, eng: UserEngagement) -> list[dict]:
    """Every badge with its earned tier and progress toward the next one."""
    have = {b.badge_key: b for b in db.query(UserBadge).filter(UserBadge.user_id == eng.user_id).all()}
    progress = _progress(db, eng)
    out = []
    for key, tiers in BADGES.items():
        row = have.get(key)
        tier = row.tier if row else 0
        out.append({
            "key": key,
            "tier": tier,
            "max_tier": len(tiers),
            **_info(key, tier),
            "earned_at": row.earned_at.isoformat() if row else None,
            "progress": progress[key],
            "next": {"at": tiers[tier][0], **_info(key, tier + 1)} if tier < len(tiers) else None,
        })
    return out


def overview(db: Session, user_id: str) -> dict:
    """Small summary for the engagement payload: tiers earned and the latest badge."""
    rows = [r for r in db.query(UserBadge).filter(UserBadge.user_id == user_id).all() if r.badge_key in BADGES]
    latest = max(rows, key=lambda r: r.earned_at, default=None)
    return {
        "count": sum(r.tier for r in rows),
        "latest": {"key": latest.badge_key, "tier": latest.tier, **_info(latest.badge_key, latest.tier)} if latest else None,
    }
