"""Mock Interview Sandbox router — voice-or-text Q&A with an AI interviewer."""
import datetime
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models.sandbox_session import SandboxSession
from app.dependencies.auth import require_owner
from app.services.interview_ai import generate_opening_question, generate_next_question, generate_feedback
from app.services.sandbox_common import bump_skill
from app.services.central_engine import log_journey_event

router = APIRouter(prefix="/api/sandbox/interview", tags=["sandbox-interview"])

ROLE_TYPES = {"technical", "behavioral", "system_design"}
ROLE_TYPE_LABEL = {"technical": "Technical Interview", "behavioral": "Behavioral Interview", "system_design": "System Design Interview"}


class StartPayload(BaseModel):
    role_type: str = "technical"


class RespondPayload(BaseModel):
    answer: str


def _session_or_404(db: Session, user_id: str, session_id: str) -> SandboxSession:
    session = db.query(SandboxSession).filter(
        SandboxSession.id == session_id,
        SandboxSession.user_id == user_id,
        SandboxSession.type == "interview",
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return session


@router.post("/{user_id}/start")
@limiter.limit("10/minute")
def start_interview(
    request: Request,
    user_id: str,
    payload: StartPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    role_type = payload.role_type if payload.role_type in ROLE_TYPES else "technical"
    question = generate_opening_question(user_id, role_type)

    session = SandboxSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type="interview",
        title=ROLE_TYPE_LABEL[role_type],
        status="in_progress",
        data=json.dumps({
            "role_type": role_type,
            "transcript": [{"role": "interviewer", "content": question}],
        }),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {"session_id": session.id, "role_type": role_type, "question": question, "question_number": 1}


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
    transcript = data.get("transcript") or []
    transcript.append({"role": "candidate", "content": payload.answer})

    question_count = sum(1 for t in transcript if t["role"] == "interviewer")
    result = generate_next_question(user_id, data.get("role_type", "technical"), transcript, question_count)

    if not result["done"] and result["question"]:
        transcript.append({"role": "interviewer", "content": result["question"]})

    data["transcript"] = transcript
    session.data = json.dumps(data)
    db.commit()

    return {
        "question": result["question"],
        "done": result["done"],
        "question_number": question_count + (0 if result["done"] else 1),
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
        return {"session_id": session.id, "feedback": data.get("feedback") or {}}

    transcript = data.get("transcript") or []
    role_type = data.get("role_type", "technical")
    feedback = generate_feedback(user_id, role_type, transcript)

    session.status = "completed"
    session.score = feedback["overall_score"]
    session.completed_at = datetime.datetime.utcnow()
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
        evidence={"skill": skill_name, "sandbox_type": "interview", "role_type": role_type},
        impact={"sandbox_session_id": session.id, "score": feedback["overall_score"]},
    )

    return {"session_id": session.id, "feedback": feedback}


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
