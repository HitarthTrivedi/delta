"""Job match: a pasted job description, read once, compared with the learner's skills.

`JobDescription` is shared and holds no personal data: only what was extracted
from a job ad (role, skills, a first proof task per skill), keyed by a hash of
the text. The pasted text itself is not stored. `JobTarget` links a learner to
a job they analysed; it has `user_id`, so export and erasure cover it.
"""
import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text

from app.database import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(String, primary_key=True)  # sha256 of the normalised text
    title = Column(String, nullable=False)
    company = Column(String, nullable=True)
    seniority = Column(String, nullable=True)
    skills = Column(Text, nullable=False)  # JSON: [{name, importance, task: {title, detail}}]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class JobTarget(Base):
    __tablename__ = "job_targets"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("job_descriptions.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    # While set and not passed, each new week includes tasks for this job's gaps.
    plan_until = Column(Date, nullable=True)
