from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True)
    brief_id = Column(String, ForeignKey("weekly_briefs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    skill = Column(String, nullable=False)
    resource_title = Column(String, nullable=True)
    resource_url = Column(String, nullable=True)
    resource_type = Column(String, default="course")
    estimated_hours = Column(Float, default=2.0)
    market_signal_text = Column(String, nullable=True)
    projected_delta_impact = Column(Float, default=0.0)
    evidence_collection_path = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, in_progress, completed
    completed_at = Column(DateTime, nullable=True)
    evidence_type = Column(String, nullable=True)
    evidence_url = Column(String, nullable=True)
    user_rating = Column(Integer, nullable=True)
    was_relevant = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    brief = relationship("WeeklyBrief", back_populates="recommendation_items")
