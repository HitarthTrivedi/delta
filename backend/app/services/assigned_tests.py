"""What college tests (BatchTestAssignment) and company tests (CompanyTest)
share: made once, the same stored questions for everyone, one attempt, and an
answer key that stays hidden from students while the test is open."""
from __future__ import annotations

import datetime
import json

from sqlalchemy.orm import Session

from app.models.company import CompanyTest
from app.models.college import BatchTestAssignment
from app.models.sandbox_session import SandboxSession

SECONDS_PER_QUESTION = 60


def is_open(a, today: datetime.date | None = None) -> bool:
    today = today or datetime.date.today()
    return a.closed_at is None and (a.due_date is None or a.due_date >= today)


def attempts(db: Session, assignment_id: str, user_ids: list[str] | None = None) -> dict[str, SandboxSession]:
    """Each student's session for this test (completed wins over in progress)."""
    q = db.query(SandboxSession).filter(SandboxSession.type == "theory",
                                        SandboxSession.data.contains(f'"assignment_id": "{assignment_id}"'))
    if user_ids is not None:
        q = q.filter(SandboxSession.user_id.in_(user_ids or [""]))
    out: dict[str, SandboxSession] = {}
    for s in q.all():
        if json.loads(s.data or "{}").get("assignment_id") != assignment_id:
            continue
        if s.user_id not in out or s.status == "completed":
            out[s.user_id] = s
    return out


def open_attempt(db: Session, assignment_id: str, user_id: str) -> SandboxSession | None:
    s = attempts(db, assignment_id, [user_id]).get(user_id)
    return s if s and s.status != "completed" else None


def find(db: Session, assignment_id: str):
    return db.get(BatchTestAssignment, assignment_id) or db.get(CompanyTest, assignment_id)


def check_attempt(db: Session, a, user_id: str) -> None:
    if not is_open(a):
        raise ValueError("This test has closed.")
    s = attempts(db, a.id, [user_id]).get(user_id)
    if s and s.status == "completed":
        raise ValueError("You've already taken this test.")


def for_student(db: Session, user_id: str, assignment_id: str):
    """A college or company test this student may take now (LookupError / ValueError otherwise)."""
    if db.get(CompanyTest, assignment_id):
        from app.services.company_roadmaps import test_for_student
        return test_for_student(db, user_id, assignment_id)
    from app.services.college_assignments import assignment_for_student
    return assignment_for_student(db, user_id, assignment_id)


def hide_answers(assignment_id: str | None, db: Session) -> bool:
    """While a college or company test is open, students don't see the answer key."""
    a = find(db, assignment_id) if assignment_id else None
    return bool(a and is_open(a))


def summary(db: Session, a, members: int | None = None) -> dict:
    done = [s for s in attempts(db, a.id).values() if s.status == "completed"]
    return {"id": a.id, "title": a.title, "topic": a.topic, "category": a.category, "difficulty": a.difficulty,
            "questions": len(json.loads(a.questions)), "time_limit_seconds": a.time_limit_seconds,
            "due_date": a.due_date.isoformat() if a.due_date else None, "open": is_open(a),
            "created_at": a.created_at.isoformat(), "members": members, "taken": len(done),
            "average": round(sum(s.score or 0 for s in done) / len(done)) if done else None}
