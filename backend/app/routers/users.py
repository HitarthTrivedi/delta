from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from app.database import get_db
from app.models import User, SkillNode, MarketSnapshot
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithSkills

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}/with-skills", response_model=UserWithSkills)
def get_user_with_skills(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/stats")
def get_user_stats(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    market = db.query(MarketSnapshot).filter(
        MarketSnapshot.user_id == user_id
    ).order_by(MarketSnapshot.snapshot_date.desc()).first()

    # Compute stats
    total_skills = len(skills)
    verified_skills = [s for s in skills if s.evidence_type in ("github", "certification", "verified")]
    evidence_density = len(verified_skills) / max(total_skills, 1)

    # Market alignment
    gaps = []
    if market and market.top_demanded_skills:
        try:
            demanded = json.loads(market.top_demanded_skills) if isinstance(market.top_demanded_skills, str) else market.top_demanded_skills
        except (json.JSONDecodeError, TypeError):
            demanded = []
        user_skill_names = {s.name.lower() for s in skills}
        gaps = [d for d in demanded if d.lower() not in user_skill_names]
        role_alignment = 1 - (len(gaps) / max(len(demanded), 1))
    else:
        role_alignment = 0.0

    return {
        "role_alignment": round(role_alignment, 2),
        "evidence_density": round(evidence_density, 2),
        "market_pulse": f"{len(gaps)} gaps detected" if gaps else "Aligned",
        "gaps": gaps,
        "total_skills": total_skills,
        "verified_count": len(verified_skills),
    }
