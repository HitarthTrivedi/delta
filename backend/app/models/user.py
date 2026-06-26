from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    current_role = Column(String, nullable=True)
    years_experience = Column(Integer, default=0)
    target_role = Column(String, nullable=True)
    hours_per_week = Column(Integer, default=10)
    learning_style = Column(String, nullable=True)
    profile_data = Column(Text, nullable=True)      # JSON blob of onboarding intake profile
    agent2_memory_data = Column(Text, nullable=True) # JSON blob for Agent 2 chat memory/context
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    skills = relationship("SkillNode", back_populates="user", lazy="selectin")
