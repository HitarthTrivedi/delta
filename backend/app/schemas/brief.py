from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class RecommendationResponse(BaseModel):
    id: str
    brief_id: str
    user_id: str
    skill: str
    resource_title: Optional[str] = None
    resource_url: Optional[str] = None
    resource_type: str = "course"
    estimated_hours: float = 2.0
    market_signal_text: Optional[str] = None
    projected_delta_impact: float = 0.0
    evidence_collection_path: Optional[str] = None
    status: str = "pending"
    completed_at: Optional[datetime] = None
    evidence_type: Optional[str] = None
    evidence_url: Optional[str] = None
    user_rating: Optional[int] = None
    was_relevant: Optional[bool] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RecommendationComplete(BaseModel):
    evidence_url: str
    evidence_type: str = "github"

class RoadmapNode(BaseModel):
    id: str
    label: str
    status: str
    description: str
    tech_twist: Optional[str] = None
    architect_warning: Optional[str] = None
    certification: Optional[str] = None
    resource_url: Optional[str] = None

class RoadmapPhase(BaseModel):
    id: str
    name: str
    description: str
    nodes: List[RoadmapNode]

class BriefResponse(BaseModel):
    id: str
    user_id: str
    week_start: Optional[date] = None
    delta_score_start: float = 0.0
    delta_score_end: Optional[float] = None
    email_sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    recommendation_items: List[RecommendationResponse] = []
    
    # Custom Roadmap Integrations
    phases: Optional[List[RoadmapPhase]] = None
    demanded_skills: Optional[List[str]] = None
    user_skills: Optional[List[str]] = None

    class Config:
        from_attributes = True

