"""Daily reminder endpoint — called once per day by a cron job."""
import hmac
import json
import logging
import threading
from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.database import SessionLocal
from app.models import RoadmapState, User
from app.services.email_service import send_reminder_email

logger = logging.getLogger("delta.reminders")
router = APIRouter(prefix="/api/reminders", tags=["reminders"])


def _as_json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _pending_tasks(roadmap: RoadmapState) -> list[str]:
    """Return titles of tasks in the current weekly focus."""
    weekly_focus = _as_json(roadmap.weekly_focus, {})
    actions = weekly_focus.get("primary_actions") or []
    return [a.get("title") or a.get("label") or "Task" for a in actions if a.get("title") or a.get("label")]


def _run_reminders_background():
    """
    Send reminder emails in a separate thread so the HTTP response can return
    immediately (202) without blocking the cron job's timeout window.
    """
    db = SessionLocal()
    sent = skipped = failed = 0
    try:
        users = db.query(User).all()
        for user in users:
            if not user.email:
                skipped += 1
                continue

            roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == user.id).first()
            if not roadmap:
                skipped += 1
                continue

            pending = _pending_tasks(roadmap)
            if not pending:
                skipped += 1
                continue

            week_number = getattr(roadmap, "week_number", 1) or 1
            name = user.name or user.email.split("@")[0]

            ok = send_reminder_email(
                to_email=user.email,
                user_name=name,
                pending_tasks=pending,
                week_number=week_number,
            )
            if ok:
                sent += 1
            else:
                failed += 1
    except Exception as exc:
        logger.error("Background reminder run failed: %s", exc)
    finally:
        db.close()

    logger.info("Daily reminders complete: sent=%d skipped=%d failed=%d", sent, skipped, failed)


@router.post("/daily", status_code=202)
def trigger_daily_reminders(
    x_reminder_secret: str = Header(default=""),
):
    """
    Kick off daily task reminder emails for all users with an active roadmap.

    Returns 202 immediately and sends emails in a background thread — this
    prevents cron-job HTTP timeouts regardless of how many users need emails.

    Protected by X-Reminder-Secret header matching REMINDER_SECRET env var.

    Example curl:
        curl -X POST https://<your-backend>.railway.app/api/reminders/daily \\
             -H "X-Reminder-Secret: <REMINDER_SECRET>"
    """
    if not settings.REMINDER_SECRET:
        raise HTTPException(status_code=503, detail="REMINDER_SECRET not configured.")
    if not hmac.compare_digest(x_reminder_secret or "", settings.REMINDER_SECRET):
        raise HTTPException(status_code=401, detail="Invalid reminder secret.")

    thread = threading.Thread(target=_run_reminders_background, name="delta-reminders", daemon=True)
    thread.start()
    return {"status": "accepted", "message": "Reminder run started in background. Check server logs for results."}
