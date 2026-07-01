from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import datetime


class OpportunityBoard(Base):
    """Per-user AI-matched job/internship board.

    Holds the user's opportunity preferences and the last AI-generated set of
    suggestions. `profile_signature` records the profile state the suggestions
    were generated from, so the UI can flag when the profile has improved and
    the board is worth regenerating.
    """
    __tablename__ = "opportunity_boards"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    preferences = Column(Text, nullable=True)   # JSON: {location, role_types, work_mode, industries, notes}
    opportunities = Column(Text, nullable=True)  # JSON: list of generated opportunities
    profile_signature = Column(String, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User")
