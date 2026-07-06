from sqlalchemy import Column, String, Float, Text, DateTime, Date, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import datetime


class CareerMemoryProfile(Base):
    __tablename__ = "career_memory_profiles"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    identity = Column(Text, nullable=True)  # JSON
    ambitions = Column(Text, nullable=True)  # JSON
    capabilities = Column(Text, nullable=True)  # JSON
    constraints = Column(Text, nullable=True)  # JSON
    preferences = Column(Text, nullable=True)  # JSON
    behavior = Column(Text, nullable=True)  # JSON
    evidence = Column(Text, nullable=True)  # JSON
    open_questions = Column(Text, nullable=True)  # JSON
    confidence_score = Column(Float, default=0.55)
    graph_version = Column(Integer, default=0)  # Tracks which graph state generated this snapshot
    tension_nodes = Column(Text, nullable=True)  # JSON list of active tension node IDs
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User")


class JourneyEvent(Base):
    __tablename__ = "journey_events"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)  # JSON
    impact = Column(Text, nullable=True)  # JSON
    event_date = Column(Date, default=datetime.date.today)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")


class RoadmapState(Base):
    __tablename__ = "roadmap_states"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    destination = Column(Text, nullable=True)  # JSON
    phases = Column(Text, nullable=True)  # JSON
    active_phase_id = Column(String, nullable=True)
    weekly_focus = Column(Text, nullable=True)  # JSON
    resource_graph = Column(Text, nullable=True)  # JSON
    proof_requirements = Column(Text, nullable=True)  # JSON
    last_replanned_reason = Column(Text, nullable=True)
    # Planning-style preference + day-wise scheduling (durable across weekly regen).
    plan_style = Column(Text, nullable=True)  # "week" (default) | "day"
    day_schedule = Column(Text, nullable=True)  # JSON: fixed commitments + personal recurring tasks
    day_plan = Column(Text, nullable=True)  # JSON: cached 7-day distribution for the current week
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User")


class ResumeProfile(Base):
    """Stores the user's structured resume and metadata for bi-weekly suggestions."""
    __tablename__ = "resume_profiles"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    # Raw full-text of the uploaded resume (if uploaded)
    raw_text = Column(Text, nullable=True)
    # JSON: { summary, skills, experience, projects, education, contact }
    structured_data = Column(Text, nullable=True)
    # ATS keyword match score 0.0–1.0
    ats_score = Column(Float, default=0.0)
    # Source: 'generated' | 'uploaded'
    source = Column(String, default="generated")
    # Timestamps for suggestion cadence
    last_suggested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User")
