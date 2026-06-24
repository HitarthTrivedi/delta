from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, SkillNode
from app.services.dossier_generator import compile_weekly_dossier
from app.dependencies.auth import require_owner

router = APIRouter(prefix="/api/dossier", tags=["dossier"])

@router.get("/weekly/{user_id}")
def get_weekly_dossier(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """
    Retrieves the immersive Weekly Dossier Portfolio assessment for a student.
    Includes active score changes, study pacing metrics, local salary trends,
    and a custom critique of keep-doing vs mistakes-to-avoid behaviors.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    
    dossier = compile_weekly_dossier(user, skills, db)
    return dossier
