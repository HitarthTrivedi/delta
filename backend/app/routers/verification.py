"""Verified readiness re-check: the student's side, and recruiters asking for one."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_owner
from app.limiter import limiter
from app.models.compliance import Recruiter
from app.routers.recruiter import require_approved_recruiter
from app.services import verification
from app.services.integrity import IntegrityPayload

router = APIRouter(prefix="/api/verify", tags=["verification"])


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class TheoryPayload(BaseModel):
    answers: list[Optional[int]] = Field(max_length=50)
    integrity: Optional[IntegrityPayload] = None


class RunPayload(BaseModel):
    language: str = Field(max_length=20)
    code: str = Field(max_length=50000)
    stdin: Optional[str] = Field(default="", max_length=10000)


class SubmitPayload(BaseModel):
    language: str = Field(max_length=20)
    code: str = Field(max_length=50000)
    integrity: Optional[IntegrityPayload] = None


@router.get("/{user_id}")
def my_status(user_id: str, _: str = Depends(require_owner), db: Session = Depends(get_db)):
    return verification.status(db, user_id)


@router.post("/{user_id}/start")
@limiter.limit("10/hour")
def start(request: Request, user_id: str, _: str = Depends(require_owner), db: Session = Depends(get_db)):
    """Starts or resumes the re-check; 202 {"preparing": job} while its questions are prepared."""
    result = _run(verification.start, db, user_id)
    return JSONResponse(result, status_code=202) if "preparing" in result else result


@router.post("/{user_id}/checks/{check_id}/theory")
@limiter.limit("10/minute")
def submit_theory(request: Request, user_id: str, check_id: str, payload: TheoryPayload,
                  _: str = Depends(require_owner), db: Session = Depends(get_db)):
    return _run(verification.submit_theory, db, user_id, check_id, payload.answers, payload.integrity)


@router.post("/{user_id}/checks/{check_id}/coding/run")
@limiter.limit("20/minute")
def run_code(request: Request, user_id: str, check_id: str, payload: RunPayload,
             _: str = Depends(require_owner), db: Session = Depends(get_db)):
    return _run(verification.run_code, db, user_id, check_id, payload.language, payload.code, payload.stdin)


@router.post("/{user_id}/checks/{check_id}/coding/submit")
@limiter.limit("10/minute")
def submit_coding(request: Request, user_id: str, check_id: str, payload: SubmitPayload,
                  _: str = Depends(require_owner), db: Session = Depends(get_db)):
    return _run(verification.submit_coding, db, user_id, check_id, payload.language, payload.code,
                payload.integrity)


@router.post("/{user_id}/checks/{check_id}/finish")
def finish(user_id: str, check_id: str, _: str = Depends(require_owner), db: Session = Depends(get_db)):
    return _run(verification.finish_now, db, user_id, check_id)


@router.post("/{user_id}/requests/{request_id}/decline")
def decline(user_id: str, request_id: str, _: str = Depends(require_owner), db: Session = Depends(get_db)):
    _run(verification.decline, db, user_id, request_id)
    return {"requests": verification.open_requests(db, user_id)}


@router.post("/candidates/{student_id}/request")
@limiter.limit("20/hour")
def recruiter_request(request: Request, student_id: str, rec: Recruiter = Depends(require_approved_recruiter),
                      db: Session = Depends(get_db)):
    """A recruiter asks a candidate they can see to verify their readiness."""
    return {"request": _run(verification.request, db, rec, student_id)}
