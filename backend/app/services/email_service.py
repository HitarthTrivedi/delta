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


def send_nudge_email(
    to_email: str,
    user_name: str,
    streak: int,
    pending_tasks: list[str],
    fresh_start: bool,
    open_url: str,
    unsubscribe_url: str | None,
) -> bool:
    """The opt-in study reminder: one short, friendly nudge, sent at the time the
    learner chose and only on days they haven't studied yet. Copy rules: no guilt,
    no false urgency, easy to turn off (CCPA dark-pattern guidelines)."""
    if not email_configured():
        return False
    first = escape(str(user_name).split()[0]) if user_name else "there"
    if fresh_start:
        subject = f"A fresh week, {first}. Want to pick it back up?"
        heading = "New week, clean slate."
        line = "No catching up needed. Five minutes today is a great restart."
    elif streak > 0:
        subject = f"{first}, 5 minutes keeps your {streak}-day streak going"
        heading = f"You're on a {streak}-day streak."
        line = "Today's Quick 5 takes about five minutes. That's all it takes to keep it going."
    else:
        subject = f"{first}, your Quick 5 is ready"
        heading = "Five minutes, five questions."
        line = "A short review today makes tomorrow easier. Start whenever you're ready."
    tasks = "".join(
        f'<li style="margin:0 0 6px;color:#3d3b37;font-size:14px;line-height:1.5;">{escape(t)}</li>'
        for t in pending_tasks[:3]
    )
    tasks_block = (f'<p style="margin:22px 0 8px;font-size:13px;color:#66645e;">Also on your plan this week:</p>'
                   f'<ul style="margin:0;padding-left:18px;">{tasks}</ul>') if tasks else ""
    off = (f'<a href="{escape(unsubscribe_url)}" style="color:#66645e;">Turn off reminders</a>'
           if unsubscribe_url else "Turn reminders off any time in Delta, under Today &rarr; Reminders")
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f7f5f0;font-family:-apple-system,BlinkMacSystemFont,'Manrope',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f5f0;padding:32px 16px;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e6e4df;max-width:520px;width:100%;">
        <tr><td style="padding:30px 32px 8px;">
          <p style="margin:0 0 10px;font-size:13px;color:#7d252b;font-weight:700;">Delta &middot; Aria</p>
          <h1 style="margin:0 0 10px;font-size:24px;line-height:1.3;color:#1a1918;font-family:Georgia,serif;font-weight:600;">{heading}</h1>
          <p style="margin:0;font-size:15px;line-height:1.6;color:#3d3b37;">Hi {first}! {line}</p>
          {tasks_block}
        </td></tr>
        <tr><td style="padding:24px 32px 30px;">
          <a href="{escape(open_url)}" style="display:inline-block;background:#1a1918;color:#ffffff;font-size:15px;font-weight:700;padding:13px 28px;text-decoration:none;">Start today's 5 minutes</a>
        </td></tr>
        <tr><td style="padding:16px 32px;border-top:1px solid #e6e4df;">
          <p style="margin:0;font-size:12px;line-height:1.6;color:#66645e;">
            You're getting this because you turned on study reminders, at the time you chose. {off}.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""
    return _dispatch(to_email, user_name, subject, html)


def send_weekly_brief_email(user_email: str, brief_data: dict) -> bool:
    """Legacy stub — kept for compatibility."""
    logger.info("[EMAIL STUB] Would send brief to %s", user_email)
    return True
