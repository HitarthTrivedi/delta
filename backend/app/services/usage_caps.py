"""Monthly AI caps per plan and feature.

A learner's plan is derived, not stored: "college" while they hold an active
seat at a live college, otherwise "solo". ("pro" waits for payments.) Caps
come from config (DEFAULT_AI_CAPS, overridable with AI_CAPS_JSON); a feature
without a cap is unlimited. Uses are counted per learner per month with an
atomic claim, and refunded when the AI call behind them fails.
"""
from __future__ import annotations

import calendar
import contextlib
import datetime
import json
import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import DEFAULT_AI_CAPS, settings
from app.models.ai_usage import AiFeatureUse

logger = logging.getLogger("delta.usage_caps")
FEATURES = {
    "chat": "chat messages",
    "theory_test": "practice tests",
    "mock_interview": "mock interviews",
    "coding_problem": "coding problems",
    "resume": "résumé reads and rewrites",
    "job_match": "job ad checks",
    "opportunities": "opportunity board refreshes",
    "brief_regenerate": "plan regenerations",
    "intake": "intake answers",
    "readiness_check": "verified readiness re-checks",
}


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def caps() -> dict[str, dict[str, int]]:
    out = {plan: dict(features) for plan, features in DEFAULT_AI_CAPS.items()}
    raw = (settings.AI_CAPS_JSON or "").strip()
    if raw:
        try:
            for plan, features in json.loads(raw).items():
                out.setdefault(plan, {}).update({k: int(v) for k, v in (features or {}).items()})
        except (ValueError, TypeError, AttributeError):
            logger.error("AI_CAPS_JSON is not valid JSON; using the defaults")
    return out


def plan_for(db: Session, user_id: str) -> str:
    from app.models.college import College, CollegeMember
    from app.services.compliance import college_is_live
    row = (db.query(College).join(CollegeMember, CollegeMember.college_id == College.id)
           .filter(CollegeMember.user_id == user_id, CollegeMember.status == "active").first())
    return "college" if row and college_is_live(row) else "solo"


def cap_for(plan: str, feature: str) -> int | None:
    return caps().get(plan, {}).get(feature)


def month_key(now: datetime.datetime | None = None) -> str:
    return (now or _now()).strftime("%Y-%m")


def resets_on(now: datetime.datetime | None = None) -> datetime.date:
    now = now or _now()
    last = calendar.monthrange(now.year, now.month)[1]
    return now.date().replace(day=last) + datetime.timedelta(days=1)


def _over_cap_message(feature: str, cap: int, now: datetime.datetime | None = None) -> str:
    now = now or _now()
    nxt = resets_on(now)
    return (f"You've used your {cap} {FEATURES.get(feature, feature)} for {now.strftime('%B')}. "
            f"More on {nxt.day} {nxt.strftime('%B')}.")


def claim(db: Session, user_id: str, feature: str) -> tuple[bool, int | None]:
    """Count one use if the learner is under the cap. Returns (allowed, cap)."""
    cap = cap_for(plan_for(db, user_id), feature)
    if cap is None:
        return True, None
    month = month_key()
    for _ in range(2):
        updated = (db.query(AiFeatureUse)
                   .filter(AiFeatureUse.user_id == user_id, AiFeatureUse.feature == feature,
                           AiFeatureUse.month == month, AiFeatureUse.count < cap)
                   .update({AiFeatureUse.count: AiFeatureUse.count + 1}, synchronize_session=False))
        if updated:
            db.commit()
            return True, cap
        exists = db.query(AiFeatureUse.id).filter(AiFeatureUse.user_id == user_id, AiFeatureUse.feature == feature,
                                                  AiFeatureUse.month == month).first()
        if exists:
            db.rollback()
            return False, cap
        if cap <= 0:
            return False, cap
        try:
            db.add(AiFeatureUse(user_id=user_id, feature=feature, month=month, count=1))
            db.commit()
            return True, cap
        except IntegrityError:  # someone else created this month's row first: try the update again
            db.rollback()
    return False, cap


def refund(db: Session, user_id: str, feature: str) -> None:
    (db.query(AiFeatureUse)
     .filter(AiFeatureUse.user_id == user_id, AiFeatureUse.feature == feature, AiFeatureUse.month == month_key(),
             AiFeatureUse.count > 0)
     .update({AiFeatureUse.count: AiFeatureUse.count - 1}, synchronize_session=False))
    db.commit()


def ensure_room(db: Session, user_id: str, feature: str) -> None:
    """Raise the over-cap 429 if no use is left this month, without counting one."""
    cap = cap_for(plan_for(db, user_id), feature)
    if cap is None:
        return
    row = db.query(AiFeatureUse).filter(AiFeatureUse.user_id == user_id, AiFeatureUse.feature == feature,
                                        AiFeatureUse.month == month_key()).first()
    if row and row.count >= cap:
        raise HTTPException(status_code=429, detail=_over_cap_message(feature, cap))


def take(db: Session, user_id: str, feature: str) -> None:
    """Count one use, or raise the over-cap 429. For long routes where wrapping
    the AI call in `using` isn't practical (no refund on failure)."""
    allowed, cap = claim(db, user_id, feature)
    if not allowed:
        raise HTTPException(status_code=429, detail=_over_cap_message(feature, cap or 0))


@contextlib.contextmanager
def using(db: Session, user_id: str, feature: str):
    """`with using(db, uid, "theory_test"):` around one AI use. Over the cap it
    raises a 429 with the reset date; if the body fails, the use is refunded."""
    allowed, cap = claim(db, user_id, feature)
    if not allowed:
        raise HTTPException(status_code=429, detail=_over_cap_message(feature, cap or 0))
    try:
        yield
    except BaseException:
        try:
            db.rollback()
            refund(db, user_id, feature)
        except Exception as exc:  # noqa: BLE001
            logger.warning("refund failed for %s/%s: %s", user_id, feature, exc)
        raise


def usage(db: Session, user_id: str) -> dict:
    plan = plan_for(db, user_id)
    month = month_key()
    used = {r.feature: r.count for r in db.query(AiFeatureUse).filter(AiFeatureUse.user_id == user_id,
                                                                     AiFeatureUse.month == month)}
    plan_caps = caps().get(plan, {})
    return {"plan": plan, "month": month, "resets_on": resets_on().isoformat(),
            "features": [{"feature": f, "label": label, "used": used.get(f, 0), "cap": plan_caps.get(f)}
                         for f, label in FEATURES.items()]}
