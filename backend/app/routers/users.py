from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import json
from app.database import get_db
from app.models import User, SkillNode, MarketSnapshot
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithSkills
from app.dependencies.auth import require_owner

router = APIRouter(prefix="/api/users", tags=["users"])


from app.services.profile_store import load_profile
from app.services.ingestion_engine_v2 import REQUIRED_FIELDS

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        try:
            user = User(
                id=user_id,
                email=f"user_{user_id}@delta.local",
                name="delta Member",
                current_role="Professional",
                years_experience=0,
                target_role="Software Engineer",
                hours_per_week=10,
                learning_style="hands-on"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=500, detail="Failed to create user.")

    profile = load_profile(user_id)
    onboarding_complete = profile.get("onboarding_complete", False)

    filled = [f for f in REQUIRED_FIELDS if profile.get(f)]
    pct = round((len(filled) / len(REQUIRED_FIELDS)) * 100, 1) if REQUIRED_FIELDS else 100.0
    if onboarding_complete:
        pct = 100.0

    user_resp = UserResponse.model_validate(user)
    user_resp.onboarding_complete = onboarding_complete
    user_resp.onboarding_percentage = pct
    return user_resp


@router.get("/{user_id}/with-skills", response_model=UserWithSkills)
def get_user_with_skills(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        try:
            user = User(
                id=user_id,
                email=f"user_{user_id}@delta.local",
                name="delta Member",
                current_role="Professional",
                years_experience=0,
                target_role="Software Engineer",
                hours_per_week=10,
                learning_style="hands-on"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=500, detail="Failed to create user.")
    
    profile = load_profile(user_id)
    onboarding_complete = profile.get("onboarding_complete", False)
    
    filled = [f for f in REQUIRED_FIELDS if profile.get(f)]
    pct = round((len(filled) / len(REQUIRED_FIELDS)) * 100, 1) if REQUIRED_FIELDS else 100.0
    if onboarding_complete:
        pct = 100.0
        
    user_resp = UserWithSkills.model_validate(user)
    user_resp.onboarding_complete = onboarding_complete
    user_resp.onboarding_percentage = pct
    return user_resp


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, data: UserUpdate, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/stats")
def get_user_stats(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    market = db.query(MarketSnapshot).filter(
        MarketSnapshot.user_id == user_id
    ).order_by(MarketSnapshot.snapshot_date.desc()).first()

    # Dynamic completed recommendation habits
    from app.models.recommendation import Recommendation
    completed_recs = db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.status == "completed"
    ).all()
    completed_count = len(completed_recs)

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
        
        # Defensive normalization to support both string list and object list formats
        demanded_names = []
        for item in demanded:
            if isinstance(item, dict):
                name = item.get("name") or item.get("skill") or ""
                if name:
                    demanded_names.append(name)
            elif isinstance(item, str):
                demanded_names.append(item)

        gaps = [d for d in demanded_names if d.lower() not in user_skill_names]
        role_alignment = 1 - (len(gaps) / max(len(demanded_names), 1))
    else:
        role_alignment = 0.5

    # Consistency rating
    consistency_index = round(min(60.0 + (completed_count * 10.0), 100.0), 1)

    return {
        "role_alignment": round(role_alignment, 2),
        "evidence_density": round(evidence_density, 2),
        "market_pulse": f"{len(gaps)} gaps detected" if gaps else "Aligned",
        "gaps": gaps,
        "total_skills": total_skills,
        "verified_count": len(verified_skills),
        "consistency_index": consistency_index,
        "completed_recommendations_count": completed_count
    }
