"""A learner following a predefined role roadmap (services/roadmap_catalog.py).

One row per learner. The template content lives in code; this row only holds
where the learner is in it. It has `user_id`, so export and erasure cover it.
"""
import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String

from app.database import Base


class RoadmapEnrollment(Base):
    __tablename__ = "roadmap_enrollments"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    template_id = Column(String, nullable=False)
    template_version = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="active")  # active | completed | stopped
    started_on = Column(Date, nullable=False)
    target_date = Column(Date, nullable=True)
    week_index = Column(Integer, nullable=False, default=0)  # weeks advanced so far (0 = week 1)
    held_weeks = Column(Integer, nullable=False, default=0)  # weeks held at the current phase's gate
    assigned_by_batch_id = Column(String, nullable=True)  # set when a college assigns it (Delta for College P4)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
