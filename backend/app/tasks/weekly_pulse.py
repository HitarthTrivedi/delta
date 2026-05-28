"""Weekly market pulse and memory consolidation task."""

from app.database import SessionLocal
from app.models import User
from app.services.central_engine import run_weekly_career_cycle


def update_market_pulse():
    """Refresh market data and memory state for all users."""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        results = []
        for user in users:
            try:
                context = run_weekly_career_cycle(db, user.id)
                results.append({
                    "user_id": user.id,
                    "status": "completed",
                    "merged_nodes": context.get("memory_consolidation", {}).get("merged_nodes", 0),
                })
            except Exception as exc:
                results.append({"user_id": user.id, "status": "failed", "error": str(exc)})
        return {"users_processed": len(users), "results": results}
    finally:
        db.close()
