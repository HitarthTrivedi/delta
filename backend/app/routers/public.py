"""Public, read-only pages that need no login (verify links)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.services import badges

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/badges/{token}")
@limiter.limit("30/minute")
def verify_badge(request: Request, token: str, db: Session = Depends(get_db)):
    found = badges.public_view(db, token)
    if not found:
        raise HTTPException(status_code=404, detail="This link isn't valid, or its owner stopped sharing it.")
    return found


class ParentDecision(BaseModel):
    grant: bool
    is_guardian: bool = False


@router.get("/parent-consent/{token}")
@limiter.limit("20/minute")
def parent_consent_view(request: Request, token: str, db: Session = Depends(get_db)):
    from app.services import minors
    try:
        return minors.parent_view(db, token)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/parent-consent/{token}")
@limiter.limit("10/minute")
def parent_consent_respond(request: Request, token: str, payload: ParentDecision, db: Session = Depends(get_db)):
    from app.services import minors
    try:
        return minors.parent_respond(db, token, payload.grant, payload.is_guardian)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
