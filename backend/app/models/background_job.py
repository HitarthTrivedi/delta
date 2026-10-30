"""Background jobs: slow AI work (planning a learner's week) runs here, not
inside the page request. Named `background_jobs` so it never gets confused
with Job match (`/api/jobs`, `job_descriptions`). Has `user_id`, so export and
erasure cover it.
"""
import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    __table_args__ = (Index("ix_background_jobs_status_created", "status", "created_at"),)

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String, nullable=False)  # weekly_cycle | first_roadmap
    payload = Column(Text, nullable=False, default="{}")  # JSON
    status = Column(String, nullable=False, default="queued")  # queued | running | done | failed
    error = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
