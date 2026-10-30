"""Monthly AI budget: alert the admins, then degrade instead of overspending.

- At each threshold in AI_BUDGET_THRESHOLDS (% of AI_MONTHLY_BUDGET_USD) the
  admins get one email (and Sentry a warning) per month.
- At 100% Delta is "degraded" until the month ends or the budget is raised:
  every AI task uses the lite model, and optional AI features (marked with
  the `optional_ai` dependency) pause. Core features keep working.
- No budget set means no alerts and no degrading; usage is still recorded.
"""
from __future__ import annotations

import datetime
import logging
import threading
import time

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.services import ai_usage

logger = logging.getLogger("delta.ai_budget")
CHECK_EVERY_SECONDS = 60
_state = {"checked_at": 0.0, "degraded": False}
_lock = threading.Lock()


def budget() -> float | None:
    try:
        value = float((settings.AI_MONTHLY_BUDGET_USD or "").strip())
    except ValueError:
        return None
    return value if value > 0 else None


def thresholds() -> list[int]:
    out = []
    for part in (settings.AI_BUDGET_THRESHOLDS or "").split(","):
        try:
            out.append(int(part.strip()))
        except ValueError:
            continue
    return sorted({t for t in out if 0 < t <= 100}) or [100]


def _month(today: datetime.date | None = None) -> str:
    return (today or datetime.datetime.utcnow().date()).strftime("%Y-%m")


def _notify(threshold: int, spent: float, limit: float) -> None:
    subject = f"Delta AI spend at {threshold}% of this month's budget"
    note = ("Every AI task now uses the lite model and optional AI features are paused until next month "
            "or until AI_MONTHLY_BUDGET_USD is raised.") if threshold >= 100 else "Nothing changes for users yet."
    html = (f"<p>Estimated AI spend this month: <strong>${spent:.2f}</strong> of ${limit:.2f} ({threshold}%).</p>"
            f"<p>{note}</p><p>See the AI usage view in the admin console for the breakdown by task and model.</p>")
    try:
        from app.services.compliance import _email_set
        from app.services.email_service import _dispatch
        for email in sorted(_email_set(settings.ADMIN_EMAILS)):
            _dispatch(email, "Delta admin", subject, html)
    except Exception as exc:  # noqa: BLE001
        logger.warning("budget alert email failed: %s", exc)
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.capture_message(subject, level="warning")
        except Exception:  # noqa: BLE001
            pass
    logger.warning(subject)


def check(db: Session, today: datetime.date | None = None) -> dict:
    """Send any threshold alerts not yet sent this month; return the state."""
    from app.models.ai_usage import AiBudgetAlert
    limit = budget()
    spent = ai_usage.month_spend(db, today)
    if not limit:
        return {"budget": None, "spent": spent, "pct": None, "degraded": False}
    pct = 100 * spent / limit
    for t in thresholds():
        if pct >= t:
            try:
                db.add(AiBudgetAlert(month=_month(today), threshold=t, spent_usd=spent))
                db.commit()
            except IntegrityError:  # already sent this month
                db.rollback()
                continue
            _notify(t, spent, limit)
    return {"budget": limit, "spent": spent, "pct": round(pct, 1), "degraded": spent >= limit}


def after_call() -> None:
    """Called after each recorded AI call; does the real check at most once a minute per process."""
    now = time.monotonic()
    with _lock:
        if now - _state["checked_at"] < CHECK_EVERY_SECONDS:
            return
        _state["checked_at"] = now
    refresh()


def refresh() -> dict:
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        state = check(db)
    finally:
        db.close()
    _state["degraded"] = state["degraded"]
    return state


def degraded() -> bool:
    if not budget():
        return False
    if time.monotonic() - _state["checked_at"] >= CHECK_EVERY_SECONDS:
        _state["checked_at"] = time.monotonic()
        try:
            refresh()
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI budget refresh failed: %s", exc)
    return bool(_state["degraded"])


def optional_ai() -> None:
    """Dependency for AI features that can wait: paused while the budget is spent."""
    if degraded():
        raise HTTPException(status_code=503, detail="This is paused for the rest of the month. Everything else works.")


def summary(db: Session) -> dict:
    from app.models.ai_usage import AiBudgetAlert
    state = check(db)
    month = _month()
    alerts = [a.threshold for a in db.query(AiBudgetAlert).filter(AiBudgetAlert.month == month)
              .order_by(AiBudgetAlert.threshold)]
    return {**state, "month": month, "alerts_sent": alerts, "thresholds": thresholds(),
            "breakdown": ai_usage.month_breakdown(db), "routes": ai_usage.routes()}
