"""Mock Interview Sandbox router — AI video interviewer (voice or text answers)."""
import datetime
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.limiter import limiter
from app.models.sandbox_session import SandboxSession
from app.dependencies.auth import require_owner
from app.services.interview_ai import (
    generate_opening_question, generate_next_question, generate_feedback,
    normalize_settings, FeedbackUnavailable, ROLE_TYPE_LABELS,
)
from app.services.sandbox_common import bump_skill
from app.services.central_engine import log_journey_event

router = APIRouter(prefix="/api/sandbox/interview", tags=["sandbox-interview"])

ROLE_TYPE_LABEL = {"technical": "Technical Interview", "behavioral": "Behavioral Interview", "case": "Case / Scenario Interview", "system_design": "System Design Interview"}


def _title(settings: dict) -> str:
    # "Technical" reads oddly for a nurse or a lawyer: call it a role-knowledge round there.
    if settings["role_type"] == "technical" and settings.get("field") not in ("cs_ai", "data", "core_engineering"):
        return "Role Knowledge Interview"
    return ROLE_TYPE_LABEL[settings["role_type"]]


class StartPayload(BaseModel):
    role_type: str = "technical"
    target_role: Optional[str] = Field(default=None, max_length=120)
    difficulty: Optional[str] = None
    num_questions: Optional[int] = None


class RespondPayload(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)


def _session_or_404(db: Session, user_id: str, session_id: str) -> SandboxSession:
    session = db.query(SandboxSession).filter(
        SandboxSession.id == session_id,
        SandboxSession.user_id == user_id,
        SandboxSession.type == "interview",
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return session


def _settings(data: dict, user_id: str) -> dict:
    # Sessions created before settings existed only stored role_type.
    s = data.get("settings") or {}
    return normalize_settings(s.get("role_type") or data.get("role_type", "technical"), s.get("target_role"),
                              s.get("difficulty"), s.get("num_questions"), user_id)


@router.post("/{user_id}/start")
@limiter.limit("10/minute")
def start_interview(
    request: Request,
    user_id: str,
    payload: StartPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    settings = normalize_settings(payload.role_type, payload.target_role, payload.difficulty, payload.num_questions, user_id)
    question = generate_opening_question(user_id, settings)

    session = SandboxSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type="interview",
        title=_title(settings),
        status="in_progress",
        data=json.dumps({
            "role_type": settings["role_type"],
            "settings": settings,
            "transcript": [{"role": "interviewer", "content": question}],
        }),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id, "role_type": settings["role_type"], "settings": settings,
        "question": question, "question_number": 1, "total_questions": settings["num_questions"],
    }


@router.post("/{user_id}/sessions/{session_id}/respond")
@limiter.limit("20/minute")
def respond(
    request: Request,
    user_id: str,
    session_id: str,
    payload: RespondPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    session = _session_or_404(db, user_id, session_id)
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="This interview has already finished.")

    data = json.loads(session.data or "{}")
    settings = _settings(data, user_id)
    transcript = data.get("transcript") or []
    transcript.append({"role": "candidate", "content": payload.answer.strip()})

    question_count = sum(1 for t in transcript if t["role"] == "interviewer")
    result = generate_next_question(user_id, settings, transcript, question_count)

    if not result["done"] and result["question"]:
        transcript.append({"role": "interviewer", "content": result["question"]})

    data["transcript"] = transcript
    session.data = json.dumps(data)
    db.commit()

    return {
        "question": result["question"],
        "done": result["done"],
        "question_number": question_count + (0 if result["done"] else 1),
        "total_questions": settings["num_questions"],
    }


@router.post("/{user_id}/sessions/{session_id}/finish")
@limiter.limit("10/minute")
def finish_interview(
    request: Request,
    user_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    session = _session_or_404(db, user_id, session_id)
    data = json.loads(session.data or "{}")

    if session.status == "completed":
        return {"session_id": session.id, "feedback": data.get("feedback") or {}, "settings": data.get("settings"),
                "transcript": data.get("transcript") or []}

    transcript = data.get("transcript") or []
    if not any(t["role"] == "candidate" for t in transcript):
        raise HTTPException(status_code=400, detail="Answer at least one question before finishing.")
    settings = _settings(data, user_id)
    try:
        feedback = generate_feedback(user_id, settings, transcript)
    except FeedbackUnavailable:
        # Keep the session open so the candidate can retry; never invent a score.
        raise HTTPException(status_code=503, detail="Couldn't generate your report right now. Please try again.")

    session.status = "completed"
    session.score = feedback["overall_score"]
    session.completed_at = datetime.datetime.utcnow()
    data["settings"] = settings
    data["feedback"] = feedback
    session.data = json.dumps(data)
    db.commit()

    skill_name = "Interview readiness"
    bump_skill(db, user_id, skill_name, amount=1)
    db.commit()

    log_journey_event(
        db=db,
        user_id=user_id,
        event_type="task_completed",
        summary=f"Completed a mock interview: {session.title} — scored {feedback['overall_score']}/100",
        evidence={"skill": skill_name, "sandbox_type": "interview", "role_type": settings["role_type"]},
        impact={"sandbox_session_id": session.id, "score": feedback["overall_score"]},
    )

    return {"session_id": session.id, "feedback": feedback, "settings": settings, "transcript": transcript}


@router.get("/{user_id}/sessions")
def list_sessions(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    rows = db.query(SandboxSession).filter(
        SandboxSession.user_id == user_id,
        SandboxSession.type == "interview",
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
        "settings": _settings(data, user_id), "transcript": data.get("transcript") or [],
        "feedback": data.get("feedback"),
        "role_type_label": ROLE_TYPE_LABELS.get(data.get("role_type", "technical")),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }
