from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class SkillInUser(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    proficiency: int = 1
    evidence_type: str = "claimed"
    evidence_weight: float = 0.4
    evidence_url: Optional[str] = None

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    id: str
    email: Optional[str] = None
    name: str
    current_role: Optional[str] = None
    target_role: Optional[str] = None
    years_experience: int = 0
    hours_per_week: int = 10
    learning_style: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    current_role: Optional[str] = None
    target_role: Optional[str] = None
    years_experience: Optional[int] = None
    hours_per_week: Optional[int] = None
    learning_style: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None
    name: str
    current_role: Optional[str] = None
    years_experience: int = 0
    target_role: Optional[str] = None
    hours_per_week: int = 10
    learning_style: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserWithSkills(UserResponse):
    skills: List[SkillInUser] = []
