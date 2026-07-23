"""Email service for Delta daily reminders.

Two HTTP transports, no SMTP: Railway blocks outbound ports 25/465/587, so
smtplib can never connect from there (see commit dd8faff). Both of these send
over HTTPS/443 instead.

  Gmail API — preferred. Sends from your own mailbox, no third-party provider.
              Used whenever GMAIL_REFRESH_TOKEN is configured.
  Brevo     — fallback, kept so reminders don't stop while Gmail OAuth is set up.
"""
from __future__ import annotations

import base64
import datetime
import logging
import threading
import time
from email.message import EmailMessage
from html import escape

import requests

from app.config import settings

logger = logging.getLogger("delta.email")

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

# Access tokens last ~1h; cache and refresh so we don't hit the token endpoint
# once per recipient. Locked because the scheduler and the manual trigger can
# both be sending at the same time.
_token_cache: dict = {"value": None, "expires_at": 0.0}
_token_lock = threading.Lock()


def gmail_configured() -> bool:
    return bool(
        settings.GMAIL_CLIENT_ID
        and settings.GMAIL_CLIENT_SECRET
        and settings.GMAIL_REFRESH_TOKEN
        and settings.GMAIL_FROM_EMAIL
    )


def email_configured() -> bool:
    """True when any transport can actually send."""
    return gmail_configured() or bool(settings.BREVO_API_KEY)


def _gmail_access_token() -> str | None:
    """Exchange the long-lived refresh token for a short-lived access token."""
    with _token_lock:
        now = time.time()
        if _token_cache["value"] and now < _token_cache["expires_at"]:
            return _token_cache["value"]
        try:
            resp = requests.post(
                GMAIL_TOKEN_URL,
                data={
                    "client_id": settings.GMAIL_CLIENT_ID,
                    "client_secret": settings.GMAIL_CLIENT_SECRET,
                    "refresh_token": settings.GMAIL_REFRESH_TOKEN,
                    "grant_type": "refresh_token",
                },
                timeout=15,
            )
        except Exception as exc:
            logger.error("Gmail token request failed: %s", exc)
            return None
        if resp.status_code != 200:
            # A revoked/expired refresh token shows up here as invalid_grant.
            logger.error("Gmail token refresh rejected: %s %s", resp.status_code, resp.text)
            return None
        data = resp.json()
        token = data.get("access_token")
        if not token:
            logger.error("Gmail token response had no access_token.")
            return None
        _token_cache["value"] = token
        # Refresh a minute early so a token can't expire mid-send.
        _token_cache["expires_at"] = now + max(60, int(data.get("expires_in", 3600))) - 60
        return token


def _send_via_gmail(to_email: str, to_name: str, subject: str, html: str) -> bool:
    token = _gmail_access_token()
    if not token:
        return False

    message = EmailMessage()
    message["To"] = f"{to_name} <{to_email}>" if to_name else to_email
    message["From"] = f"{settings.GMAIL_FROM_NAME} <{settings.GMAIL_FROM_EMAIL}>"
    message["Subject"] = subject
    # Plain-text part first so clients without HTML still show something useful.
    message.set_content(
        "Your Delta reminder is best viewed as HTML. "
        f"Open your plan: {settings.FRONTEND_URL}/roadmap"
    )
    message.add_alternative(html, subtype="html")
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        resp = requests.post(
            GMAIL_SEND_URL,
            json={"raw": raw},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if resp.status_code in (200, 201):
            logger.info("Reminder sent via Gmail → %s", to_email)
            return True
        logger.error("Gmail rejected email to %s: %s %s", to_email, resp.status_code, resp.text)
        return False
    except Exception as exc:
        logger.error("Gmail send to %s failed: %s", to_email, exc)
        return False


def _send_via_brevo(to_email: str, to_name: str, subject: str, html: str) -> bool:
    payload = {
        "sender": {"name": settings.BREVO_FROM_NAME, "email": settings.BREVO_FROM_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": settings.BREVO_API_KEY,
    }
    try:
        response = requests.post(BREVO_SEND_URL, json=payload, headers=headers, timeout=15)
        if response.status_code in (200, 201):
            logger.info("Reminder sent via Brevo → %s", to_email)
            return True
        logger.error("Brevo rejected email to %s: %s %s", to_email, response.status_code, response.text)
        return False
    except Exception as exc:
        logger.error("Failed to send reminder to %s: %s", to_email, exc)
        return False


def _dispatch(to_email: str, to_name: str, subject: str, html: str) -> bool:
    """Send via Gmail when configured, otherwise Brevo."""
    if gmail_configured():
        return _send_via_gmail(to_email, to_name, subject, html)
    if settings.BREVO_API_KEY:
        return _send_via_brevo(to_email, to_name, subject, html)
    logger.warning("No email transport configured — skipping email to %s.", to_email)
    return False


def send_reminder_email(
    to_email: str,
    user_name: str,
    pending_tasks: list[str],
    week_number: int,
    personal_tasks: list[str] | None = None,
    today_tasks: list[str] | None = None,
) -> bool:
    """Send a daily reminder via Brevo: what Delta wants done today (day-plan users),
    what is still pending this week, and a check-in on the user's own daily
    commitments. Returns True on success."""
    if not email_configured():
        logger.warning("No email transport configured — skipping reminder email.")
        return False

    personal_tasks = personal_tasks or []
    today_tasks = today_tasks or []

    first_name = escape(str(user_name).split()[0]) if user_name else "there"

    if today_tasks:
        n = len(today_tasks)
        subject = f"{first_name}, your {n} move{'s' if n != 1 else ''} for today 🎯"
    elif pending_tasks:
        n = len(pending_tasks)
        subject = f"{first_name}, {n} task{'s' if n != 1 else ''} between you and a stronger week"
    else:
        subject = f"Nice work, {first_name} — you're all clear. Keep the streak?"

    # One rotating line of encouragement so the daily email never reads the same
    # twice. Deterministic by date: everyone gets the same line on a given day,
    # and it changes tomorrow — no LLM call, no per-user state.
    _LINES = [
        "Small reps, compounded weekly, are how careers actually get built.",
        "You don't have to finish it all today. You just have to start.",
        "The person you're becoming is built on ordinary days exactly like this one.",
        "One task done beats three tasks planned. Pick one and go.",
        "Momentum is a decision you make in the next five minutes.",
        "Consistency isn't intensity — it's just showing up today.",
        "Future-you is watching what you do right now. Make them proud.",
    ]
    motivation = _LINES[datetime.date.today().toordinal() % len(_LINES)]

    def _rows(items: list[str]) -> str:
        return "".join(
            f'<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a1a;'
            f'color:#cccccc;font-size:14px;line-height:1.5;">{escape(str(item))}</td></tr>'
            for item in items
        )

    # Day-plan users lead with today's slice; the weekly list then acts as context.
    today_section = f"""
        <tr><td style="padding:24px 36px 0;">
          <p style="margin:0 0 14px;font-size:11px;font-weight:700;letter-spacing:.08em;
                    text-transform:uppercase;color:#8b5a5a;">On today's plan</p>
          <table width="100%" cellpadding="0" cellspacing="0">{_rows(today_tasks)}</table>
        </td></tr>""" if today_tasks else ""

    if pending_tasks:
        heading = "Also pending this week" if today_tasks else "Pending this week"
        delta_section = f"""
        <tr><td style="padding:24px 36px;">
          <p style="margin:0 0 14px;font-size:11px;font-weight:700;letter-spacing:.08em;
                    text-transform:uppercase;color:#444;">{heading}</p>
          <table width="100%" cellpadding="0" cellspacing="0">{_rows(pending_tasks)}</table>
        </td></tr>"""
    else:
        delta_section = """
        <tr><td style="padding:24px 36px;">
          <p style="margin:0;font-size:14px;color:#cccccc;line-height:1.6;">
            No Delta tasks pending — you've cleared this week's plan. Nice work.
          </p>
        </td></tr>"""

    personal_section = f"""
        <tr><td style="padding:0 36px 24px;">
          <p style="margin:0 0 14px;font-size:11px;font-weight:700;letter-spacing:.08em;
                    text-transform:uppercase;color:#444;">Your own tasks today &mdash; did these happen?</p>
          <table width="100%" cellpadding="0" cellspacing="0">{_rows(personal_tasks)}</table>
          <p style="margin:14px 0 0;font-size:13px;color:#444;line-height:1.6;">
            These are yours, not Delta's &mdash; they're never scored or carried over.
            Keeping them visible is what keeps the week realistic.
          </p>
        </td></tr>""" if personal_tasks else ""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#000;font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#000;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#0a0a0a;border:1px solid #1f1f1f;border-radius:8px;max-width:560px;width:100%;">

        <tr><td style="padding:32px 36px 22px;border-bottom:1px solid #1a1a1a;">
          <p style="margin:0 0 14px;font-size:11px;font-weight:700;letter-spacing:.1em;
                    text-transform:uppercase;color:#8b5a5a;">Delta &middot; Week {week_number}</p>
          <h1 style="margin:0 0 12px;font-size:25px;font-weight:800;color:#fff;line-height:1.25;">
            Morning, {first_name}. Let's make today count.
          </h1>
          <p style="margin:0;font-size:15px;color:#b8b8b8;line-height:1.6;font-style:italic;">
            {motivation}
          </p>
        </td></tr>
{today_section}
{delta_section}
{personal_section}

        <tr><td style="padding:28px 36px 8px;" align="center">
          <a href="{settings.FRONTEND_URL}"
             style="display:inline-block;background:#fff;color:#000;font-size:15px;
                    font-weight:800;padding:15px 40px;border-radius:8px;text-decoration:none;">
            Open Delta &amp; get started &rarr;
          </a>
        </td></tr>

        <tr><td style="padding:14px 36px 30px;" align="center">
          <p style="margin:0;font-size:13px;color:#666;line-height:1.6;">
            Knock these out and you're a full day ahead of where you were.<br>
            Agent 2 is tracking your pace — one task is enough to keep the streak alive.
          </p>
        </td></tr>

        <tr><td style="padding:20px 36px;border-top:1px solid #1a1a1a;" align="center">
          <p style="margin:0 0 4px;font-size:12px;color:#555;">
            Sent by Delta &middot; Alpha.Kore
          </p>
          <p style="margin:0;font-size:11px;color:#333;">
            <a href="{settings.FRONTEND_URL}" style="color:#555;text-decoration:underline;">delta-kappa-pink.vercel.app</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return _dispatch(to_email, user_name, subject, html)


def send_weekly_brief_email(user_email: str, brief_data: dict) -> bool:
    """Legacy stub — kept for compatibility."""
    logger.info("[EMAIL STUB] Would send brief to %s", user_email)
    return True
