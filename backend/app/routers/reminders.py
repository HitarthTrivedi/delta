"""Manual reminder trigger.

Reminders normally fire from the in-process scheduler in reminder_service (Railway
cron proved unreliable). This endpoint stays for on-demand testing — it forces a
send, bypassing the once-a-day guard, so you can verify the email without waiting
for the scheduled hour.
"""
import hmac
import logging
import threading

from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.services.reminder_service import run_daily_reminders

logger = logging.getLogger("delta.reminders")
router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.post("/daily", status_code=202)
def trigger_daily_reminders(
    x_reminder_secret: str = Header(default=""),
):
    """Force a reminder run for all users, ignoring the once-a-day guard.

    Returns 202 immediately and sends in a background thread so the caller never
    blocks on the email round-trips.

    Protected by X-Reminder-Secret matching the REMINDER_SECRET env var:
        curl -X POST https://<backend>/api/reminders/daily \\
             -H "X-Reminder-Secret: <REMINDER_SECRET>"
    """
    if not settings.REMINDER_SECRET:
        raise HTTPException(status_code=503, detail="REMINDER_SECRET not configured.")
    if not hmac.compare_digest(x_reminder_secret or "", settings.REMINDER_SECRET):
        raise HTTPException(status_code=401, detail="Invalid reminder secret.")

    threading.Thread(
        target=run_daily_reminders,
        kwargs={"force": True},
        name="delta-reminders-manual",
        daemon=True,
    ).start()
    return {"status": "accepted", "message": "Reminder run started. Check server logs for results."}
