from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SkillCreate(BaseModel):
    user_id: str
    name: str
    category: Optional[str] = None
    proficiency: int = 1
    evidence_type: str = "claimed"
    evidence_url: Optional[str] = None

class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    proficiency: Optional[int] = None
    evidence_type: Optional[str] = None
    evidence_url: Optional[str] = None

class SkillVerify(BaseModel):
    evidence_type: str
    evidence_url: str

class SkillResponse(BaseModel):
    id: str
    user_id: str
    name: str
    category: Optional[str] = None
    proficiency: int = 1
    evidence_type: str = "claimed"
    evidence_weight: float = 0.4
    evidence_url: Optional[str] = None
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
