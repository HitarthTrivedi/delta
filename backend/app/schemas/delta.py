from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class DeltaScoreResponse(BaseModel):
    id: str
    user_id: str
    score: float = 0.0
    score_date: Optional[date] = None
    skill_snapshot: Optional[str] = None
    market_snapshot_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
