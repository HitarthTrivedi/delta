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
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User")
