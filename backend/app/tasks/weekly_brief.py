"""Weekly brief generation task."""

from fastapi import HTTPException

from app.database import SessionLocal
from app.models import User
from app.routers.briefs import generate_brief


def generate_all_briefs():
    """Generate weekly briefs for all users. Called by scheduler."""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        results = []
        for user in users:
            try:
                brief = generate_brief(user.id, db)
                results.append({
                    "user_id": user.id,
                    "status": "completed",
                    "brief_id": brief.id,
                    "week_start": brief.week_start.isoformat() if brief.week_start else None,
                })
            except HTTPException as exc:
                results.append({"user_id": user.id, "status": "failed", "error": exc.detail})
            except Exception as exc:
                db.rollback()
                results.append({"user_id": user.id, "status": "failed", "error": str(exc)})
        return {"users_processed": len(users), "results": results}
    finally:
        db.close()
