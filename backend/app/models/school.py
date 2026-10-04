from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from app.database import Base
import datetime


class ChildProfile(Base):
    """A child learner in Delta for School, created and managed by a parent.

    Children have no login of their own: they study inside the parent's account
    (child mode, PIN to exit). `user_id` is the PARENT's account id, so the
    parent's data export / account deletion automatically covers the child.
    Data minimisation: first name + grade only."""
    __tablename__ = "child_profiles"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # parent
    first_name = Column(String, nullable=False)
    grade = Column(Integer, nullable=False)
    board = Column(String, default="CBSE")
    pin_hash = Column(String, nullable=False)  # salted scrypt, "salt$hash"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SchoolLesson(Base):
    """One chapter's lesson + quiz. Generated once (AI draft), then edited and
    approved by a human reviewer. Children only ever see status='approved',
    so every child in a grade sees the same reviewed content."""
    __tablename__ = "school_lessons"

    id = Column(String, primary_key=True)
    board = Column(String, default="CBSE")
    grade = Column(Integer, nullable=False)
    subject = Column(String, nullable=False)
    chapter_no = Column(Integer, nullable=False)
    chapter_title = Column(String, nullable=False)
    content = Column(Text, nullable=True)  # lesson, markdown
    quiz = Column(Text, nullable=True)  # JSON: [{question, options[4], answer_index, explanation}]
    status = Column(String, default="draft")  # draft | approved | rejected
    generated_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    reviewed_by = Column(String, nullable=True)  # reviewer email
    reviewed_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("board", "grade", "subject", "chapter_no", name="uq_school_lesson_chapter"),)


class ChildLessonProgress(Base):
    """A child's result on one chapter (latest attempt + best score). `user_id`
    is the parent's id (see ChildProfile)."""
    __tablename__ = "child_lesson_progress"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # parent
    child_id = Column(String, ForeignKey("child_profiles.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    chapter_no = Column(Integer, nullable=False)
    last_score = Column(Integer, nullable=True)
    best_score = Column(Integer, nullable=True)
    attempts = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
