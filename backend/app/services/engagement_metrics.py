"""Retention metrics for admins, computed from our own records only (no
third-party analytics). Aggregates only: no per-learner data leaves here.

Return windows (by signup date): day 1 = active the day after signing up;
week 2 = active on any of days 7-13; month 1 = active on any of days 30-36.
"Active" = at least one real learning action (frozen/break days don't count).
"""
from __future__ import annotations

import datetime

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import ConsentRecord, DailyActivity, NudgeLog, User, UserEngagement, XpEvent
from app.services import compliance

WINDOWS = {"day_1": (1, 1), "week_2": (7, 13), "month_1": (30, 36)}


def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def retention_metrics(db: Session, today: datetime.date | None = None, weeks: int = 8) -> dict:
    today = today or datetime.date.today()
    active = {}  # user_id -> set of active dates
    since = today - datetime.timedelta(days=7 * weeks + 40)
    for uid, d in (db.query(DailyActivity.user_id, DailyActivity.local_date)
                   .filter(DailyActivity.actions > 0, DailyActivity.local_date >= since)):
        active.setdefault(uid, set()).add(d)

    cohorts = []
    start = today - datetime.timedelta(days=today.weekday() + 7 * (weeks - 1))
    for w in range(weeks):
        week_start = start + datetime.timedelta(days=7 * w)
        week_end = week_start + datetime.timedelta(days=7)
        users = db.query(User.id, User.created_at).filter(
            User.created_at >= datetime.datetime.combine(week_start, datetime.time()),
            User.created_at < datetime.datetime.combine(week_end, datetime.time())).all()
        row = {"week_of": week_start.isoformat(), "signups": len(users)}
        for name, (lo, hi) in WINDOWS.items():
            eligible = returned = 0
            for uid, created in users:
                signup = created.date()
                if signup + datetime.timedelta(days=hi) > today:
                    continue  # window not finished yet
                eligible += 1
                days = active.get(uid, set())
                if any(signup + datetime.timedelta(days=k) in days for k in range(lo, hi + 1)):
                    returned += 1
            row[name] = _pct(returned, eligible)
        cohorts.append(row)

    def users_active_since(n: int) -> set[str]:
        cut = today - datetime.timedelta(days=n - 1)
        return {u for u, ds in active.items() if any(d >= cut for d in ds)}

    dau, wau, mau = users_active_since(1), users_active_since(7), users_active_since(30)
    streaky = db.query(UserEngagement).filter(UserEngagement.user_id.in_(wau or {""}),
                                              UserEngagement.current_streak >= 7).count() if wau else 0
    week_ago = today - datetime.timedelta(days=6)
    quick5 = db.query(func.count(XpEvent.id)).filter(XpEvent.source_type == "quick_review",
                                                     XpEvent.local_date >= week_ago).scalar() or 0

    opted_in = db.query(UserEngagement).filter(UserEngagement.reminders_opt_in.is_(True)).count()
    month_ago = datetime.datetime.combine(today - datetime.timedelta(days=29), datetime.time())
    opt_outs = db.query(ConsentRecord).filter(ConsentRecord.purpose == compliance.LEARNING_REMINDERS,
                                              ConsentRecord.action == "withdrawn",
                                              ConsentRecord.created_at >= month_ago).count()
    nudged = db.query(UserEngagement).filter(UserEngagement.last_nudged_on >= week_ago,
                                             UserEngagement.last_nudged_on < today).all()
    came_back = sum(1 for e in nudged if {e.last_nudged_on, e.last_nudged_on + datetime.timedelta(days=1)}
                    & active.get(e.user_id, set()))
    # How each reminder wording does (what the bandit is learning from).
    wordings = [
        {"variant": v, "sent_90d": int(n), "studied_same_day_pct": _pct(int(r or 0), int(n))}
        for v, n, r in db.query(NudgeLog.variant, func.count(NudgeLog.id),
                                func.sum(case((NudgeLog.returned.is_(True), 1), else_=0)))
        .filter(NudgeLog.local_date >= today - datetime.timedelta(days=89))
        .group_by(NudgeLog.variant).order_by(NudgeLog.variant).all()
    ]

    return {
        "as_of": today.isoformat(),
        "cohorts": cohorts,
        "active": {"dau": len(dau), "wau": len(wau), "mau": len(mau), "dau_over_wau": _pct(len(dau), len(wau))},
        "habit": {"weekly_active_on_7_day_streak_pct": _pct(streaky, len(wau)), "quick5_completions_7d": quick5},
        "reminders": {"opted_in": opted_in, "opt_outs_30d": opt_outs,
                      "nudged_last_7d": len(nudged), "studied_within_a_day_after_nudge_pct": _pct(came_back, len(nudged)),
                      "wordings": wordings},
    }
