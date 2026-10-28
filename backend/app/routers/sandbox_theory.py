"""Technical Theory Test router — AI-generated MCQ test, graded server-side."""
import datetime
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.services import compliance, integrity
from app.services.integrity import IntegrityPayload
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.limiter import limiter
from app.models.sandbox_session import SandboxSession
from app.models.skill_node import SkillNode
from app.dependencies.auth import require_owner
from app.services.theory_test_ai import generate_test, MIN_QUESTIONS, MAX_QUESTIONS, DIFFICULTIES, APTITUDE_AREAS
from app.services.profile_store import load_profile
from app.services.sandbox_common import bump_skill
from app.services.central_engine import log_journey_event

router = APIRouter(prefix="/api/sandbox/theory", tags=["sandbox-theory"])

SKILL_PASS_RATIO = 0.7  # per-skill accuracy needed to bump that skill
SECONDS_PER_QUESTION = 60
GRACE_SECONDS = 15  # network/render slack before a timed attempt counts as overtime


class StartPayload(BaseModel):
    topic: Optional[str] = None
    num_questions: int = 10
    difficulty: str = "medium"
    category: str = "technical"  # technical | aptitude
    area: Optional[str] = None  # aptitude: quantitative | logical | verbal
    timed: bool = False
    assignment_id: Optional[str] = None  # a test the learner's college set (questions already made)


class SubmitPayload(BaseModel):
    answers: list[Optional[int]]
    integrity: Optional[IntegrityPayload] = None


def _session_or_404(db: Session, user_id: str, session_id: str) -> SandboxSession:
    session = db.query(SandboxSession).filter(
        SandboxSession.id == session_id,
        SandboxSession.user_id == user_id,
        SandboxSession.type == "theory",
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Test session not found.")
    return session


def _public_questions(questions: list[dict]) -> list[dict]:
    """Strip the answer key before sending questions to the client."""
    return [{"question": q["question"], "options": q["options"], "skill": q["skill"]} for q in questions]


def _public_result(db: Session, data: dict, result: dict) -> dict:
    """A college test that is still open never shows its answer key."""
    from app.services.assigned_tests import hide_answers
    if hide_answers(data.get("assignment_id"), db):
        return {**result, "questions": [], "answers_hidden": True}
    return result


def _start_assigned(db: Session, user_id: str, assignment_id: str) -> dict:
    from app.services import assigned_tests
    try:
        a = assigned_tests.for_student(db, user_id, assignment_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session = assigned_tests.open_attempt(db, a.id, user_id)
    if not session:  # the same stored questions for everyone it was set for: no model call
        started_at = datetime.datetime.utcnow()
        session = SandboxSession(
            id=str(uuid.uuid4()), user_id=user_id, type="theory", title=a.title[:200], status="in_progress",
            data=json.dumps({"topic": a.topic, "category": a.category, "difficulty": a.difficulty,
                             "questions": json.loads(a.questions), "time_limit_seconds": a.time_limit_seconds,
                             "started_at": started_at.isoformat(), "assignment_id": a.id}),
            created_at=started_at)
        db.add(session)
        db.commit()
    data = json.loads(session.data)
    return {"session_id": session.id, "topic": data["topic"], "category": data["category"],
            "difficulty": data["difficulty"], "time_limit_seconds": data["time_limit_seconds"],
            "questions": _public_questions(data["questions"]), "assignment_id": a.id}


@router.post("/{user_id}/start")
@limiter.limit("10/minute")
def start_test(
    request: Request,
    user_id: str,
    payload: StartPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    if payload.assignment_id:
        return _start_assigned(db, user_id, payload.assignment_id)
    num_questions = max(MIN_QUESTIONS, min(MAX_QUESTIONS, payload.num_questions))
    category = "aptitude" if payload.category == "aptitude" else "technical"
    difficulty = payload.difficulty if payload.difficulty in DIFFICULTIES else "medium"
    area = payload.area if payload.area in APTITUDE_AREAS else None
    from app.models.user import User
    minor = compliance.is_minor(db.get(User, user_id))
    if minor and category == "technical" and not (payload.topic or "").strip():
        raise HTTPException(status_code=400, detail="Pick a topic for your test.")
    try:
        if minor:  # never send an under-18 learner's profile to the model
            topic, questions = generate_test(None, payload.topic, num_questions, difficulty, category, area,
                                             personalize=False)
        else:
            topic, questions = generate_test(user_id, payload.topic, num_questions, difficulty, category, area)
    except ValueError:
        raise HTTPException(status_code=503, detail="Could not generate a test right now. Try again in a moment.")

    time_limit = len(questions) * SECONDS_PER_QUESTION if payload.timed else None
    started_at = datetime.datetime.utcnow()
    label = "Aptitude Test" if category == "aptitude" else "Theory Test"
    session = SandboxSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type="theory",
        title=f"{label}: {topic}"[:200],
        status="in_progress",
        data=json.dumps({
            "topic": topic, "category": category, "difficulty": difficulty, "questions": questions,
            "time_limit_seconds": time_limit, "started_at": started_at.isoformat(),
        }),
        created_at=started_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id, "topic": topic, "category": category, "difficulty": difficulty,
        "time_limit_seconds": time_limit, "questions": _public_questions(questions),
    }


@router.post("/{user_id}/sessions/{session_id}/submit")
@limiter.limit("10/minute")
def submit_test(
    request: Request,
    user_id: str,
    session_id: str,
    payload: SubmitPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    session = _session_or_404(db, user_id, session_id)
    data = json.loads(session.data or "{}")

    if session.status == "completed":
        return {"session_id": session.id, "result": _public_result(db, data, data.get("result") or {})}

    questions = data.get("questions") or []
    if len(payload.answers) != len(questions):
        raise HTTPException(status_code=400, detail=f"Expected {len(questions)} answers.")

    per_question = []
    skill_breakdown: dict[str, dict] = {}
    correct_total = 0
    for q, chosen in zip(questions, payload.answers):
        is_correct = chosen == q["answer_index"]
        correct_total += is_correct
        stats = skill_breakdown.setdefault(q["skill"], {"correct": 0, "total": 0})
        stats["total"] += 1
        stats["correct"] += is_correct
        per_question.append({
            "question": q["question"],
            "options": q["options"],
            "skill": q["skill"],
            "chosen_index": chosen,
            "answer_index": q["answer_index"],
            "correct": is_correct,
            "explanation": q["explanation"],
        })

    score = round(100 * correct_total / len(questions)) if questions else 0
    try:
        time_taken = int((datetime.datetime.utcnow() - datetime.datetime.fromisoformat(data["started_at"])).total_seconds())
    except (KeyError, ValueError, TypeError):
        time_taken = None
    limit = data.get("time_limit_seconds")
    result = {
        "score": score,
        "correct": correct_total,
        "total": len(questions),
        "skill_breakdown": skill_breakdown,
        "questions": per_question,
        "difficulty": data.get("difficulty", "medium"),
        "category": data.get("category", "technical"),
        "time_taken_seconds": time_taken,
        "time_limit_seconds": limit,
        "overtime": bool(limit and time_taken is not None and time_taken > limit + GRACE_SECONDS),
    }

    session.status = "completed"
    session.score = score
    session.completed_at = datetime.datetime.utcnow()
    data["answers"] = payload.answers
    data["result"] = result
    integrity.record(data, payload.integrity)
    session.data = json.dumps(data)
    db.commit()
    result["integrity"] = integrity.notes(session)

    for skill_name, stats in skill_breakdown.items():
        if stats["correct"] / stats["total"] >= SKILL_PASS_RATIO:
            bump_skill(db, user_id, skill_name, amount=1)
    db.commit()

    log_journey_event(
        db=db,
        user_id=user_id,
        event_type="task_completed",
        summary=f"Completed a theory test: {data.get('topic')} — scored {score}/100",
        evidence={"skill": data.get("topic"), "sandbox_type": "theory", "skill_breakdown": skill_breakdown},
        impact={"sandbox_session_id": session.id, "score": score},
    )

    return {"session_id": session.id, "result": _public_result(db, data, result)}


@router.get("/{user_id}/sessions")
def list_sessions(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    rows = db.query(SandboxSession).filter(
        SandboxSession.user_id == user_id,
        SandboxSession.type == "theory",
    ).order_by(SandboxSession.created_at.desc()).limit(50).all()
    return {
        "sessions": [
            {
                "id": r.id, "title": r.title, "status": r.status, "score": r.score,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in rows
        ]
    }


@router.get("/{user_id}/sessions/{session_id}")
def get_session(user_id: str, session_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    session = _session_or_404(db, user_id, session_id)
    data = json.loads(session.data or "{}")
    return {
        "session_id": session.id, "title": session.title, "status": session.status, "score": session.score,
        "topic": data.get("topic"), "category": data.get("category", "technical"),
        "difficulty": data.get("difficulty", "medium"),
        # Answer key only once the test is submitted.
        "result": _public_result(db, data, data["result"]) if session.status == "completed" and data.get("result") else None,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


@router.get("/{user_id}/suggestions")
def suggestions(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Topic chips: the student's weakest skills first, then skills on their
    current roadmap phase, then their target role."""
    from app.models.career_os import RoadmapState

    seen: set[str] = set()
    topics: list[dict] = []

    def add(name, reason):
        name = (name or "").strip()
        if name and name.lower() not in seen and name.lower() not in {"exploring", "interview readiness"}:
            seen.add(name.lower())
            topics.append({"topic": name, "reason": reason})

    for sk in db.query(SkillNode).filter(SkillNode.user_id == user_id).order_by(SkillNode.proficiency.asc()).limit(6).all():
        add(sk.name, "weak spot" if (sk.proficiency or 0) <= 3 else "your skill")
    roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == user_id).first()
    if roadmap and roadmap.phases:
        try:
            phases = json.loads(roadmap.phases) or []
            active = next((p for p in phases if p.get("id") == roadmap.active_phase_id), phases[0] if phases else {})
            for node in active.get("nodes") or []:
                add(node.get("skill_name") or node.get("label"), "on your roadmap")
        except (ValueError, AttributeError, TypeError):
            pass
    profile = load_profile(user_id, db=db) or {}
    add(profile.get("target_role"), "your target role")
    return {"topics": topics[:10]}
