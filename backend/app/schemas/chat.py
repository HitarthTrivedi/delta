from pydantic import BaseModel
from typing import Optional, List

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    context: Optional[str] = None
    # When Agent 2 changes the weekly plan, it returns the authoritative task list here so
    # the frontend displays exactly what the AI decided — no separate re-derivation that
    # could disagree. None means "no change to the task list this turn".
    updated_actions: Optional[List[dict]] = None
    week_phase: Optional[str] = None

class OnboardingStartRequest(BaseModel):
    raw_input: str
    target_role: Optional[str] = "AI Developer / Software Engineer"

class OnboardingStartResponse(BaseModel):
    ambition_summary: str
    adaptive_questions: List[str]
    market_demand_focus: str
    market_snapshot: Optional[dict] = None

class OnboardingFinalizeRequest(BaseModel):
    user_id: str
    raw_input: str
    adaptive_questions: List[str]
    answers: List[str]

class OnboardingFinalizeResponse(BaseModel):
    status: str
    profile: dict
    career_os: Optional[dict] = None
