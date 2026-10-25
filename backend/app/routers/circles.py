"""Study circles API: create, join by invite code, leave, and owner controls."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_owner
from app.limiter import limiter
from app.services import circles

router = APIRouter(prefix="/api/circles", tags=["circles"])


class CreatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class JoinPayload(BaseModel):
    code: str = Field(min_length=4, max_length=16)


def _run(fn, *args):
    try:
        return fn(*args)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{user_id}")
def my_circles(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return circles.board(db, user_id)


@router.post("/{user_id}")
@limiter.limit("10/minute")
def create_circle(request: Request, user_id: str, payload: CreatePayload, db: Session = Depends(get_db),
                  _: str = Depends(require_owner)):
    return _run(circles.create, db, user_id, payload.name)


@router.get("/{user_id}/preview/{code}")
@limiter.limit("30/minute")
def preview_circle(request: Request, user_id: str, code: str, db: Session = Depends(get_db),
                   _: str = Depends(require_owner)):
    found = circles.preview(db, code)
    if not found:
        raise HTTPException(status_code=404, detail="This invite link is not valid any more. Ask for a new one.")
    return found


@router.post("/{user_id}/join")
@limiter.limit("10/minute")
def join_circle(request: Request, user_id: str, payload: JoinPayload, db: Session = Depends(get_db),
                _: str = Depends(require_owner)):
    return _run(circles.join, db, user_id, payload.code)


@router.delete("/{user_id}/{circle_id}")
def leave_circle(user_id: str, circle_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return circles.leave(db, user_id, circle_id)


@router.delete("/{user_id}/{circle_id}/members/{member_id}")
@limiter.limit("20/minute")
def remove_member(request: Request, user_id: str, circle_id: str, member_id: str, db: Session = Depends(get_db),
                  _: str = Depends(require_owner)):
    return _run(circles.remove_member, db, user_id, circle_id, member_id)


@router.post("/{user_id}/{circle_id}/new-code")
@limiter.limit("10/minute")
def new_code(request: Request, user_id: str, circle_id: str, db: Session = Depends(get_db),
             _: str = Depends(require_owner)):
    return _run(circles.new_invite_code, db, user_id, circle_id)
