from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import datetime


class SandboxSession(Base):
    """A practice attempt in any sandbox: a coding problem, a mock
    interview, or a theory test. `type` discriminates the payload shape stored in `data`."""
    __tablename__ = "sandbox_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # 'coding' | 'interview' | 'theory'
    title = Column(String, nullable=False)
    status = Column(String, default="in_progress")  # in_progress | completed
    data = Column(Text, nullable=True)  # JSON: type-specific payload
    score = Column(Integer, nullable=True)  # 0-100, set on completion
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User")
