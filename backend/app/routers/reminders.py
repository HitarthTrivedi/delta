"""Daily reminder endpoint — called once per day by a cron job."""
import json
import logging
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
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


@router.post("/daily")
def trigger_daily_reminders(
    x_reminder_secret: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """
    Send daily task reminder emails to all users who have an active roadmap.

    Protected by X-Reminder-Secret header matching REMINDER_SECRET env var.
    Call this once per day from a Render Cron Job or cron-job.org.

    Example curl:
        curl -X POST https://<your-backend>.onrender.com/api/reminders/daily \\
             -H "X-Reminder-Secret: <REMINDER_SECRET>"
    """
    if not settings.REMINDER_SECRET:
        raise HTTPException(status_code=503, detail="REMINDER_SECRET not configured.")
    import hmac
    if not hmac.compare_digest(x_reminder_secret or "", settings.REMINDER_SECRET):
        raise HTTPException(status_code=401, detail="Invalid reminder secret.")

    users = db.query(User).all()
    sent = 0
    skipped = 0
    failed = 0

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

    logger.info("Daily reminders: sent=%d skipped=%d failed=%d", sent, skipped, failed)
    return {"sent": sent, "skipped": skipped, "failed": failed}
