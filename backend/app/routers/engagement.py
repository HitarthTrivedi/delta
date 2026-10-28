"""Daily habit API: streak, XP, level, daily goal, break mode, badges, leagues."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import current_identity, require_owner
from app.limiter import limiter
from app.services import compliance, engagement

router = APIRouter(prefix="/api/engagement", tags=["engagement"])


class SettingsPayload(BaseModel):
    timezone: Optional[str] = Field(default=None, max_length=64)
    goal_minutes: Optional[int] = None
    study_time: Optional[str] = Field(default=None, max_length=5)  # "HH:MM", "" clears
    reminder_channel: Optional[str] = None


class BreakPayload(BaseModel):
    days: int = Field(ge=1, le=engagement.BREAK_DAYS_PER_MONTH)


@router.get("/admin/metrics")
def admin_metrics(db: Session = Depends(get_db), identity=Depends(current_identity)):
    """Retention dashboard numbers (aggregates only), for ADMIN_EMAILS."""
    if not compliance.is_admin(identity[1]):
        raise HTTPException(status_code=403, detail="Admin access required.")
    from app.services.engagement_metrics import retention_metrics
    return retention_metrics(db)


@router.get("/{user_id}")
def get_engagement(user_id: str, tz: Optional[str] = None, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    # `tz` (the browser's timezone) is only used the first time, to set up the account.
    return engagement.summary(db, user_id, timezone=tz)


@router.put("/{user_id}")
@limiter.limit("30/minute")
def put_settings(request: Request, user_id: str, payload: SettingsPayload, db: Session = Depends(get_db),
                 _: str = Depends(require_owner)):
    try:
        return engagement.update_settings(
            db, user_id, timezone=payload.timezone, goal_minutes=payload.goal_minutes,
            study_time=payload.study_time, reminder_channel=payload.reminder_channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{user_id}/break")
@limiter.limit("10/minute")
def start_break(request: Request, user_id: str, payload: BreakPayload, db: Session = Depends(get_db),
                _: str = Depends(require_owner)):
    try:
        return engagement.start_break(db, user_id, payload.days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{user_id}/break")
def end_break(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return engagement.end_break(db, user_id)


# ── Reminders (opt-in) ───────────────────────────────────────────────────────

class RemindersPayload(BaseModel):
    enabled: bool
    channel: Optional[str] = None  # email | push | both


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=10, max_length=200)
    auth: str = Field(min_length=8, max_length=100)


class PushPayload(BaseModel):
    endpoint: str = Field(min_length=10, max_length=1000)
    keys: Optional[PushKeys] = None


class UnsubscribePayload(BaseModel):
    u: str = Field(min_length=1, max_length=64)
    t: str = Field(min_length=10, max_length=80)


@router.put("/{user_id}/reminders")
@limiter.limit("20/minute")
def set_reminders(request: Request, user_id: str, payload: RemindersPayload, db: Session = Depends(get_db),
                  _: str = Depends(require_owner)):
    try:
        return engagement.set_reminders(db, user_id, payload.enabled, payload.channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{user_id}/badges")
def get_badges(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    from app.services import badges
    eng = engagement.get_or_create(db, user_id)
    badges.check(db, eng)  # catches up anything earned before badges existed
    db.commit()
    return {"badges": badges.listing(db, eng)}


@router.post("/{user_id}/badges/{key}/share")
@limiter.limit("20/minute")
def share_badge(request: Request, user_id: str, key: str, db: Session = Depends(get_db),
                _: str = Depends(require_owner)):
    from app.services import badges
    try:
        return {"token": badges.share(db, user_id, key)}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{user_id}/badges/{key}/share")
def unshare_badge(user_id: str, key: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    from app.services import badges
    badges.unshare(db, user_id, key)
    return {"ok": True}


class ReferralPayload(BaseModel):
    code: str = Field(min_length=4, max_length=16)


@router.get("/{user_id}/referrals")
def get_referrals(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    from app.services import referrals
    return referrals.overview(db, user_id)


@router.get("/{user_id}/referrals/preview/{code}")
@limiter.limit("30/minute")
def preview_referral(request: Request, user_id: str, code: str, db: Session = Depends(get_db),
                     _: str = Depends(require_owner)):
    from app.services import referrals
    return referrals.preview(db, user_id, code)


@router.post("/{user_id}/referrals/claim")
@limiter.limit("10/minute")
def claim_referral(request: Request, user_id: str, payload: ReferralPayload, db: Session = Depends(get_db),
                   _: str = Depends(require_owner)):
    from app.services import referrals
    try:
        return referrals.claim(db, user_id, payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class LeaguePayload(BaseModel):
    enabled: bool


@router.get("/{user_id}/league")
def get_league(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    from app.services import leagues
    return leagues.board(db, user_id)


@router.put("/{user_id}/league")
@limiter.limit("10/minute")
def set_league(request: Request, user_id: str, payload: LeaguePayload, db: Session = Depends(get_db),
               _: str = Depends(require_owner)):
    from app.services import leagues
    try:
        return leagues.set_opt_in(db, user_id, payload.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/push/public-key")
def push_public_key():
    from app.services.push_service import push_configured
    from app.config import settings
    return {"key": settings.VAPID_PUBLIC_KEY if push_configured() else None}


@router.post("/{user_id}/push")
@limiter.limit("10/minute")
def add_push(request: Request, user_id: str, payload: PushPayload, db: Session = Depends(get_db),
             _: str = Depends(require_owner)):
    if not payload.endpoint.startswith("https://") or payload.keys is None:
        raise HTTPException(status_code=400, detail="Invalid push subscription.")
    engagement.add_push_subscription(db, user_id, payload.endpoint, payload.keys.p256dh, payload.keys.auth)
    return {"ok": True}


@router.delete("/{user_id}/push")
def remove_push(user_id: str, payload: PushPayload, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    engagement.remove_push_subscription(db, user_id, payload.endpoint)
    return {"ok": True}


@router.post("/unsubscribe")
@limiter.limit("10/minute")
def unsubscribe(request: Request, payload: UnsubscribePayload, db: Session = Depends(get_db)):
    """One-click unsubscribe from an email link: no login needed, the link is signed."""
    if not engagement.verify_unsubscribe_token(payload.u, payload.t):
        raise HTTPException(status_code=400, detail="This unsubscribe link isn't valid.")
    engagement.set_reminders(db, payload.u, False)
    return {"ok": True}
