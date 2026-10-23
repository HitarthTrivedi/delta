"""Mock Interview Sandbox router — AI video interviewer (voice or text answers)."""
import datetime
import json
import logging
import uuid
from xml.sax.saxutils import escape

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.config import settings as config
from app.database import get_db
from app.limiter import limiter
from app.models.sandbox_session import SandboxSession
from app.dependencies.auth import require_owner
from app.services.interview_ai import (
    generate_opening_question, generate_next_question, generate_feedback,
    normalize_settings, FeedbackUnavailable,
)
from app.services.domain_packs import get_domain_pack
from app.services.sandbox_common import bump_skill
from app.services.central_engine import log_journey_event

router = APIRouter(prefix="/api/sandbox/interview", tags=["sandbox-interview"])
logger = logging.getLogger("delta.interview")

GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
MAX_TTS_WORDS = 300

ROLE_TYPE_LABEL = {"technical": "Technical Interview", "behavioral": "Behavioral Interview", "case": "Case / Scenario Interview", "system_design": "System Design Interview"}


def _title(settings: dict) -> str:
    # "Technical" reads oddly for a nurse or a lawyer: call it a role-knowledge round there.
    # Same rule as the prompt and the frontend: the field pack's is_tech flag.
    if settings["role_type"] == "technical" and not get_domain_pack(settings.get("field") or "general")["is_tech"]:
        return "Role Knowledge Interview"
    return ROLE_TYPE_LABEL[settings["role_type"]]


class StartPayload(BaseModel):
    role_type: str = "technical"
    target_role: Optional[str] = Field(default=None, max_length=120)
    difficulty: Optional[str] = None
    num_questions: Optional[int] = None


class RespondPayload(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)


class TtsPayload(BaseModel):
    text: str = Field(min_length=1, max_length=1500)
    voice: Optional[str] = Field(default=None, max_length=60)


def _tts_voices() -> list[str]:
    return [v.strip() for v in (config.INTERVIEW_TTS_VOICES or "").split(",") if v.strip()]


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
    # Settings are fixed when the interview starts. Reuse them as stored, so a
    # profile edit mid-interview can't change the field or question count, and
    # no turn pays for a profile reload. Only sessions created before settings
    # were stored (role_type only) are rebuilt from the profile.
    s = data.get("settings") or {}
    if s.get("num_questions") and s.get("field"):
        return s
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


@router.get("/{user_id}/avatar")
def avatar_config(user_id: str, _: str = Depends(require_owner)):
    """Whether the 3D, lip-synced interviewer is available (needs the TTS key)."""
    voices = _tts_voices()
    return {"tts": bool(config.GOOGLE_TTS_API_KEY and voices), "voice": voices[0] if voices else None}


@router.post("/{user_id}/tts")
@limiter.limit("60/minute")
def interviewer_speech(request: Request, user_id: str, payload: TtsPayload, _: str = Depends(require_owner)):
    """Speak the interviewer's line with Google Cloud TTS, plus per-word start
    times (ms) that drive the 3D avatar's lip-sync.

    Only the interviewer's own text is sent to Google, never the candidate's
    voice or answers. The SSML is built here from plain words, so a client
    can't send arbitrary SSML, and the key stays server-side.
    """
    voices = _tts_voices()
    if not config.GOOGLE_TTS_API_KEY or not voices:
        raise HTTPException(status_code=503, detail="The interviewer's voice isn't configured.")
    voice = payload.voice if payload.voice in voices else voices[0]
    words = payload.text.split()[:MAX_TTS_WORDS]
    if not words:
        raise HTTPException(status_code=400, detail="Nothing to say.")
    # A mark before every word: Google reports when each mark is reached.
    ssml = "<speak>" + " ".join(f'<mark name="{i}"/>{escape(w)}' for i, w in enumerate(words)) + "</speak>"
    body = {
        "input": {"ssml": ssml},
        "voice": {"languageCode": "-".join(voice.split("-")[:2]), "name": voice},
        "audioConfig": {"audioEncoding": "MP3"},
        "enableTimePointing": ["SSML_MARK"],
    }
    try:
        res = requests.post(GOOGLE_TTS_URL, json=body, timeout=15,
                            headers={"X-Goog-Api-Key": config.GOOGLE_TTS_API_KEY})
    except requests.RequestException as exc:
        logger.warning("tts: request to Google failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="The interviewer's voice is unavailable right now.") from exc
    if res.status_code != 200:
        logger.warning("tts: Google returned %s: %s", res.status_code, res.text[:200])
        raise HTTPException(status_code=502, detail="The interviewer's voice is unavailable right now.")
    data = res.json()
    marks = {tp.get("markName"): float(tp.get("timeSeconds") or 0) for tp in data.get("timepoints") or []}
    wtimes, last = [], 0
    for i in range(len(words)):
        # Google occasionally skips a mark; reuse the previous time so order holds.
        last = round(marks[str(i)] * 1000) if str(i) in marks else last
        wtimes.append(last)
    return {"audio": data.get("audioContent") or "", "words": words, "wtimes": wtimes, "voice": voice}


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
        "role_type_label": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }
