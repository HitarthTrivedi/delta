"""Daily-habit engine: streaks, XP, levels, daily goal, freezes, break mode.

Design rules (see the gamification plan in the Master Plan):
- Habit before intensity: ANY one real learning action keeps the streak; the
  daily goal is separate and only adds a bonus.
- Reward learning, not clicking: XP is awarded here, server-side, only for
  actions verified against our own records, once per source.
- Forgiving: missed days use streak freezes, break mode pauses the streak,
  and a broken streak can be repaired within a short window.
- XP never touches readiness, sandbox scores or recruiter-facing data.
- Children (Delta for School) never reach this module.

Everything is evaluated lazily in the learner's own timezone (no cron job):
reading or recording activity first "rolls" the streak forward to yesterday.
"""
from __future__ import annotations

import datetime
import json
import logging
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.career_os import RoadmapState
from app.models.engagement import DailyActivity, UserEngagement, XpEvent
from app.models.recommendation import Recommendation
from app.models.sandbox_session import SandboxSession

_log = logging.getLogger("delta.engagement")

# XP per verified learning action.
XP_TABLE = {
    "weekly_task": 20,
    "quick_review": 10,
    "quick_review_perfect": 5,
    "test": 15,
    "interview": 30,
    "coding": 25,
    "recommendation": 20,
    "daily_goal": 10,
}
GOAL_MINUTES = (5, 10, 20)
XP_PER_GOAL_MINUTE = 2           # 10-minute goal = 20 XP a day
FREEZE_EVERY_DAYS = 7            # a 7-day streak earns a freeze
MAX_FREEZES = 2
BREAK_DAYS_PER_MONTH = 7
REPAIR_WINDOW_DAYS = 2           # win a lost streak back within 2 days...
REPAIR_GOAL_DAYS = 2             # ...by meeting the daily goal on 2 days
TASK_REAWARD_DAYS = 7            # one award per plan task per week
CONSISTENT_DAYS = 20             # "Consistent learner": studied on 20+...
CONSISTENT_WINDOW_DAYS = 30      # ...of the last 30 days

# Cumulative XP needed for each level; beyond the table, +800 XP per level.
LEVEL_XP = [0, 50, 150, 300, 500, 800, 1200, 1700, 2300, 3000]
LEVEL_NAMES = [
    (1, "Getting started"),
    (3, "Building momentum"),
    (5, "Steady learner"),
    (7, "Sharp"),
    (9, "Unstoppable"),
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _tz(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or settings.REMINDER_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("Asia/Kolkata")


def valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def _now() -> datetime.datetime:
    """The current UTC time (one place, so tests can move the clock)."""
    return datetime.datetime.now(datetime.timezone.utc)


def local_today(eng: UserEngagement, now: datetime.datetime | None = None) -> datetime.date:
    return (now or _now()).astimezone(_tz(eng.timezone)).date()


def goal_xp(eng: UserEngagement) -> int:
    return (eng.daily_goal_minutes or 10) * XP_PER_GOAL_MINUTE


def level_for(xp: int) -> dict:
    level = 1
    for i, threshold in enumerate(LEVEL_XP):
        if xp >= threshold:
            level = i + 1
    extra = 0
    if xp >= LEVEL_XP[-1]:
        extra = (xp - LEVEL_XP[-1]) // 800
        level = len(LEVEL_XP) + extra
    floor = LEVEL_XP[level - 1] if level <= len(LEVEL_XP) else LEVEL_XP[-1] + extra * 800
    ceiling = LEVEL_XP[level] if level < len(LEVEL_XP) else floor + 800
    name = LEVEL_NAMES[0][1]
    for min_level, label in LEVEL_NAMES:
        if level >= min_level:
            name = label
    return {"level": level, "name": name, "xp_into_level": xp - floor, "xp_for_next": ceiling - floor}


def get_or_create(db: Session, user_id: str, timezone: str | None = None) -> UserEngagement:
    eng = db.get(UserEngagement, user_id)
    if eng is None:
        eng = UserEngagement(
            user_id=user_id,
            timezone=timezone if timezone and valid_timezone(timezone) else settings.REMINDER_TIMEZONE,
            daily_goal_minutes=10, current_streak=0, longest_streak=0, streak_freezes=0,
            repair_streak=0, repair_progress=0, break_days_used=0, xp_total=0,
            reminders_opt_in=False, reminder_channel="email", ignored_nudges=0,
        )
        db.add(eng)
        db.flush()
    return eng


def _day(db: Session, user_id: str, d: datetime.date) -> DailyActivity:
    row = db.get(DailyActivity, (user_id, d))
    if row is None:
        row = DailyActivity(user_id=user_id, local_date=d, xp=0, actions=0,
                            goal_met=False, freeze_used=False, on_break=False)
        db.add(row)
        db.flush()
    return row


# ── streak ───────────────────────────────────────────────────────────────────

def roll_forward(db: Session, eng: UserEngagement, today: datetime.date) -> None:
    """Settle every missed day up to yesterday: break mode or a freeze keeps
    the streak alive; otherwise it breaks (and a repair window opens)."""
    if eng.repair_deadline and today > eng.repair_deadline:
        eng.repair_streak, eng.repair_deadline, eng.repair_progress = 0, None, 0
    if not eng.last_active_date or eng.current_streak <= 0:
        return
    d = eng.last_active_date + datetime.timedelta(days=1)
    while d < today:
        if eng.break_until and d <= eng.break_until:
            _day(db, eng.user_id, d).on_break = True
        elif eng.streak_freezes > 0:
            eng.streak_freezes -= 1
            _day(db, eng.user_id, d).freeze_used = True
        else:
            # Streak broken. Offer a repair window instead of starting over cold.
            if eng.current_streak >= 3:
                eng.repair_streak = eng.current_streak
                eng.repair_deadline = d + datetime.timedelta(days=REPAIR_WINDOW_DAYS)
                eng.repair_progress = 0
            eng.current_streak = 0
            return
        eng.last_active_date = d
        d += datetime.timedelta(days=1)


def _extend_streak(eng: UserEngagement, today: datetime.date) -> None:
    if eng.last_active_date == today:
        return
    if eng.last_active_date == today - datetime.timedelta(days=1) and eng.current_streak > 0:
        eng.current_streak += 1
    else:
        eng.current_streak = 1
    eng.last_active_date = today
    if eng.current_streak % FREEZE_EVERY_DAYS == 0:
        eng.streak_freezes = min(MAX_FREEZES, eng.streak_freezes + 1)
    eng.longest_streak = max(eng.longest_streak, eng.current_streak)


def _on_goal_met(eng: UserEngagement, today: datetime.date) -> None:
    if eng.repair_streak and eng.repair_deadline and today <= eng.repair_deadline:
        eng.repair_progress += 1
        if eng.repair_progress >= REPAIR_GOAL_DAYS:
            # Restore the old streak plus the days spent winning it back.
            eng.current_streak = eng.repair_streak + eng.current_streak
            eng.longest_streak = max(eng.longest_streak, eng.current_streak)
            eng.repair_streak, eng.repair_deadline, eng.repair_progress = 0, None, 0


# ── verification of claimed activity ────────────────────────────────────────

def _current_task_keys(db: Session, user_id: str) -> set[str]:
    roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == user_id).first()
    if not roadmap or not roadmap.weekly_focus:
        return set()
    try:
        actions = (json.loads(roadmap.weekly_focus) or {}).get("primary_actions") or []
    except (TypeError, ValueError):
        return set()
    keys = set()
    for a in actions:
        if isinstance(a, dict):
            for k in ("id", "title"):
                if a.get(k):
                    keys.add(str(a[k]).strip().lower())
    return keys


def _completed_session(db: Session, user_id: str, session_id: str | None, kind: str) -> SandboxSession | None:
    if not session_id:
        return None
    s = db.get(SandboxSession, session_id)
    if s and s.user_id == user_id and s.type == kind and s.status == "completed":
        return s
    return None


# ── recording ────────────────────────────────────────────────────────────────

def record_activity(db: Session, user_id: str, source_type: str, source_id: str,
                    repeat_key: str | None = None, bonus_xp: int = 0) -> dict:
    """Award XP once for a verified learning action and extend the streak.
    Returns what changed, for celebrations. Commits."""
    eng = get_or_create(db, user_id)
    today = local_today(eng)
    roll_forward(db, eng, today)

    if db.query(XpEvent).filter_by(user_id=user_id, source_type=source_type, source_id=source_id).first():
        db.commit()
        return {"awarded": 0, "duplicate": True}

    xp = XP_TABLE.get(source_type, 0) + bonus_xp
    if repeat_key and db.query(XpEvent).filter_by(user_id=user_id, source_type=source_type,
                                                  repeat_key=repeat_key, local_date=today).first():
        xp = 0  # same test/problem again today: still practice (keeps the streak), no extra XP

    xp_before = eng.xp_total
    db.add(XpEvent(id=str(uuid.uuid4()), user_id=user_id, source_type=source_type, source_id=source_id,
                   repeat_key=repeat_key, xp=xp, local_date=today))
    day = _day(db, user_id, today)
    day.xp += xp
    day.actions += 1
    eng.xp_total += xp
    eng.ignored_nudges = 0  # they came back: reminders return to the normal rhythm
    _extend_streak(eng, today)

    def award(kind: str, sid: str, amount: int) -> bool:
        """Book a bonus (goal, quests, weekly challenge) at most once."""
        if db.query(XpEvent).filter_by(user_id=user_id, source_type=kind, source_id=sid).first():
            return False
        db.add(XpEvent(id=str(uuid.uuid4()), user_id=user_id, source_type=kind, source_id=sid,
                       xp=amount, local_date=today))
        day.xp += amount
        eng.xp_total += amount
        return True

    goal_just_met = False

    def check_goal() -> None:
        nonlocal goal_just_met
        if not day.goal_met and day.xp >= goal_xp(eng):
            day.goal_met = goal_just_met = True
            award("daily_goal", today.isoformat(), XP_TABLE["daily_goal"])
            _on_goal_met(eng, today)

    from app.services import badges, quests
    check_goal()
    db.flush()
    quest = quests.evaluate(db, eng, today, award)
    check_goal()  # the quest bonus can complete the goal
    db.flush()
    new_badges = badges.check(db, eng)
    db.commit()

    if eng.leagues_opt_in:
        try:
            from app.services import leagues
            leagues.ensure_membership(db, eng)
        except Exception:  # a league hiccup must never cost the learner their XP
            _log.exception("league membership failed for %s", user_id)
            db.rollback()

    return {
        "awarded": eng.xp_total - xp_before,
        "goal_met": goal_just_met,
        "streak": eng.current_streak,
        "level_up": level_for(eng.xp_total)["level"] > level_for(xp_before)["level"],
        "level": level_for(eng.xp_total)["level"],
        "quests_done": quest["quests_done"],
        "challenge_won": quest["challenge_won"],
        "badges": new_badges,
    }


def reverse_weekly_task(db: Session, user_id: str, task_key: str) -> int:
    """A reopened plan task gives its XP back (the streak day is kept)."""
    prefix = f"{task_key}@"
    ev = (db.query(XpEvent)
          .filter(XpEvent.user_id == user_id, XpEvent.source_type == "weekly_task",
                  XpEvent.source_id.like(prefix + "%"))
          .order_by(XpEvent.created_at.desc()).first())
    if not ev:
        return 0
    eng = get_or_create(db, user_id)
    eng.xp_total = max(0, eng.xp_total - ev.xp)
    day = db.get(DailyActivity, (user_id, ev.local_date))
    if day:
        day.xp = max(0, day.xp - ev.xp)
    db.delete(ev)
    db.commit()
    return ev.xp


def on_journey_event(db: Session, user_id: str, event_type: str, evidence: dict, impact: dict) -> dict | None:
    """Called for every journey event. Rewards only claims we can verify."""
    evidence = evidence or {}
    impact = impact or {}
    if event_type in ("weekly_task_completed", "weekly_task_reopened"):
        key = str(evidence.get("id") or evidence.get("title") or "").strip().lower()
        if not key or key not in _current_task_keys(db, user_id):
            return None
        if event_type == "weekly_task_reopened":
            reverse_weekly_task(db, user_id, key)
            return None
        eng = get_or_create(db, user_id)
        today = local_today(eng)
        since = today - datetime.timedelta(days=TASK_REAWARD_DAYS - 1)
        recent = (db.query(XpEvent)
                  .filter(XpEvent.user_id == user_id, XpEvent.source_type == "weekly_task",
                          XpEvent.source_id.like(f"{key}@%"), XpEvent.local_date >= since).first())
        if recent:
            return None
        return record_activity(db, user_id, "weekly_task", f"{key}@{today.isoformat()}")

    if event_type == "task_completed":
        kind = evidence.get("sandbox_type")
        session_id = impact.get("sandbox_session_id")
        mapping = {"theory": "test", "coding": "coding", "interview": "interview"}
        if kind not in mapping or not _completed_session(db, user_id, session_id, kind):
            return None
        repeat = None
        if kind in ("theory", "coding"):
            repeat = str(evidence.get("topic") or evidence.get("skill") or "").strip().lower() or None
        return record_activity(db, user_id, mapping[kind], session_id, repeat_key=repeat)

    if event_type == "milestone_verified":
        rec_id = evidence.get("recommendation_id")
        rec = db.get(Recommendation, rec_id) if rec_id else None
        if rec and rec.user_id == user_id and rec.status == "completed":
            return record_activity(db, user_id, "recommendation", rec_id)
    return None


# ── reading / settings ───────────────────────────────────────────────────────

def summary(db: Session, user_id: str, timezone: str | None = None) -> dict:
    eng = get_or_create(db, user_id, timezone)
    today = local_today(eng)
    roll_forward(db, eng, today)
    db.commit()
    day = db.get(DailyActivity, (user_id, today))
    done_today = bool(day and day.actions > 0)
    week = []
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        row = db.get(DailyActivity, (user_id, d))
        week.append({
            "date": d.isoformat(),
            "active": bool(row and row.actions > 0),
            "goal_met": bool(row and row.goal_met),
            "protected": bool(row and (row.freeze_used or row.on_break)),
        })
    on_break = bool(eng.break_until and today <= eng.break_until)
    quick_done = db.query(XpEvent).filter_by(user_id=user_id, source_type="quick_review",
                                             source_id=today.isoformat()).first() is not None
    month = today.strftime("%Y-%m")
    break_left = BREAK_DAYS_PER_MONTH - (eng.break_days_used if eng.break_month == month else 0)
    from app.services import badges, quests
    return {
        "timezone": eng.timezone,
        "today": today.isoformat(),
        "streak": eng.current_streak,
        "longest_streak": eng.longest_streak,
        "done_today": done_today,
        "quick_done_today": quick_done,
        # Streak alive through yesterday but nothing yet today: the day still counts if you study.
        "at_risk": eng.current_streak > 0 and not done_today and not on_break,
        "freezes": eng.streak_freezes,
        "max_freezes": MAX_FREEZES,
        "on_break": on_break,
        "break_until": eng.break_until.isoformat() if eng.break_until else None,
        "break_days_left": max(0, break_left),
        "repair": ({"streak": eng.repair_streak, "deadline": eng.repair_deadline.isoformat(),
                    "progress": eng.repair_progress, "needed": REPAIR_GOAL_DAYS}
                   if eng.repair_streak and eng.repair_deadline else None),
        "xp_total": eng.xp_total,
        "xp_today": day.xp if day else 0,
        "goal_minutes": eng.daily_goal_minutes,
        "goal_xp": goal_xp(eng),
        "goal_met_today": bool(day and day.goal_met),
        "level": level_for(eng.xp_total),
        "week": week,
        "study_time": eng.study_time,
        "reminders_opt_in": eng.reminders_opt_in,
        "reminder_channel": eng.reminder_channel,
        "quests": quests.state(db, eng, today),
        "badges": badges.overview(db, user_id),
        "leagues_opt_in": eng.leagues_opt_in,
    }


def start_break(db: Session, user_id: str, days: int) -> dict:
    eng = get_or_create(db, user_id)
    today = local_today(eng)
    roll_forward(db, eng, today)
    month = today.strftime("%Y-%m")
    if eng.break_month != month:
        eng.break_month, eng.break_days_used = month, 0
    allowed = BREAK_DAYS_PER_MONTH - eng.break_days_used
    if days < 1 or days > allowed:
        raise ValueError(f"You can take up to {allowed} more break day(s) this month.")
    # Break days are settled as they pass (roll_forward); studying on one still counts.
    eng.break_until = today + datetime.timedelta(days=days - 1)
    eng.break_days_used += days
    db.commit()
    return summary(db, user_id)


def end_break(db: Session, user_id: str) -> dict:
    eng = get_or_create(db, user_id)
    today = local_today(eng)
    if eng.break_until and eng.break_until >= today:
        unused = (eng.break_until - today).days
        eng.break_days_used = max(0, eng.break_days_used - unused)
        eng.break_until = today
    db.commit()
    return summary(db, user_id)


def update_settings(db: Session, user_id: str, *, timezone: str | None = None, goal_minutes: int | None = None,
                    study_time: str | None = None, reminder_channel: str | None = None) -> dict:
    eng = get_or_create(db, user_id)
    if timezone is not None:
        if not valid_timezone(timezone):
            raise ValueError("Unknown timezone.")
        eng.timezone = timezone
    if goal_minutes is not None:
        if goal_minutes not in GOAL_MINUTES:
            raise ValueError("Daily goal must be 5, 10 or 20 minutes.")
        eng.daily_goal_minutes = goal_minutes
    if study_time is not None:
        if study_time and not _valid_hhmm(study_time):
            raise ValueError("Study time must look like 20:30.")
        eng.study_time = study_time or None
    if reminder_channel is not None:
        if reminder_channel not in ("email", "push", "both"):
            raise ValueError("Unknown reminder channel.")
        eng.reminder_channel = reminder_channel
    db.commit()
    return summary(db, user_id)


# ── reminders (opt-in) ───────────────────────────────────────────────────────

def set_reminders(db: Session, user_id: str, enabled: bool, channel: str | None = None) -> dict:
    """Switch study reminders on/off. Every switch is a recorded consent event."""
    from app.services import compliance
    if enabled and not compliance.has_current_terms_consent(db, user_id):
        raise ValueError("Accept the Terms of Use and Privacy Policy first.")
    eng = get_or_create(db, user_id)
    if channel is not None:
        if channel not in ("email", "push", "both"):
            raise ValueError("Unknown reminder channel.")
        eng.reminder_channel = channel
    if bool(eng.reminders_opt_in) != bool(enabled):
        compliance.record_consent(db, user_id, compliance.LEARNING_REMINDERS, enabled)
    eng.reminders_opt_in = enabled
    eng.ignored_nudges = 0
    db.commit()
    return summary(db, user_id)


def _link_secret() -> bytes:
    secret = settings.EMAIL_LINK_SECRET or settings.REMINDER_SECRET
    return secret.encode("utf-8") if secret else b""


def unsubscribe_token(user_id: str) -> str | None:
    import hashlib
    import hmac
    secret = _link_secret()
    if not secret:
        return None
    return hmac.new(secret, f"unsubscribe:{user_id}".encode(), hashlib.sha256).hexdigest()[:40]


def verify_unsubscribe_token(user_id: str, token: str) -> bool:
    import hmac
    expected = unsubscribe_token(user_id)
    return bool(expected and token and hmac.compare_digest(expected, token))


def add_push_subscription(db: Session, user_id: str, endpoint: str, p256dh: str, auth: str) -> None:
    from app.models.engagement import PushSubscription
    sub = db.get(PushSubscription, endpoint)
    if sub is None:
        sub = PushSubscription(endpoint=endpoint, user_id=user_id, p256dh=p256dh, auth=auth)
        db.add(sub)
    else:  # same browser, maybe a different account now
        sub.user_id, sub.p256dh, sub.auth = user_id, p256dh, auth
    db.commit()


def remove_push_subscription(db: Session, user_id: str, endpoint: str) -> None:
    from app.models.engagement import PushSubscription
    sub = db.get(PushSubscription, endpoint)
    if sub and sub.user_id == user_id:
        db.delete(sub)
        db.commit()


def consistent_learners(db: Session, user_ids) -> set[str]:
    """Learners who chose to show recruiters the "Consistent learner" badge and
    studied on 20+ of the last 30 days. Recruiters get a yes/no only: no XP,
    streak or day counts leave Delta."""
    from app.services import compliance
    ids = compliance.granted_user_ids(db, compliance.RECRUITER_HABIT_BADGE, user_ids)
    if not ids:
        return set()
    since = _now().date() - datetime.timedelta(days=CONSISTENT_WINDOW_DAYS - 1)
    rows = (db.query(DailyActivity.user_id)
            .filter(DailyActivity.user_id.in_(list(ids)), DailyActivity.actions > 0,
                    DailyActivity.local_date >= since)
            .group_by(DailyActivity.user_id)
            .having(func.count(DailyActivity.local_date) >= CONSISTENT_DAYS).all())
    return {r[0] for r in rows}


def _valid_hhmm(value: str) -> bool:
    try:
        datetime.datetime.strptime(value, "%H:%M")
        return True
    except ValueError:
        return False
