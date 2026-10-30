"""Which model each AI task uses, what it costs, and the daily usage ledger.

Routes and prices come from config (DEFAULT_AI_ROUTES / DEFAULT_AI_PRICES,
overridable with AI_ROUTES_JSON / AI_PRICES_JSON). The ledger keeps calls and
tokens per day, task and model, never who made the call.
"""
from __future__ import annotations

import datetime
import json
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import DEFAULT_AI_PRICES, DEFAULT_AI_ROUTES, settings

logger = logging.getLogger("delta.ai_usage")


def _json_setting(raw: str, name: str) -> dict:
    if not (raw or "").strip():
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except ValueError:
        logger.error("%s is not valid JSON; using the defaults", name)
        return {}


def routes() -> dict[str, str]:
    return {**DEFAULT_AI_ROUTES, **_json_setting(settings.AI_ROUTES_JSON, "AI_ROUTES_JSON")}


def prices() -> dict[str, list[float]]:
    return {**DEFAULT_AI_PRICES, **_json_setting(settings.AI_PRICES_JSON, "AI_PRICES_JSON")}


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price = prices().get(model)
    if not price:
        return 0.0
    return (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000


def estimate_tokens(text: str | None) -> int:
    """When a provider doesn't report usage: about 4 characters per token."""
    return max(1, len(text or "") // 4)


def record(task: str, model: str, input_tokens: int, output_tokens: int, day: datetime.date | None = None) -> None:
    """Add one call to today's ledger row. Never raises: metering must not break AI."""
    from app.database import SessionLocal
    from app.models.ai_usage import AiUsageDaily
    day = day or datetime.datetime.utcnow().date()
    amount = cost(model, input_tokens, output_tokens)
    db = None
    try:
        db = SessionLocal()
        for _ in range(2):
            updated = (db.query(AiUsageDaily)
                       .filter(AiUsageDaily.day == day, AiUsageDaily.task == task, AiUsageDaily.model == model)
                       .update({AiUsageDaily.calls: AiUsageDaily.calls + 1,
                                AiUsageDaily.input_tokens: AiUsageDaily.input_tokens + input_tokens,
                                AiUsageDaily.output_tokens: AiUsageDaily.output_tokens + output_tokens,
                                AiUsageDaily.est_cost_usd: AiUsageDaily.est_cost_usd + amount},
                               synchronize_session=False))
            if updated:
                db.commit()
                break
            try:
                db.add(AiUsageDaily(day=day, task=task, model=model, calls=1, input_tokens=input_tokens,
                                    output_tokens=output_tokens, est_cost_usd=amount))
                db.commit()
                break
            except IntegrityError:  # another call created today's row first: update it instead
                db.rollback()
    except Exception as exc:  # noqa: BLE001
        if db is not None:
            db.rollback()
        logger.warning("AI usage not recorded (%s): %s", task, exc)
    finally:
        if db is not None:
            db.close()
    try:
        from app.services import ai_budget
        ai_budget.after_call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI budget check failed: %s", exc)


def month_bounds(today: datetime.date | None = None) -> tuple[datetime.date, datetime.date]:
    today = today or datetime.datetime.utcnow().date()
    start = today.replace(day=1)
    end = (start + datetime.timedelta(days=32)).replace(day=1)
    return start, end


def month_spend(db: Session, today: datetime.date | None = None) -> float:
    from sqlalchemy import func
    from app.models.ai_usage import AiUsageDaily
    start, end = month_bounds(today)
    total = (db.query(func.sum(AiUsageDaily.est_cost_usd))
             .filter(AiUsageDaily.day >= start, AiUsageDaily.day < end).scalar())
    return float(total or 0.0)


def month_breakdown(db: Session, today: datetime.date | None = None) -> list[dict]:
    from sqlalchemy import func
    from app.models.ai_usage import AiUsageDaily
    start, end = month_bounds(today)
    rows = (db.query(AiUsageDaily.task, AiUsageDaily.model, func.sum(AiUsageDaily.calls),
                     func.sum(AiUsageDaily.input_tokens), func.sum(AiUsageDaily.output_tokens),
                     func.sum(AiUsageDaily.est_cost_usd))
            .filter(AiUsageDaily.day >= start, AiUsageDaily.day < end)
            .group_by(AiUsageDaily.task, AiUsageDaily.model).all())
    out = [{"task": t, "model": m, "calls": int(c or 0), "input_tokens": int(i or 0), "output_tokens": int(o or 0),
            "est_cost_usd": round(float(s or 0), 4)} for t, m, c, i, o, s in rows]
    return sorted(out, key=lambda r: -r["est_cost_usd"])
