"""Delta for School router.

Parent-managed children (DPDP §9 verifiable parental consent): an adult who
has accepted the Terms (18+) adds a child profile after giving explicit
parental consent. The child studies inside the parent's account ("child
mode", PIN to exit), so every child endpoint is scoped to the parent's
user_id and protected by `require_owner`.

Lessons are fixed per chapter: AI-drafted once, then edited and approved by a
reviewer (CONTENT_REVIEWER_EMAILS / ADMIN_EMAILS). Children only see approved
lessons. No child data is ever sent to an AI model, and there is no tracking,
profiling or advertising for children.
"""
import datetime
import hashlib
import hmac
import json
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.limiter import limiter
from app.dependencies.auth import require_owner, current_identity, GUEST_ID
from app.models.compliance import Recruiter
from app.models.school import ChildProfile, SchoolLesson, ChildLessonProgress
from app.services import compliance
from app.services import school_curriculum as cur
from app.services.school_content_ai import generate_lesson_draft, clean_quiz

router = APIRouter(prefix="/api/school", tags=["school"])

MAX_CHILDREN = 6
PIN_RE = re.compile(r"^\d{4,6}$")


# ── Helpers ─────────────────────────────────────────────────────────────────

def _hash_pin(pin: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(pin.encode(), salt=salt, n=2 ** 14, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"


def _check_pin(pin: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        digest = hashlib.scrypt(pin.encode(), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _child_or_404(db: Session, user_id: str, child_id: str) -> ChildProfile:
    child = db.query(ChildProfile).filter(ChildProfile.id == child_id, ChildProfile.user_id == user_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child profile not found.")
    return child


def _approved_lesson(db: Session, grade: int, subject: str, chapter_no: int) -> SchoolLesson | None:
    return db.query(SchoolLesson).filter(
        SchoolLesson.board == cur.BOARD, SchoolLesson.grade == grade, SchoolLesson.subject == subject,
        SchoolLesson.chapter_no == chapter_no, SchoolLesson.status == "approved",
    ).first()


def _grade_curriculum(db: Session, grade: int, progress: dict | None = None) -> list[dict]:
    """Subjects → chapters for a grade, with which ones are available (approved)."""
    approved = {
        (l.subject, l.chapter_no)
        for l in db.query(SchoolLesson.subject, SchoolLesson.chapter_no).filter(
            SchoolLesson.board == cur.BOARD, SchoolLesson.grade == grade, SchoolLesson.status == "approved",
        ).all()
    }
    progress = progress or {}
    out = []
    for key, label in cur.SUBJECTS.items():
        b = cur.book(grade, key)
        if not b:
            continue
        out.append({
            "subject": key, "label": label, "textbook": b["textbook"], "textbook_url": cur.NCERT_TEXTBOOK_PORTAL,
            "chapters": [
                {"chapter_no": i, "title": t, "available": (key, i) in approved, **(progress.get((key, i)) or {})}
                for i, t in enumerate(b["chapters"], start=1)
            ],
        })
    return out


def _progress_map(db: Session, child_id: str) -> dict:
    return {
        (p.subject, p.chapter_no): {"best_score": p.best_score, "last_score": p.last_score, "attempts": p.attempts}
        for p in db.query(ChildLessonProgress).filter(ChildLessonProgress.child_id == child_id).all()
    }


def _child_summary(db: Session, child: ChildProfile) -> dict:
    rows = db.query(ChildLessonProgress).filter(ChildLessonProgress.child_id == child.id).all()
    scores = [r.best_score for r in rows if r.best_score is not None]
    return {
        "id": child.id, "first_name": child.first_name, "grade": child.grade, "board": child.board,
        "chapters_done": len(rows),
        "average_score": round(sum(scores) / len(scores)) if scores else None,
        "created_at": child.created_at.isoformat() if child.created_at else None,
    }


# ── Parent: manage children ─────────────────────────────────────────────────

class AddChildPayload(BaseModel):
    first_name: str = Field(min_length=1, max_length=40)
    grade: int
    pin: str
    is_parent_or_guardian: bool = False
    consent: bool = False


class PinPayload(BaseModel):
    pin: str


@router.get("/{user_id}/children")
def list_children(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    children = db.query(ChildProfile).filter(ChildProfile.user_id == user_id).order_by(ChildProfile.created_at.asc()).all()
    return {"children": [_child_summary(db, c) for c in children], "grades": cur.GRADES, "board": cur.BOARD}


@router.post("/{user_id}/children")
@limiter.limit("10/minute")
def add_child(request: Request, user_id: str, payload: AddChildPayload, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    if user_id == GUEST_ID:
        raise HTTPException(status_code=403, detail="Not available for the demo account.")
    if not compliance.has_current_terms_consent(db, user_id):
        raise HTTPException(status_code=403, detail="Accept the Terms of Use and Privacy Policy first.")
    if db.query(Recruiter).filter(Recruiter.id == user_id).first():
        raise HTTPException(status_code=403, detail="Recruiter accounts can't add children.")
    if not (payload.is_parent_or_guardian and payload.consent):
        raise HTTPException(status_code=400, detail="Only a parent or legal guardian can add a child, and their consent is required.")
    if payload.grade not in cur.GRADES:
        raise HTTPException(status_code=400, detail=f"Delta for School currently supports classes {cur.GRADES[0]}–{cur.GRADES[-1]}.")
    if not PIN_RE.match(payload.pin):
        raise HTTPException(status_code=400, detail="The PIN must be 4 to 6 digits.")
    if db.query(ChildProfile).filter(ChildProfile.user_id == user_id).count() >= MAX_CHILDREN:
        raise HTTPException(status_code=400, detail=f"You can add up to {MAX_CHILDREN} children.")

    from app.models.user import User
    if not db.query(User).filter(User.id == user_id).first():
        # Parents who only use School may never have opened the career app.
        db.add(User(id=user_id, name="Delta Parent"))
        db.flush()

    child = ChildProfile(
        id=str(uuid.uuid4()), user_id=user_id, first_name=payload.first_name.strip(),
        grade=payload.grade, board=cur.BOARD, pin_hash=_hash_pin(payload.pin),
    )
    db.add(child)
    db.commit()
    compliance.record_consent(db, user_id, compliance.PARENTAL_CONSENT, granted=True, subject_id=child.id)
    return _child_summary(db, child)


@router.delete("/{user_id}/children/{child_id}")
@limiter.limit("10/minute")
def remove_child(request: Request, user_id: str, child_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Withdraw parental consent: erase the child's profile and all progress."""
    child = _child_or_404(db, user_id, child_id)
    db.query(ChildLessonProgress).filter(ChildLessonProgress.child_id == child.id).delete()
    db.delete(child)
    db.commit()
    compliance.record_consent(db, user_id, compliance.PARENTAL_CONSENT, granted=False, subject_id=child_id)
    return {"deleted": True}


@router.post("/{user_id}/children/{child_id}/verify-pin")
@limiter.limit("10/minute")
def verify_pin(request: Request, user_id: str, child_id: str, payload: PinPayload, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    child = _child_or_404(db, user_id, child_id)
    if not _check_pin(payload.pin, child.pin_hash):
        raise HTTPException(status_code=403, detail="Wrong PIN.")
    return {"ok": True}


# ── Child learning (inside the parent's account) ───────────────────────────

class QuizSubmit(BaseModel):
    answers: list[Optional[int]]


@router.get("/{user_id}/children/{child_id}")
def child_home(user_id: str, child_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    child = _child_or_404(db, user_id, child_id)
    return {**_child_summary(db, child), "subjects": _grade_curriculum(db, child.grade, _progress_map(db, child.id))}


@router.get("/{user_id}/children/{child_id}/lessons/{subject}/{chapter_no}")
def get_lesson(user_id: str, child_id: str, subject: str, chapter_no: int, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    child = _child_or_404(db, user_id, child_id)
    lesson = _approved_lesson(db, child.grade, subject, chapter_no)
    if not lesson:
        raise HTTPException(status_code=404, detail="This chapter isn't ready yet.")
    b = cur.book(child.grade, subject)
    quiz = json.loads(lesson.quiz or "[]")
    return {
        "subject": subject, "subject_label": cur.SUBJECTS.get(subject, subject), "chapter_no": chapter_no,
        "chapter_title": lesson.chapter_title, "textbook": b["textbook"] if b else None,
        "textbook_url": cur.NCERT_TEXTBOOK_PORTAL, "content": lesson.content,
        "quiz": [{"question": q["question"], "options": q["options"]} for q in quiz],
    }


@router.post("/{user_id}/children/{child_id}/lessons/{subject}/{chapter_no}/submit")
@limiter.limit("20/minute")
def submit_quiz(request: Request, user_id: str, child_id: str, subject: str, chapter_no: int, payload: QuizSubmit,
                db: Session = Depends(get_db), _: str = Depends(require_owner)):
    child = _child_or_404(db, user_id, child_id)
    lesson = _approved_lesson(db, child.grade, subject, chapter_no)
    if not lesson:
        raise HTTPException(status_code=404, detail="This chapter isn't ready yet.")
    quiz = json.loads(lesson.quiz or "[]")
    if len(payload.answers) != len(quiz):
        raise HTTPException(status_code=400, detail=f"Expected {len(quiz)} answers.")

    results = []
    correct = 0
    for q, chosen in zip(quiz, payload.answers):
        ok = chosen == q["answer_index"]
        correct += ok
        results.append({**q, "chosen_index": chosen, "correct": ok})
    score = round(100 * correct / len(quiz)) if quiz else 0

    now = datetime.datetime.utcnow()
    prog = db.query(ChildLessonProgress).filter(
        ChildLessonProgress.child_id == child.id, ChildLessonProgress.subject == subject,
        ChildLessonProgress.chapter_no == chapter_no,
    ).first()
    if not prog:
        prog = ChildLessonProgress(id=str(uuid.uuid4()), user_id=user_id, child_id=child.id, subject=subject,
                                   chapter_no=chapter_no, attempts=0, completed_at=now)
        db.add(prog)
    prog.attempts = (prog.attempts or 0) + 1
    prog.last_score = score
    prog.best_score = max(prog.best_score or 0, score)
    prog.updated_at = now
    db.commit()

    return {"score": score, "correct": correct, "total": len(quiz), "best_score": prog.best_score, "questions": results}


# ── Reviewers: draft, edit, approve lessons ────────────────────────────────

class LessonEdit(BaseModel):
    content: str = Field(min_length=1, max_length=60000)
    quiz: list[dict]


def require_reviewer(identity=Depends(current_identity)) -> str:
    if not compliance.is_content_reviewer(identity[1]):
        raise HTTPException(status_code=403, detail="Content reviewers only.")
    return identity[1]


def _lesson_dict(l: SchoolLesson) -> dict:
    return {
        "id": l.id, "grade": l.grade, "subject": l.subject, "chapter_no": l.chapter_no,
        "chapter_title": l.chapter_title, "content": l.content, "quiz": json.loads(l.quiz or "[]"),
        "status": l.status, "reviewed_by": l.reviewed_by,
        "reviewed_at": l.reviewed_at.isoformat() if l.reviewed_at else None,
        "updated_at": l.updated_at.isoformat() if l.updated_at else None,
    }


def _lesson_or_404(db: Session, lesson_id: str) -> SchoolLesson:
    l = db.query(SchoolLesson).filter(SchoolLesson.id == lesson_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    return l


@router.get("/review/me")
def reviewer_me(identity=Depends(current_identity)):
    return {"is_reviewer": compliance.is_content_reviewer(identity[1])}


@router.get("/review/{grade:int}/{subject}")
def review_chapters(grade: int, subject: str, _: str = Depends(require_reviewer), db: Session = Depends(get_db)):
    b = cur.book(grade, subject)
    if not b:
        raise HTTPException(status_code=404, detail="Unknown class/subject.")
    lessons = {l.chapter_no: l for l in db.query(SchoolLesson).filter(
        SchoolLesson.board == cur.BOARD, SchoolLesson.grade == grade, SchoolLesson.subject == subject).all()}
    return {
        "textbook": b["textbook"], "verify_chapter_list": b.get("verify", False),
        "chapters": [
            {"chapter_no": i, "title": t, "lesson_id": lessons[i].id if i in lessons else None,
             "status": lessons[i].status if i in lessons else "missing"}
            for i, t in enumerate(b["chapters"], start=1)
        ],
    }


@router.post("/review/{grade:int}/{subject}/{chapter_no:int}/generate")
@limiter.limit("6/minute")
def review_generate(request: Request, grade: int, subject: str, chapter_no: int,
                    _: str = Depends(require_reviewer), db: Session = Depends(get_db)):
    title = cur.chapter_title(grade, subject, chapter_no)
    if not title:
        raise HTTPException(status_code=404, detail="Unknown chapter.")
    lesson = db.query(SchoolLesson).filter(
        SchoolLesson.board == cur.BOARD, SchoolLesson.grade == grade, SchoolLesson.subject == subject,
        SchoolLesson.chapter_no == chapter_no).first()
    if lesson and lesson.status == "approved":
        raise HTTPException(status_code=409, detail="This lesson is approved. Edit it instead of regenerating.")
    try:
        content, quiz = generate_lesson_draft(cur.BOARD, grade, cur.SUBJECTS[subject], cur.book(grade, subject)["textbook"], chapter_no, title)
    except ValueError:
        raise HTTPException(status_code=503, detail="Could not generate a draft right now. Try again.")
    now = datetime.datetime.utcnow()
    if not lesson:
        lesson = SchoolLesson(id=str(uuid.uuid4()), board=cur.BOARD, grade=grade, subject=subject,
                              chapter_no=chapter_no, chapter_title=title)
        db.add(lesson)
    lesson.content, lesson.quiz = content, json.dumps(quiz)
    lesson.status, lesson.generated_at, lesson.updated_at = "draft", now, now
    lesson.reviewed_by = lesson.reviewed_at = None
    db.commit()
    return _lesson_dict(lesson)


@router.get("/review/lessons/{lesson_id}")
def review_get(lesson_id: str, _: str = Depends(require_reviewer), db: Session = Depends(get_db)):
    return _lesson_dict(_lesson_or_404(db, lesson_id))


@router.put("/review/lessons/{lesson_id}")
def review_edit(lesson_id: str, payload: LessonEdit, _: str = Depends(require_reviewer), db: Session = Depends(get_db)):
    lesson = _lesson_or_404(db, lesson_id)
    quiz = clean_quiz(payload.quiz)
    if len(quiz) != len(payload.quiz) or len(quiz) < 3:
        raise HTTPException(status_code=400, detail="Each quiz question needs text, 4 options and a correct answer (at least 3 questions).")
    lesson.content, lesson.quiz = payload.content.strip(), json.dumps(quiz)
    # Any edit needs a fresh approval before children see it.
    lesson.status, lesson.reviewed_by, lesson.reviewed_at = "draft", None, None
    lesson.updated_at = datetime.datetime.utcnow()
    db.commit()
    return _lesson_dict(lesson)


@router.post("/review/lessons/{lesson_id}/approve")
def review_approve(lesson_id: str, email: str = Depends(require_reviewer), db: Session = Depends(get_db)):
    lesson = _lesson_or_404(db, lesson_id)
    if not lesson.content or len(clean_quiz(json.loads(lesson.quiz or "[]"))) < 3:
        raise HTTPException(status_code=400, detail="A lesson needs content and at least 3 valid quiz questions.")
    lesson.status, lesson.reviewed_by, lesson.reviewed_at = "approved", email, datetime.datetime.utcnow()
    db.commit()
    return _lesson_dict(lesson)


@router.post("/review/lessons/{lesson_id}/reject")
def review_reject(lesson_id: str, email: str = Depends(require_reviewer), db: Session = Depends(get_db)):
    lesson = _lesson_or_404(db, lesson_id)
    lesson.status, lesson.reviewed_by, lesson.reviewed_at = "rejected", email, datetime.datetime.utcnow()
    db.commit()
    return _lesson_dict(lesson)
