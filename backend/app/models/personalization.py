from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database import Base
import datetime

class PersonalizationProfile(Base):
    __tablename__ = "personalization_profiles"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    raw_intake = Column(Text, nullable=True)  # JSON
    structured_profile = Column(Text, nullable=True)  # JSON
    ai_questions_asked = Column(Text, nullable=True)  # JSON
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
