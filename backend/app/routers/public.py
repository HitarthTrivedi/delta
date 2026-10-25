"""Public, read-only pages that need no login (verify links)."""
from fastapi import APIRouter, Depends, HTTPException, Request
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
