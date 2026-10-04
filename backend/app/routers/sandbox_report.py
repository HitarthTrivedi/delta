"""Test Center report — the student's combined interview-readiness view."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_owner
from app.services.readiness import compute_readiness

router = APIRouter(prefix="/api/sandbox/report", tags=["sandbox-report"])


@router.get("/{user_id}")
def readiness_report(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return compute_readiness(db, user_id)
