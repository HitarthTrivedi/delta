from sqlalchemy import Column, String, Float, Date, Text, DateTime, ForeignKey
from app.database import Base
import datetime

class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    target_role = Column(String, nullable=True)
    snapshot_date = Column(Date, default=datetime.date.today)
    top_demanded_skills = Column(Text, nullable=True)  # JSON
    emerging_skills = Column(Text, nullable=True)  # JSON
    raw_data = Column(Text, nullable=True)  # JSON
    confidence_score = Column(Float, default=0.7)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
