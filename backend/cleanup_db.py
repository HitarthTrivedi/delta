import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
import json

from app.models import JourneyEvent

db = SessionLocal()
try:
    user_id = "00000000-0000-0000-0000-000000000000"
    cycle_events = db.query(JourneyEvent).filter(
        JourneyEvent.user_id == user_id,
        JourneyEvent.event_type == "weekly_cycle_completed"
    ).all()
    deleted_count = 0
    for event in cycle_events:
        try:
            impact = json.loads(event.impact or "{}")
            evidence = json.loads(event.evidence or "{}")
        except Exception:
            impact = {}
            evidence = {}
        if impact.get("advance_approved") is True or evidence.get("completed_task_count"):
            continue
        db.delete(event)
        deleted_count += 1
    db.commit()
    print(f"Successfully deleted {deleted_count} stale refresh-created weekly cycle events for user {user_id}.")
except Exception as e:
    db.rollback()
    print("Error cleaning up database:", e)
finally:
    db.close()
