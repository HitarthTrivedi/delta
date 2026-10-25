"""Study reminders: opt-in, one gentle nudge a day, at the learner's own time.

Rules (Duolingo "protect the channel" + India's CCPA dark-pattern guidelines):
- Only learners who switched reminders on (a recorded `learning_reminders`
  consent) get anything, by email and/or browser push.
- At most one nudge a day, at the study time the learner picked (or
  REMINDER_HOUR_LOCAL), and only if they haven't studied yet that day.
- Back off when ignored: after 3 ignored nudges, every other day; after 14,
  one "fresh week" note on a Monday, then silence until they come back.
- No guilt, no false urgency; every email has a one-click unsubscribe.

A daemon thread checks every REMINDER_CHECK_INTERVAL_SECONDS, and real user
traffic also triggers a check (a sleeping host would miss the thread). A
per-learner atomic claim on `last_nudged_on` guarantees one nudge per day even
across restarts and replicas.
"""
from __future__ import annotations

import datetime
import logging
import threading
import time

import requests
from sqlalchemy import update

from app.config import settings
from app.database import SessionLocal
from app.models import DailyActivity, RoadmapState, User, UserEngagement
from app.services import engagement, push_service
from app.services.email_service import email_configured, send_nudge_email

logger = logging.getLogger("delta.reminders")


# Synthetic addresses the app stamps on auto-created rows before a real email is
# known (users.py) and on seed accounts. These are undeliverable — sending to them
# just bounces back to the sender — so the sweep must skip them.
_PLACEHOLDER_EMAIL_DOMAINS = ("delta.local", "delta.dev", "example.com")


def _is_real_email(email: str | None) -> bool:
    """True only for an address we can actually deliver to."""
    if not email or "@" not in email:
        return False
    local, _, domain = email.rpartition("@")
    domain = domain.lower().strip()
    if not local or "." not in domain:  # a real domain needs a TLD
        return False
    if domain in _PLACEHOLDER_EMAIL_DOMAINS or domain.endswith(".local"):
        return False
    return True


def _supabase_base_url() -> str:
    """Project base URL (…supabase.co) derived from the configured REST URL."""
    base = (settings.SUPABASE_URL or "").strip()
    for suffix in ("/rest/v1/", "/rest/v1"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base.rstrip("/")


def _supabase_admin_email(user_id: str) -> str | None:
    """Look up a user's real email in Supabase auth via the admin API.

    Users authenticate through Supabase, so their real address lives in auth.users,
    not our local table (which only ever held a user_<id>@delta.local placeholder).
    Requires the service-role key. Returns None on any failure — the caller then
    just skips that user rather than bouncing mail to a dead address.
    """
    base = _supabase_base_url()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not base or not key:
        return None
    try:
        resp = requests.get(
            f"{base}/auth/v1/admin/users/{user_id}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=10,
        )
    except Exception as exc:
        logger.warning("Supabase admin lookup failed for %s: %s", user_id, exc)
        return None
    if resp.status_code != 200:
        logger.warning("Supabase admin lookup for %s returned %s", user_id, resp.status_code)
        return None
    email = (resp.json() or {}).get("email")
    return email if _is_real_email(email) else None


def _resolve_email(db, user: User) -> str | None:
    """Deliverable email for a user, backfilling from Supabase when ours is a
    placeholder. The real address is persisted so the lookup happens only once."""
    if _is_real_email(user.email):
        return user.email
    real = _supabase_admin_email(user.id)
    if real:
        user.email = real
        db.commit()
        logger.info("Backfilled real email for user %s from Supabase auth.", user.id)
        return real
    return None


def _pending_tasks(db, user: User, roadmap: RoadmapState) -> tuple[list[str], int]:
    """Titles of Delta tasks NOT yet completed or skipped, plus the week number.

    Uses evaluate_week_status — the same source of truth as the weekly-cycle gate
    and the UI — so a task the user already ticked off never appears in a reminder.
    """
    from app.services.central_engine import evaluate_week_status

    status = evaluate_week_status(db, user, roadmap)
    titles = [
        a.get("title") or a.get("label") or "Task"
        for a in status["incomplete_actions"]
        if a.get("title") or a.get("label")
    ]
    return titles, status["week_number"]


def _default_send_time() -> str:
    return f"{max(0, min(23, settings.REMINDER_HOUR_LOCAL)):02d}:00"


def nudge_kind(eng: UserEngagement, local_now: datetime.datetime, done_today: bool) -> str | None:
    """What to send this learner right now: "streak", "gentle", "fresh_start" or None."""
    today = local_now.date()
    if not eng.reminders_opt_in or done_today:
        return None
    if eng.break_until and today <= eng.break_until:
        return None
    if eng.last_nudged_on == today:
        return None
    if local_now.strftime("%H:%M") < (eng.study_time or _default_send_time()):
        return None
    ignored = eng.ignored_nudges or 0
    if ignored >= 15:
        return None  # silent until they come back (studying resets the count)
    if ignored == 14:
        return "fresh_start" if today.weekday() == 0 else None
    if ignored >= 3 and eng.last_nudged_on and (today - eng.last_nudged_on).days < 2:
        return None
    return "streak" if eng.current_streak > 0 else "gentle"


def _claim(db, user_id: str, today: datetime.date) -> bool:
    """Atomically mark this learner as nudged today. True only for the first caller."""
    result = db.execute(
        update(UserEngagement)
        .where(UserEngagement.user_id == user_id)
        .where((UserEngagement.last_nudged_on.is_(None)) | (UserEngagement.last_nudged_on != today))
        .values(last_nudged_on=today)
    )
    db.commit()
    return (result.rowcount or 0) > 0


def run_daily_reminders(force: bool = False) -> dict:
    """Nudge every opted-in learner who is due. Safe to call as often as you like.

    `force=True` (manual test endpoint) ignores the time of day and the daily claim,
    but still only reaches opted-in learners who haven't studied today.
    """
    db = SessionLocal()
    sent = skipped = failed = 0
    try:
        learners = db.query(UserEngagement).filter(UserEngagement.reminders_opt_in.is_(True)).all()
        for eng in learners:
            local_now = engagement._now().astimezone(engagement._tz(eng.timezone))
            today = local_now.date()
            engagement.roll_forward(db, eng, today)
            db.commit()
            day = db.get(DailyActivity, (eng.user_id, today))
            done_today = bool(day and day.actions > 0)
            kind = nudge_kind(eng, local_now, done_today)
            if force and kind is None and not done_today:
                kind = "streak" if eng.current_streak > 0 else "gentle"
            if kind is None or (not force and not _claim(db, eng.user_id, today)):
                skipped += 1
                continue

            user = db.get(User, eng.user_id)
            roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == eng.user_id).first()
            pending = _pending_tasks(db, user, roadmap)[0] if (user and roadmap) else []
            open_url = f"{settings.FRONTEND_URL.rstrip('/')}/today"
            delivered = False

            if eng.reminder_channel in ("email", "both") and user:
                email = _resolve_email(db, user)
                if email:
                    token = engagement.unsubscribe_token(eng.user_id)
                    unsub = (f"{settings.FRONTEND_URL.rstrip('/')}/unsubscribe?u={eng.user_id}&t={token}"
                             if token else None)
                    delivered |= send_nudge_email(
                        to_email=email, user_name=user.name or email.split("@")[0],
                        streak=eng.current_streak, pending_tasks=pending,
                        fresh_start=kind == "fresh_start", open_url=open_url, unsubscribe_url=unsub)

            if eng.reminder_channel in ("push", "both"):
                title = (f"Keep your {eng.current_streak}-day streak going"
                         if kind == "streak" else "Your Quick 5 is ready")
                body = "Five questions, about five minutes. Start whenever you're ready."
                delivered |= push_service.send_to_user(db, eng.user_id, title, body, open_url) > 0

            if delivered:
                eng.ignored_nudges = (eng.ignored_nudges or 0) + 1
                db.commit()
                sent += 1
            else:
                failed += 1  # no reachable channel today; the claim stops retry spam
    except Exception as exc:
        logger.error("Reminder sweep failed: %s", exc, exc_info=True)
    finally:
        db.close()
    logger.info("Reminder sweep: sent=%d skipped=%d failed=%d", sent, skipped, failed)
    return {"sent": sent, "skipped": skipped, "failed": failed}


# ── Triggers ──────────────────────────────────────────────────────────────────
# Learners pick their own times, so the sweep runs every check interval. The
# in-memory timestamp only avoids rescanning on every request; the per-learner
# claim is what guarantees one nudge a day.
_sweep_lock = threading.Lock()
_last_sweep_at = 0.0


def maybe_run_daily_sweep() -> None:
    """Run a reminder check if the interval has passed. Never blocks the caller."""
    global _last_sweep_at
    if not settings.REMINDERS_ENABLED:
        return
    interval = max(60, settings.REMINDER_CHECK_INTERVAL_SECONDS)
    now = time.monotonic()
    if _last_sweep_at and now - _last_sweep_at < interval:
        return
    with _sweep_lock:
        if _last_sweep_at and now - _last_sweep_at < interval:
            return
        _last_sweep_at = now
    threading.Thread(target=run_daily_reminders, name="delta-reminders-check", daemon=True).start()


def _scheduler_loop() -> None:
    """Heartbeat for a server that happens to stay up past the send hour.

    Delegates to the same maybe_run_daily_sweep() the request hook uses, so both
    paths share one definition of "has today's sweep already run".
    """
    interval = max(60, settings.REMINDER_CHECK_INTERVAL_SECONDS)
    logger.info("Reminder scheduler running (checking every %ds)", interval)
    while True:
        try:
            maybe_run_daily_sweep()
        except Exception as exc:
            logger.error("Reminder scheduler tick failed: %s", exc, exc_info=True)
        time.sleep(interval)


def start_reminder_scheduler() -> None:
    """Start the reminder thread. No-op when disabled or no email transport."""
    if not settings.REMINDERS_ENABLED:
        logger.info("Reminder scheduler disabled (REMINDERS_ENABLED=false).")
        return
    if not email_configured() and not push_service.push_configured():
        logger.warning("Reminder scheduler not started — no email transport or push keys configured.")
        return
    threading.Thread(target=_scheduler_loop, name="delta-reminders", daemon=True).start()
