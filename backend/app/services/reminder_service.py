"""Daily reminder sweep + in-process scheduler.

Railway cron proved unreliable, so reminders are driven by a daemon thread inside
the API process instead of an external trigger. The thread wakes periodically and
runs the sweep once the configured UTC hour arrives; a per-user `last_reminded_on`
date makes the sweep idempotent, so container restarts (frequent on Railway) and
multiple replicas can never double-send.

Each email answers three things for the user:
  1. what Delta wants done TODAY (day-plan users only),
  2. what is still pending for the WEEK,
  3. whether their own recurring commitments happened today.
"""
from __future__ import annotations

import datetime
import json
import logging
import threading
import time

import requests
from sqlalchemy import update

from app.config import settings
from app.database import SessionLocal
from app.models import RoadmapState, User
from app.services.email_service import send_reminder_email

logger = logging.getLogger("delta.reminders")


def _local_now() -> datetime.datetime:
    """Current time in the reminder timezone.

    Everything day-related uses this, not the server clock: on Railway the server
    runs UTC, where 'today' would roll over at 5:30am IST — mid-morning for the
    users this is meant to serve.
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo(settings.REMINDER_TIMEZONE))
    except Exception:
        # Bad tz name or missing tzdata — degrade to UTC rather than break sending.
        logger.warning(
            "REMINDER_TIMEZONE '%s' unusable — falling back to UTC.",
            settings.REMINDER_TIMEZONE,
        )
        return datetime.datetime.now(datetime.timezone.utc)


def _local_today() -> datetime.date:
    return _local_now().date()


def _past_send_hour() -> bool:
    return _local_now().hour >= settings.REMINDER_HOUR_LOCAL


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


def _as_json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


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


def _todays_delta_tasks(roadmap: RoadmapState) -> list[str]:
    """For day-plan users: the Delta work scheduled for TODAY that is still undone.

    Returns [] for week-style users (no day_plan) so the email simply omits the
    section rather than inventing a daily split the user never asked for.
    """
    if (getattr(roadmap, "plan_style", None) or "week") != "day":
        return []
    plan = _as_json(getattr(roadmap, "day_plan", None), {}) or {}
    today = _local_today().isoformat()
    for day in plan.get("days") or []:
        if day.get("date") != today:
            continue
        out = []
        for task in day.get("delta_tasks") or []:
            if task.get("done"):
                continue
            title = task.get("title") or "Task"
            note = task.get("note")
            out.append(f"{title} — {note}" if note and note != title else title)
        return out
    return []


def _personal_tasks_today(roadmap: RoadmapState) -> list[str]:
    """The user's own commitments scheduled for today (German class, work, …).

    Never tracked as Delta progress — the email only asks whether they happened,
    keeping the daily habit visible alongside the Delta work.
    """
    from app.services.day_planner import _WEEKDAYS, _cadence_days

    schedule = _as_json(getattr(roadmap, "day_schedule", None), {}) or {}
    today_key = _WEEKDAYS[_local_today().weekday()]
    labels: list[str] = []

    def _add(label: str) -> None:
        label = (label or "").strip()
        if label and label not in labels:
            labels.append(label)

    for item in schedule.get("fixed") or []:
        days = [str(d).strip().lower() for d in (item.get("days") or [])]
        if today_key in days:
            _add(item.get("label"))
    for item in schedule.get("recurring") or []:
        # Unclear cadence => assume a daily habit, matching the day planner.
        target = _cadence_days(item.get("cadence") or "") or list(_WEEKDAYS)
        if today_key in target:
            _add(item.get("label"))
    return labels


def _claim_user_for_today(db, user_id: str, today: datetime.date) -> bool:
    """Atomically mark this user as reminded today. Returns True if WE claimed it.

    The conditional UPDATE is what makes the sweep safe to run repeatedly and from
    more than one replica — only the first caller of the day gets a True back.
    """
    result = db.execute(
        update(User)
        .where(User.id == user_id)
        .where((User.last_reminded_on.is_(None)) | (User.last_reminded_on != today))
        .values(last_reminded_on=today)
    )
    db.commit()
    return (result.rowcount or 0) > 0


def run_daily_reminders(force: bool = False) -> dict:
    """Send today's reminder to every eligible user. Idempotent per user per day.

    `force=True` bypasses the once-a-day claim — used by the manual test endpoint.
    """
    db = SessionLocal()
    today = _local_today()
    sent = skipped = failed = 0
    try:
        users = db.query(User).all()
        logger.info("Reminder sweep started: %d users", len(users))

        for user in users:
            # Real users still carry a user_<id>@delta.local placeholder in our table;
            # resolve their actual address from Supabase auth (cached back after the
            # first lookup). Skip only if we genuinely can't find a deliverable one —
            # emailing a placeholder just bounces to the sender.
            email = _resolve_email(db, user)
            if not email:
                skipped += 1
                continue

            roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == user.id).first()
            if not roadmap:
                skipped += 1
                continue

            pending, week_number = _pending_tasks(db, user, roadmap)
            today_tasks = _todays_delta_tasks(roadmap)
            personal = _personal_tasks_today(roadmap)

            # Nothing to chase and nothing to ask about — don't email at all.
            if not pending and not today_tasks and not personal:
                skipped += 1
                continue

            if not force and not _claim_user_for_today(db, user.id, today):
                skipped += 1  # already reminded today
                continue

            ok = send_reminder_email(
                to_email=email,
                user_name=user.name or email.split("@")[0],
                pending_tasks=pending,
                week_number=week_number,
                personal_tasks=personal,
                today_tasks=today_tasks,
            )
            if ok:
                sent += 1
            else:
                failed += 1
                if not force:
                    # Let a failed send be retried on the next pass today.
                    db.execute(
                        update(User).where(User.id == user.id).values(last_reminded_on=None)
                    )
                    db.commit()
    except Exception as exc:
        logger.error("Reminder sweep failed: %s", exc, exc_info=True)
    finally:
        db.close()

    logger.info("Reminder sweep complete: sent=%d skipped=%d failed=%d", sent, skipped, failed)
    return {"sent": sent, "skipped": skipped, "failed": failed}


# ── Activity-triggered sweep ─────────────────────────────────────────────────
# The scheduler thread only fires while the process is alive, so a sleeping or
# restarting container can miss the window entirely. This hook closes that gap:
# the first real request of the day (someone opening the app) also wakes the
# server, and that request kicks off the sweep for everyone.
#
# Correctness does not depend on this in-memory date — the per-user
# `last_reminded_on` claim is what guarantees one email per user per day, even
# across restarts and replicas. The date is only a cheap way to avoid rescanning
# every user on every request.
_sweep_lock = threading.Lock()
_last_sweep_date: datetime.date | None = None


def maybe_run_daily_sweep() -> None:
    """Fire today's sweep if it hasn't run yet. Cheap and never blocks the caller."""
    global _last_sweep_date

    if not settings.REMINDERS_ENABLED:
        return
    today = _local_today()
    if _last_sweep_date == today:
        return  # fast path — no lock, no DB
    # Don't blast everyone at 3am because one night owl opened the app; wait for
    # the intended send hour, then let the first activity after it trigger.
    if not _past_send_hour():
        return

    with _sweep_lock:
        if _last_sweep_date == today:
            return  # another request won the race
        _last_sweep_date = today

    logger.info("Daily reminder sweep triggered by user activity.")
    threading.Thread(
        target=run_daily_reminders, name="delta-reminders-activity", daemon=True
    ).start()


def _scheduler_loop() -> None:
    """Heartbeat for a server that happens to stay up past the send hour.

    Delegates to the same maybe_run_daily_sweep() the request hook uses, so both
    paths share one definition of "has today's sweep already run".
    """
    interval = max(60, settings.REMINDER_CHECK_INTERVAL_SECONDS)
    logger.info(
        "Reminder scheduler running (from %02d:00 %s, checking every %ds)",
        settings.REMINDER_HOUR_LOCAL, settings.REMINDER_TIMEZONE, interval,
    )
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
    from app.services.email_service import email_configured, gmail_configured

    if not email_configured():
        logger.warning("Reminder scheduler not started — no email transport configured.")
        return
    logger.info("Reminder transport: %s", "Gmail API" if gmail_configured() else "Brevo")
    threading.Thread(target=_scheduler_loop, name="delta-reminders", daemon=True).start()
