"""Email service — Gmail SMTP for Delta daily reminders."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger("delta.email")


_SMTP_TIMEOUT = 20  # seconds — prevents indefinite blocking on slow/unreachable SMTP


def _smtp_connection():
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=_SMTP_TIMEOUT)
    server.ehlo()
    server.starttls()
    server.login(settings.REMINDER_FROM_EMAIL, settings.REMINDER_FROM_PASSWORD)
    return server


def send_reminder_email(to_email: str, user_name: str, pending_tasks: list[str], week_number: int) -> bool:
    """Send a daily task reminder. Returns True on success, False on skip/failure."""
    if not settings.REMINDER_FROM_EMAIL or not settings.REMINDER_FROM_PASSWORD:
        logger.warning("REMINDER_FROM_EMAIL / REMINDER_FROM_PASSWORD not set — skipping.")
        return False

    subject = f"Delta — {len(pending_tasks)} task{'s' if len(pending_tasks) != 1 else ''} still pending this week"

    task_rows = "".join(
        f'<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a1a;'
        f'color:#cccccc;font-size:14px;line-height:1.5;">{task}</td></tr>'
        for task in pending_tasks
    )

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#000;font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#000;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#0a0a0a;border:1px solid #1f1f1f;border-radius:8px;max-width:560px;width:100%;">

        <tr><td style="padding:32px 36px 24px;border-bottom:1px solid #1a1a1a;">
          <p style="margin:0 0 14px;font-size:11px;font-weight:700;letter-spacing:.1em;
                    text-transform:uppercase;color:#444;">Delta &middot; Week {week_number}</p>
          <h1 style="margin:0;font-size:24px;font-weight:800;color:#fff;line-height:1.2;">
            Hey {user_name}, finished with your usual daily tasks?
          </h1>
        </td></tr>

        <tr><td style="padding:24px 36px;">
          <p style="margin:0 0 14px;font-size:11px;font-weight:700;letter-spacing:.08em;
                    text-transform:uppercase;color:#444;">Pending this week</p>
          <table width="100%" cellpadding="0" cellspacing="0">{task_rows}</table>
        </td></tr>

        <tr><td style="padding:8px 36px 32px;">
          <a href="{settings.FRONTEND_URL}/roadmap"
             style="display:inline-block;background:#fff;color:#000;font-size:14px;
                    font-weight:700;padding:12px 28px;border-radius:6px;text-decoration:none;">
            Open Delta &rarr;
          </a>
          <p style="margin:20px 0 0;font-size:13px;color:#444;line-height:1.6;">
            If your regular daily tasks are over, get to work on your pending Delta tasks to stay on track!<br>
            Agent 2 is watching your pace.
          </p>
        </td></tr>

        <tr><td style="padding:20px 36px;border-top:1px solid #1a1a1a;">
          <p style="margin:0;font-size:12px;color:#333;">
            Sent by Delta &middot; Alpha.Kore
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Delta by Alpha.Kore <{settings.REMINDER_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with _smtp_connection() as server:
            server.sendmail(settings.REMINDER_FROM_EMAIL, to_email, msg.as_string())
        logger.info("Reminder sent → %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send reminder to %s: %s", to_email, exc)
        return False


def send_weekly_brief_email(user_email: str, brief_data: dict) -> bool:
    """Legacy stub — kept for compatibility."""
    logger.info("[EMAIL STUB] Would send brief to %s", user_email)
    return True
