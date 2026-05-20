from sqlalchemy import Column, String, Float, Date, Text, DateTime, ForeignKey
from app.database import Base
import datetime

class DeltaScore(Base):
    __tablename__ = "delta_scores"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    score = Column(Float, default=0.0)
    score_date = Column(Date, default=datetime.date.today)
    skill_snapshot = Column(Text, nullable=True)  # JSON string
    market_snapshot_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
