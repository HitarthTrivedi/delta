"""Email service — stub for future SendGrid/SMTP integration."""

def send_weekly_brief_email(user_email: str, brief_data: dict) -> bool:
    """Send weekly brief email. Currently a no-op stub."""
    print(f"[EMAIL STUB] Would send brief to {user_email}")
    return True
