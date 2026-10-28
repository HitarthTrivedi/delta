from sqlalchemy import Column, String, Text, DateTime, Index
from app.database import Base
import datetime


class ConsentRecord(Base):
    """Append-only log of consent events (DPDP Act §6: consent must be
    provable). The latest row per (user_id, purpose) is the current state.

    No FK to users on purpose: a minimal, pseudonymous record (account id,
    purpose, action, version, timestamp) is kept after account deletion as
    proof of what was consented to and when."""
    __tablename__ = "consent_records"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    # 'terms_privacy' | 'recruiter_visibility' | 'recruiter_terms' | 'parental_consent' | 'account_deleted'
    purpose = Column(String, nullable=False)
    # For parental consent: the child profile the parent consented for.
    subject_id = Column(String, nullable=True)
    action = Column(String, nullable=False)  # 'granted' | 'withdrawn'
    policy_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class Recruiter(Base):
    """A recruiter account. Separate from `users` (students): same Supabase
    auth, but a recruiter never gets a student profile. Sees nothing until an
    admin sets status='approved'."""
    __tablename__ = "recruiters"

    id = Column(String, primary_key=True)  # Supabase auth user id
    email = Column(String, nullable=True)
    name = Column(String, nullable=False)
    company = Column(String, nullable=False)
    designation = Column(String, nullable=True)
    company_website = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending | approved | rejected
    preferences = Column(Text, nullable=True)  # JSON: last saved search preferences
    # Which students this recruiter can ever see: "campus" = only opted-in students of
    # colleges that linked them; "open" = only opted-in students not in a college.
    pool = Column(String, nullable=False, default="open", server_default="open")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class RecruiterProfileView(Base):
    """Every time a recruiter opens a student's full profile. Shown to the
    student ("who viewed my profile") — transparency + an audit trail. The
    company is snapshotted (no FK) so the student's history survives the
    recruiter deleting their account."""
    __tablename__ = "recruiter_profile_views"

    id = Column(String, primary_key=True)
    recruiter_id = Column(String, nullable=False, index=True)
    recruiter_company = Column(String, nullable=True)
    student_id = Column(String, nullable=False, index=True)
    viewed_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (Index("ix_profile_views_student_time", "student_id", "viewed_at"),)
