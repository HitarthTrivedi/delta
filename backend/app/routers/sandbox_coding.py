"""Coding Sandbox router — pick a problem, write code, run it, submit for grading."""
import datetime
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.limiter import limiter
from app.models.sandbox_session import SandboxSession
from app.dependencies.auth import require_owner
from app.services.code_runner import run_code, outputs_match, LANGUAGES
from app.services.sandbox_problems import list_topics, find_problem, generate_problem_package
from app.services.sandbox_common import bump_skill
from app.services.central_engine import log_journey_event

router = APIRouter(prefix="/api/sandbox/coding", tags=["sandbox-coding"])


class StartProblemPayload(BaseModel):
    topic: str
    problem_id: int


class RunPayload(BaseModel):
    language: str
    code: str
    stdin: Optional[str] = ""


class SubmitPayload(BaseModel):
    language: str
    code: str


def _session_or_404(db: Session, user_id: str, session_id: str) -> SandboxSession:
    session = db.query(SandboxSession).filter(
        SandboxSession.id == session_id,
        SandboxSession.user_id == user_id,
        SandboxSession.type == "coding",
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sandbox session not found.")
    return session


@router.get("/{user_id}/problems")
def get_problems(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Curated problem list grouped by topic, flagged with prior completion."""
    topics = list_topics()
    completed_titles = {
        row[0] for row in db.query(SandboxSession.title).filter(
            SandboxSession.user_id == user_id,
            SandboxSession.type == "coding",
            SandboxSession.status == "completed",
        ).all()
    }
    for topic in topics:
        for problem in topic["problems"]:
            problem["completed"] = problem["title"] in completed_titles
    return {"topics": topics, "languages": list(LANGUAGES.keys())}


@router.post("/{user_id}/problems/start")
def start_problem(
    user_id: str,
    payload: StartProblemPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    """Generate (or load a cached) problem package and open a session for it."""
    problem = find_problem(payload.topic, payload.problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found.")

    package = generate_problem_package(payload.topic, problem["title"], problem["difficulty"])

    session = SandboxSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type="coding",
        title=problem["title"],
        status="in_progress",
        data=json.dumps({
            "topic": payload.topic,
            "difficulty": problem["difficulty"],
            "statement": package.get("statement", ""),
            "examples": package.get("examples", []),
            "starter_code": package.get("starter_code", {}),
            "test_cases": package.get("test_cases", []),  # hidden from the response below
        }),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    data = json.loads(session.data)
    return {
        "session_id": session.id,
        "title": session.title,
        "topic": data["topic"],
        "difficulty": data["difficulty"],
        "statement": data["statement"],
        "examples": data["examples"],
        "starter_code": data["starter_code"],
    }


@router.post("/{user_id}/sessions/{session_id}/run")
@limiter.limit("10/minute")
def run_session_code(
    request: Request,
    user_id: str,
    session_id: str,
    payload: RunPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    """Manual "Run" — executes against user-supplied stdin, no grading."""
    _session_or_404(db, user_id, session_id)
    result = run_code(payload.language, payload.code, payload.stdin or "")
    return result


@router.post("/{user_id}/sessions/{session_id}/submit")
@limiter.limit("10/minute")
def submit_session_code(
    request: Request,
    user_id: str,
    session_id: str,
    payload: SubmitPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    """Grades the submission against every stored test case."""
    session = _session_or_404(db, user_id, session_id)
    data = json.loads(session.data or "{}")
    test_cases = data.get("test_cases") or []
    if not test_cases:
        raise HTTPException(status_code=400, detail="This problem has no test cases to grade against.")

    results = []
    for i, case in enumerate(test_cases):
        run = run_code(payload.language, payload.code, case.get("input", ""))
        if run.get("error"):
            return {"error": run["error"], "passed": 0, "total": len(test_cases), "results": []}
        passed = outputs_match(run.get("stdout", ""), case.get("expected_output", ""))
        results.append({
            "index": i,
            "passed": passed,
            "input": case.get("input", ""),
            "expected_output": case.get("expected_output", ""),
            "actual_output": run.get("stdout", ""),
            "stderr": run.get("stderr", ""),
        })

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)
    all_passed = passed_count == total

    if all_passed and session.status != "completed":
        session.status = "completed"
        session.score = 100
        session.completed_at = datetime.datetime.utcnow()
        db.commit()

        skill_name = "DSA interview consistency"
        bump_skill(db, user_id, skill_name, amount=1)
        db.commit()

        log_journey_event(
            db=db,
            user_id=user_id,
            event_type="task_completed",
            summary=f"Completed a coding sandbox exercise: {session.title} ({data.get('difficulty', 'Medium')})",
            evidence={"skill": skill_name, "sandbox_type": "coding", "topic": data.get("topic"), "language": payload.language},
            impact={"sandbox_session_id": session.id, "tests_passed": f"{passed_count}/{total}"},
        )

    return {"passed": passed_count, "total": total, "all_passed": all_passed, "results": results}


@router.get("/{user_id}/sessions")
def list_sessions(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    rows = db.query(SandboxSession).filter(
        SandboxSession.user_id == user_id,
        SandboxSession.type == "coding",
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
