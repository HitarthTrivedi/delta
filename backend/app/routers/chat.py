from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import json
import datetime

from app.database import get_db
from app.models import User, SkillNode, PersonalizationProfile
from app.schemas.chat import (
    ChatRequest, ChatResponse,
    OnboardingStartRequest, OnboardingStartResponse,
    OnboardingFinalizeRequest, OnboardingFinalizeResponse
)
from app.services.onboarding_pipeline import start_onboarding, finalize_onboarding

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
def chat_message(data: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    skills = db.query(SkillNode).filter(SkillNode.user_id == data.user_id).all()

    user_context = f"User: {user.name if user else 'Unknown'}, Target: {user.target_role if user else 'N/A'}"
    skills_context = ", ".join([f"{s.name} ({s.proficiency}/10)" for s in skills]) if skills else "No skills yet"

    # Try Gemini API
    try:
        from app.services.ai_service import generate_response
        prompt = f"""You are Delta, a career AI assistant. The user is:
{user_context}
Skills: {skills_context}

User message: {data.message}

Respond helpfully about their career journey. Be encouraging but data-driven."""
        response = generate_response(prompt)
        return ChatResponse(response=response, context=user_context)
    except Exception:
        # Fallback mock response
        return ChatResponse(
            response=f"I see you're working toward becoming a {user.target_role if user else 'developer'}! "
                     f"Based on your current skills ({len(skills)} tracked), I'd recommend focusing on "
                     f"building evidence through GitHub projects and certifications. "
                     f"Your Delta Score reflects your market readiness — let's push it higher this week!",
            context=user_context,
        )


@router.post("/onboarding/start", response_model=OnboardingStartResponse)
def onboarding_start(data: OnboardingStartRequest):
    """
    Ingests initial raw aspirations and triggers AI-driven custom research questions.
    """
    res = start_onboarding(data.raw_input, data.target_role)
    return OnboardingStartResponse(
        ambition_summary=res.get("ambition_summary", "Aspirations loaded."),
        adaptive_questions=res.get("adaptive_questions", []),
        market_demand_focus=res.get("market_demand_focus", "")
    )


@router.post("/onboarding/finalize", response_model=OnboardingFinalizeResponse)
def onboarding_finalize(data: OnboardingFinalizeRequest, db: Session = Depends(get_db)):
    """
    Ingests follow-up answers and compiles/registers the finalized user profile.
    """
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Run extraction pipeline
    profile_data = finalize_onboarding(data.raw_input, data.adaptive_questions, data.answers)

    # 1. Update Core User Model
    user.target_role = profile_data.get("ambitions", user.target_role)
    user.hours_per_week = profile_data.get("hours_per_week", user.hours_per_week)
    user.learning_style = profile_data.get("learning_style", user.learning_style)
    user.updated_at = datetime.datetime.utcnow()

    # 2. Sync PersonalizationProfile Record
    profile = db.query(PersonalizationProfile).filter(PersonalizationProfile.user_id == data.user_id).first()
    raw_intake_payload = {
        "raw_input": data.raw_input,
        "adaptive_questions": data.adaptive_questions,
        "answers": data.answers
    }
    
    if not profile:
        profile = PersonalizationProfile(
            id=str(uuid.uuid4()),
            user_id=data.user_id,
            raw_intake=json.dumps(raw_intake_payload),
            structured_profile=json.dumps(profile_data),
            ai_questions_asked=json.dumps(data.adaptive_questions),
            created_at=datetime.datetime.utcnow(),
            last_updated=datetime.datetime.utcnow()
        )
        db.add(profile)
    else:
        profile.raw_intake = json.dumps(raw_intake_payload)
        profile.structured_profile = json.dumps(profile_data)
        profile.ai_questions_asked = json.dumps(data.adaptive_questions)
        profile.last_updated = datetime.datetime.utcnow()

    # 3. Add any extracted skills as skill nodes (claimed starting base)
    for skill_name in profile_data.get("extracted_skills", []):
        existing_skill = db.query(SkillNode).filter(
            SkillNode.user_id == data.user_id,
            SkillNode.name.ilike(skill_name)
        ).first()
        if not existing_skill:
            db.add(SkillNode(
                id=str(uuid.uuid4()),
                user_id=data.user_id,
                name=skill_name,
                category="core",
                proficiency=3, # starting baseline claimed
                evidence_type="claimed",
                evidence_weight=0.4,
                last_updated=datetime.datetime.utcnow(),
                created_at=datetime.datetime.utcnow()
            ))

    db.commit()
    db.refresh(user)

    return OnboardingFinalizeResponse(
        status="success",
        profile=profile_data
    )
