from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import datetime
import json
import uuid

from app.database import get_db
from app.models import JourneyEvent, PersonalizationProfile, SkillNode, User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    OnboardingFinalizeRequest,
    OnboardingFinalizeResponse,
    OnboardingStartRequest,
    OnboardingStartResponse,
)
from app.services.central_engine import (
    compile_career_context,
    initialize_career_os_for_user,
    log_journey_event,
)
from app.services.onboarding_pipeline import finalize_onboarding, start_onboarding

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
def chat_message(data: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    skills = db.query(SkillNode).filter(SkillNode.user_id == data.user_id).all()
    try:
        career_context = compile_career_context(db, data.user_id)
    except Exception:
        career_context = {}

    user_context = f"User: {user.name if user else 'Unknown'}, Target: {user.target_role if user else 'N/A'}"
    skills_context = ", ".join([f"{s.name} ({s.proficiency}/10)" for s in skills]) if skills else "No skills yet"
    context_json = json.dumps(career_context, default=str)[:8000]

    try:
        from app.services.ai_service import generate_response

        prompt = f"""You are Delta, the central AI assistant inside a personalized Career OS.
Use the user's Career Memory, Roadmap State, Market Pulse, Journey Log, Proof Projects, and Portfolio Assessment.
Be honest, specific, and action-oriented. If the user is drifting, say it clearly but supportively.

The user is:
{user_context}
Skills: {skills_context}

Career OS Context JSON:
{context_json}

User message: {data.message}

Respond with a practical next step, mention relevant roadmap/project/market context when useful, and ask at most one follow-up question."""
        response = generate_response(prompt)
        log_journey_event(
            db=db,
            user_id=data.user_id,
            event_type="assistant_guidance",
            summary=f"Delta answered career question: {data.message[:120]}",
            evidence={"message": data.message},
            impact={"context_used": bool(career_context)},
        )
        return ChatResponse(response=response, context=user_context)
    except Exception:
        next_project = (career_context.get("proof_projects") or [{}])[0]
        weekly_focus = (career_context.get("roadmap") or {}).get("weekly_focus", {})
        return ChatResponse(
            response=f"I see you're working toward becoming a {user.target_role if user else 'developer'}! "
            f"Your current focus is {weekly_focus.get('phase_name', 'building proof-backed skills')}. "
            f"Based on your {len(skills)} tracked skills, the strongest next proof is: "
            f"{next_project.get('title', 'one GitHub project with a clean README and demo')}. "
            f"Do that before adding more claimed skills.",
            context=user_context,
        )


@router.get("/history/{user_id}")
def chat_history(user_id: str, db: Session = Depends(get_db)):
    events = db.query(JourneyEvent).filter(
        JourneyEvent.user_id == user_id,
        JourneyEvent.event_type == "assistant_guidance",
    ).order_by(JourneyEvent.created_at.desc()).limit(6).all()
    messages = []
    for event in reversed(events):
        payload = json.loads(event.evidence or "{}")
        if payload.get("message"):
            messages.append({"role": "user", "content": payload["message"]})
        messages.append({"role": "assistant", "content": event.summary})
    return {"messages": messages}


@router.post("/onboarding/start", response_model=OnboardingStartResponse)
def onboarding_start(data: OnboardingStartRequest):
    res = start_onboarding(data.raw_input, data.target_role)
    return OnboardingStartResponse(
        ambition_summary=res.get("ambition_summary", "Aspirations loaded."),
        adaptive_questions=res.get("adaptive_questions", []),
        market_demand_focus=res.get("market_demand_focus", ""),
        market_snapshot=res.get("market_snapshot", {}),
    )


@router.post("/onboarding/finalize", response_model=OnboardingFinalizeResponse)
def onboarding_finalize(data: OnboardingFinalizeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile_data = finalize_onboarding(data.raw_input, data.adaptive_questions, data.answers)

    user.target_role = profile_data.get("ambitions", user.target_role)
    user.hours_per_week = profile_data.get("hours_per_week", user.hours_per_week)
    user.learning_style = profile_data.get("learning_style", user.learning_style)
    user.updated_at = datetime.datetime.utcnow()

    profile = db.query(PersonalizationProfile).filter(PersonalizationProfile.user_id == data.user_id).first()
    raw_intake_payload = {
        "raw_input": data.raw_input,
        "adaptive_questions": data.adaptive_questions,
        "answers": data.answers,
    }

    if not profile:
        profile = PersonalizationProfile(
            id=str(uuid.uuid4()),
            user_id=data.user_id,
            raw_intake=json.dumps(raw_intake_payload),
            structured_profile=json.dumps(profile_data),
            ai_questions_asked=json.dumps(data.adaptive_questions),
            created_at=datetime.datetime.utcnow(),
            last_updated=datetime.datetime.utcnow(),
        )
        db.add(profile)
    else:
        profile.raw_intake = json.dumps(raw_intake_payload)
        profile.structured_profile = json.dumps(profile_data)
        profile.ai_questions_asked = json.dumps(data.adaptive_questions)
        profile.last_updated = datetime.datetime.utcnow()

    for skill_name in profile_data.get("extracted_skills", []):
        existing_skill = db.query(SkillNode).filter(
            SkillNode.user_id == data.user_id,
            SkillNode.name.ilike(skill_name),
        ).first()
        if not existing_skill:
            db.add(SkillNode(
                id=str(uuid.uuid4()),
                user_id=data.user_id,
                name=skill_name,
                category="core",
                proficiency=3,
                evidence_type="claimed",
                evidence_weight=0.4,
                last_updated=datetime.datetime.utcnow(),
                created_at=datetime.datetime.utcnow(),
            ))

    db.commit()
    db.refresh(user)
    career_os = initialize_career_os_for_user(
        db=db,
        user_id=data.user_id,
        source="ai_adaptive_onboarding",
        structured=profile_data,
    )

    return OnboardingFinalizeResponse(
        status="success",
        profile=profile_data,
        career_os=career_os,
    )
