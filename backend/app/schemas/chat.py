from pydantic import BaseModel
from typing import Optional, List

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    context: Optional[str] = None

class OnboardingStartRequest(BaseModel):
    raw_input: str
    target_role: Optional[str] = "AI Developer / Software Engineer"

class OnboardingStartResponse(BaseModel):
    ambition_summary: str
    adaptive_questions: List[str]
    market_demand_focus: str

class OnboardingFinalizeRequest(BaseModel):
    user_id: str
    raw_input: str
    adaptive_questions: List[str]
    answers: List[str]

class OnboardingFinalizeResponse(BaseModel):
    status: str
    profile: dict
