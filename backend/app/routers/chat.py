from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, SkillNode
from app.schemas.chat import ChatRequest, ChatResponse
import json

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
