"""Quick 5 daily review: a shared question bank + each learner's spaced-review state."""
import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, Boolean

from app.database import Base


class PracticeItem(Base):
    """A multiple-choice question in the shared bank. Content only: generated
    without any learner's profile and reused by everyone with the same topic."""
    __tablename__ = "practice_items"

    id = Column(String, primary_key=True)
    topic_key = Column(String, nullable=False, index=True)  # normalised topic, e.g. "backend engineer"
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON list of 4 strings
    answer_index = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=True)
    skill = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UserPracticeState(Base):
    """Leitner box per learner per question: right answers space it out,
    a wrong answer brings it back tomorrow."""
    __tablename__ = "user_practice_state"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    item_id = Column(String, ForeignKey("practice_items.id"), primary_key=True)
    box = Column(Integer, nullable=False, default=1)
    due_date = Column(Date, nullable=False)
    last_correct = Column(Boolean, nullable=True)
    times_seen = Column(Integer, nullable=False, default=0)
    last_answered_date = Column(Date, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
