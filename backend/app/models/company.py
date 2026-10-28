"""Company roadmaps: a company's stated skill needs turned into a roadmap that
students can follow as an extra track, plus tests the company sets once.

Ownership: the roadmap and its tests belong to the recruiter's company.
`company_roadmap_members` has `user_id`, so the privacy export and erasure
cover it; what the company sees is gated by the `company_roadmap` consent.
"""
import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database import Base


class CompanyRoadmap(Base):
    __tablename__ = "company_roadmaps"

    id = Column(String, primary_key=True)
    recruiter_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    role = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    skills = Column(Text, nullable=False, default="[]")  # JSON: ordered skill names
    milestones = Column(Text, nullable=False, default="[]")  # JSON: catalog-shaped milestones
    weeks = Column(Integer, nullable=False, default=8)
    status = Column(String, nullable=False, default="draft")  # draft | pending_review | approved | rejected | archived
    review_note = Column(Text, nullable=True)
    reviewed_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)


class CompanyRoadmapMember(Base):
    __tablename__ = "company_roadmap_members"
    __table_args__ = (UniqueConstraint("roadmap_id", "user_id", name="uq_company_roadmap_member"),)

    id = Column(String, primary_key=True)
    roadmap_id = Column(String, ForeignKey("company_roadmaps.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="active")  # active | left | completed
    joined_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    left_at = Column(DateTime, nullable=True)


class CompanyTest(Base):
    """A test a company set for its roadmap: generated once with no learner data,
    stored with its answer key, which never reaches a student while open."""
    __tablename__ = "company_tests"

    id = Column(String, primary_key=True)
    roadmap_id = Column(String, ForeignKey("company_roadmaps.id"), nullable=False, index=True)
    recruiter_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    category = Column(String, nullable=False, default="technical")  # technical | aptitude
    difficulty = Column(String, nullable=False, default="medium")
    questions = Column(Text, nullable=False)  # JSON, with answer_index + explanation
    time_limit_seconds = Column(Integer, nullable=True)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
