from sqlalchemy import Column, String, Integer, Text, DateTime
from app.database import Base
import datetime


class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    source = Column(String, default="website")  # "feedback", "beta_signup", "partner_inquiry"
    meta = Column(Text, nullable=True)  # JSON blob for extra fields (firm, role, company, etc.)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
