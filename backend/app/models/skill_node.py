from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class SkillNode(Base):
    __tablename__ = "skill_nodes"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    proficiency = Column(Integer, default=1)
    evidence_type = Column(String, default="claimed")
    evidence_weight = Column(Float, default=0.4)
    evidence_url = Column(String, nullable=True)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="skills")
