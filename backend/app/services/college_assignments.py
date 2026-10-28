"""Delta for College P4: roadmaps and tests a college sets for a batch.

- A batch roadmap applies to every active member (now and when they join) and
  can't be stopped while they're in that batch. Leaving, removal or the
  college unsetting it makes it the student's own choice again.
- A batch test is generated once with no learner data in the prompt, stored
  with its answer key, and every member takes the same questions. The key and
  per-question review stay hidden from students until the test closes.
"""
from __future__ import annotations

import datetime
import json
import uuid

from sqlalchemy.orm import Session

from app.models.college import Batch, BatchTestAssignment, CollegeMember, RosterEntry
from app.models.roadmap_template import RoadmapEnrollment
from app.models.user import User
from app.services import integrity, roadmap_templates
from app.services.assigned_tests import SECONDS_PER_QUESTION, attempts as _attempts, check_attempt, is_open, summary
from app.services.roadmap_catalog import TEMPLATES
from app.services.theory_test_ai import APTITUDE_AREAS, DIFFICULTIES, MAX_QUESTIONS, MIN_QUESTIONS, generate_test


def _batch(db: Session, college_id: str, batch_id: str) -> Batch:
    b = db.query(Batch).filter(Batch.id == batch_id, Batch.college_id == college_id).first()
    if not b:
        raise LookupError("Batch not found.")
    return b


def _active_members(db: Session, batch_id: str) -> list[CollegeMember]:
    return db.query(CollegeMember).filter(CollegeMember.batch_id == batch_id, CollegeMember.status == "active").all()


# ── batch roadmap ────────────────────────────────────────────────────────────

def batch_template(db: Session, b: Batch) -> dict | None:
    if not b.template_id or b.template_id not in TEMPLATES:
        return None
    t = TEMPLATES[b.template_id]
    following = db.query(RoadmapEnrollment).filter(RoadmapEnrollment.assigned_by_batch_id == b.id,
                                                   RoadmapEnrollment.status == "active").count()
    return {"template_id": t["id"], "title": t["title"], "weeks": t["weeks"],
            "target_date": b.template_target_date.isoformat() if b.template_target_date else None,
            "following": following}


def _release(db: Session, batch_id: str, user_id: str | None = None) -> None:
    """The roadmap stays, but becomes the student's own choice."""
    q = db.query(RoadmapEnrollment).filter(RoadmapEnrollment.assigned_by_batch_id == batch_id)
    if user_id:
        q = q.filter(RoadmapEnrollment.user_id == user_id)
    for e in q.all():
        e.assigned_by_batch_id = None
    db.commit()


def set_batch_template(db: Session, college_id: str, batch_id: str, template_id: str | None,
                       target_date: datetime.date | None = None) -> dict | None:
    b = _batch(db, college_id, batch_id)
    if template_id and template_id not in TEMPLATES:
        raise LookupError("Unknown roadmap.")
    if template_id and target_date and target_date <= datetime.date.today() + datetime.timedelta(days=13):
        raise ValueError("Pick a target date at least two weeks away.")
    if not template_id:
        b.template_id = b.template_target_date = None
        db.commit()
        _release(db, b.id)
        return None
    b.template_id, b.template_target_date = template_id, target_date
    db.commit()
    for m in _active_members(db, b.id):
        roadmap_templates.start(db, m.user_id, template_id, target_date, assigned_by_batch_id=b.id)
    return batch_template(db, b)


def on_member_active(db: Session, m: CollegeMember) -> None:
    """A student became an active member: apply the batch roadmap, if any."""
    b = db.get(Batch, m.batch_id) if m.batch_id else None
    if b and b.template_id in TEMPLATES and m.status == "active":
        target = b.template_target_date
        if target and target <= datetime.date.today() + datetime.timedelta(days=13):
            target = None  # too close to squeeze a plan into; follow it at its own pace
        roadmap_templates.start(db, m.user_id, b.template_id, target, assigned_by_batch_id=b.id)


def on_member_left(db: Session, m: CollegeMember) -> None:
    if m.batch_id:
        _release(db, m.batch_id, m.user_id)


# ── batch tests ──────────────────────────────────────────────────────────────

def _test_dict(db: Session, a: BatchTestAssignment, members: int | None = None) -> dict:
    return {**summary(db, a, members), "batch_id": a.batch_id}


def create_test(db: Session, college_id: str, batch_id: str, *, topic: str | None, category: str = "technical",
                area: str | None = None, difficulty: str = "medium", num_questions: int = 10, timed: bool = True,
                due_date: datetime.date | None = None, title: str | None = None, by: str | None = None) -> dict:
    _batch(db, college_id, batch_id)
    category = "aptitude" if category == "aptitude" else "technical"
    if category == "technical" and not (topic or "").strip():
        raise ValueError("Pick a topic for the test.")
    if due_date and due_date < datetime.date.today():
        raise ValueError("The due date is in the past.")
    num_questions = max(MIN_QUESTIONS, min(MAX_QUESTIONS, num_questions))
    difficulty = difficulty if difficulty in DIFFICULTIES else "medium"
    area = area if area in APTITUDE_AREAS else None
    # One model call for the whole batch; no student's data goes into the prompt.
    try:
        topic, questions = generate_test(None, (topic or "").strip() or None, num_questions, difficulty, category,
                                         area, personalize=False)
    except ValueError as exc:  # unusable model output: never store placeholder questions
        raise RuntimeError("Could not make the test right now. Try again in a moment.") from exc
    a = BatchTestAssignment(
        id=str(uuid.uuid4()), college_id=college_id, batch_id=batch_id, topic=topic, category=category,
        difficulty=difficulty, questions=json.dumps(questions),
        title=" ".join((title or "").split())[:120] or f"{'Aptitude' if category == 'aptitude' else 'Test'}: {topic}"[:120],
        time_limit_seconds=len(questions) * SECONDS_PER_QUESTION if timed else None, due_date=due_date, created_by=by)
    db.add(a)
    db.commit()
    return _test_dict(db, a, len(_active_members(db, batch_id)))


def list_tests(db: Session, college_id: str, batch_id: str) -> list[dict]:
    _batch(db, college_id, batch_id)
    members = len(_active_members(db, batch_id))
    rows = (db.query(BatchTestAssignment).filter(BatchTestAssignment.batch_id == batch_id)
            .order_by(BatchTestAssignment.created_at.desc()).all())
    return [_test_dict(db, a, members) for a in rows]


def _assignment(db: Session, college_id: str, assignment_id: str) -> BatchTestAssignment:
    a = db.query(BatchTestAssignment).filter(BatchTestAssignment.id == assignment_id,
                                             BatchTestAssignment.college_id == college_id).first()
    if not a:
        raise LookupError("Test not found.")
    return a


def close_test(db: Session, college_id: str, assignment_id: str) -> dict:
    a = _assignment(db, college_id, assignment_id)
    a.closed_at = a.closed_at or datetime.datetime.utcnow()
    db.commit()
    return _test_dict(db, a, len(_active_members(db, a.batch_id)))


def results(db: Session, college_id: str, assignment_id: str) -> dict:
    """Every active member of the batch with their attempt, score and integrity notes."""
    a = _assignment(db, college_id, assignment_id)
    members = _active_members(db, a.batch_id)
    ids = [m.user_id for m in members]
    attempts = _attempts(db, a.id, ids)
    entries = {e.id: e for e in db.query(RosterEntry).filter(
        RosterEntry.id.in_([m.roster_entry_id for m in members if m.roster_entry_id] or [""]))}
    names = {u.id: u.name for u in db.query(User.id, User.name).filter(User.id.in_(ids or [""]))}
    rows = []
    for m in members:
        e, s = entries.get(m.roster_entry_id), attempts.get(m.user_id)
        notes = integrity.notes(s) if s and s.status == "completed" else None
        rows.append({"user_id": m.user_id, "name": (e.name if e else None) or names.get(m.user_id) or "Student",
                     "roll_no": e.roll_no if e else None,
                     "status": "done" if s and s.status == "completed" else ("started" if s else "not started"),
                     "score": s.score if s and s.status == "completed" else None,
                     "completed_at": s.completed_at.isoformat() if s and s.completed_at else None,
                     "notes": notes["flags"] if notes else []})
    rows.sort(key=lambda r: (r["status"] != "done", -(r["score"] or 0), r["name"].lower()))
    return {"test": _test_dict(db, a, len(members)), "students": rows}


# ── the student side ─────────────────────────────────────────────────────────

def _membership(db: Session, user_id: str) -> CollegeMember | None:
    return db.query(CollegeMember).filter(CollegeMember.user_id == user_id, CollegeMember.status == "active").first()


def student_tests(db: Session, user_id: str) -> list[dict]:
    m = _membership(db, user_id)
    if not m or not m.batch_id:
        return []
    rows = (db.query(BatchTestAssignment).filter(BatchTestAssignment.batch_id == m.batch_id)
            .order_by(BatchTestAssignment.created_at.desc()).limit(20).all())
    out = []
    for a in rows:
        s = _attempts(db, a.id, [user_id]).get(user_id)
        out.append({"id": a.id, "title": a.title, "topic": a.topic, "questions": len(json.loads(a.questions)),
                    "timed": bool(a.time_limit_seconds), "due_date": a.due_date.isoformat() if a.due_date else None,
                    "open": is_open(a),
                    "status": "done" if s and s.status == "completed" else ("started" if s else "not started"),
                    "score": s.score if s and s.status == "completed" else None, "session_id": s.id if s else None})
    return out


def assignment_for_student(db: Session, user_id: str, assignment_id: str) -> BatchTestAssignment:
    """The test, if this student may take it now."""
    a = db.get(BatchTestAssignment, assignment_id)
    m = _membership(db, user_id)
    if not a or not m or m.batch_id != a.batch_id:
        raise LookupError("Test not found.")
    check_attempt(db, a, user_id)
    return a


def weekly_college_actions(db: Session, user_id: str) -> list[dict]:
    """Open tests from the student's college that they haven't finished: the
    weekly plan puts these right after job tasks."""
    out = []
    for t in student_tests(db, user_id):
        if t["open"] and t["status"] != "done":
            due = f" by {datetime.date.fromisoformat(t['due_date']).strftime('%d %b')}" if t["due_date"] else ""
            out.append({
                "id": f"college-test-{t['id'][:8]}", "type": "practice", "title": f"Take your college test: {t['title']}"[:120],
                "skill": t["topic"], "description": f"{t['questions']} questions set by your college{due}.",
                "detail": f"{t['questions']} questions set by your college{due}.",
                "url": f"/practice/theory?assignment={t['id']}", "resource_url": "", "source": "Your college",
                "why_now": f"Your college set this test{due}.", "difficulty_level": "Intermediate",
            })
    return out
