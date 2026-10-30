"""Verified readiness re-check (Master Plan backlog #9).

- `verified_items`: a shared question bank made once per topic with no
  learner data. Kept apart from the Quick 5 bank so these questions are never
  practised in advance.
- `verified_seen`: which bank questions a learner has already been shown.
- `coding_packages`: generated coding problems, shared and kept (generate once).
- `readiness_checks`: one strictly timed re-check and its result.
- `verification_requests`: a recruiter asking a candidate to verify.
Tables with `user_id` are covered by the privacy export and erasure.
"""
import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.database import Base


class VerifiedItem(Base):
    __tablename__ = "verified_items"

    id = Column(String, primary_key=True)  # sha1(topic_key|question)[:32]
    topic_key = Column(String, nullable=False, index=True)
    difficulty = Column(String, nullable=False, default="medium")
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON list of 4
    answer_index = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=True)
    skill = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class VerifiedSeen(Base):
    __tablename__ = "verified_seen"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    item_id = Column(String, ForeignKey("verified_items.id"), primary_key=True)
    seen_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class CodingPackage(Base):
    __tablename__ = "coding_packages"

    problem_key = Column(String, primary_key=True)  # "topic::title"
    package = Column(Text, nullable=False)  # JSON: statement, examples, starter_code, test_cases
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class ReadinessCheck(Base):
    __tablename__ = "readiness_checks"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="in_progress")  # in_progress | verified | not_verified
    parts = Column(Text, nullable=False, default="{}")  # JSON: session ids and deadlines per part
    baseline = Column(Float, nullable=True)  # practice readiness on the same parts, at start
    check_score = Column(Float, nullable=True)
    flags = Column(Text, nullable=False, default="[]")  # JSON list of integrity reasons
    request_id = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)


class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id = Column(String, primary_key=True)
    recruiter_id = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # the student
    status = Column(String, nullable=False, default="open")  # open | done | declined
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
