from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class MarketSnapshotResponse(BaseModel):
    id: str
    user_id: str
    target_role: Optional[str] = None
    snapshot_date: Optional[date] = None
    top_demanded_skills: Optional[str] = None
    emerging_skills: Optional[str] = None
    confidence_score: float = 0.7
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
