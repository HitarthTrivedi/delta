from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import uuid, datetime
from typing import Annotated, Optional
from app.database import get_db
from app.models import SkillNode
from app.schemas.skill import SkillCreate, SkillUpdate, SkillResponse, SkillVerify
from app.dependencies.auth import require_owner, verify_resource_owner

router = APIRouter(prefix="/api/skills", tags=["skills"])

EVIDENCE_WEIGHTS = {
    "claimed": 0.4,
    "resume": 0.6,
    "github": 0.85,
    "certification": 0.9,
    "verified": 1.0,
}


@router.get("/{user_id}", response_model=list[SkillResponse])
def get_skills(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return db.query(SkillNode).filter(SkillNode.user_id == user_id).all()


@router.post("", response_model=SkillResponse)
def create_skill(
    data: SkillCreate,
    db: Session = Depends(get_db),
    x_user_id: Annotated[Optional[str], Header()] = None,
    authorization: Annotated[Optional[str], Header()] = None,
):
    verify_resource_owner(data.user_id, x_user_id=x_user_id, authorization=authorization)
    skill = SkillNode(
        id=str(uuid.uuid4()),
        user_id=data.user_id,
        name=data.name,
        category=data.category,
        proficiency=data.proficiency,
        evidence_type=data.evidence_type,
        evidence_weight=data.evidence_weight if data.evidence_weight is not None else EVIDENCE_WEIGHTS.get(data.evidence_type, 0.4),
        evidence_url=data.evidence_url,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.put("/{skill_id}", response_model=SkillResponse)
def update_skill(
    skill_id: str,
    data: SkillUpdate,
    db: Session = Depends(get_db),
    x_user_id: Annotated[str | None, Header()] = None,
):
    skill = db.query(SkillNode).filter(SkillNode.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    # Ownership check — caller must own the skill
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header. Authentication required.")
    if skill.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: you can only update your own skills.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(skill, key, value)
    if data.evidence_type:
        skill.evidence_weight = EVIDENCE_WEIGHTS.get(data.evidence_type, skill.evidence_weight)
    skill.last_updated = datetime.datetime.utcnow()
    db.commit()
    db.refresh(skill)
    return skill


@router.post("/{skill_id}/verify", response_model=SkillResponse)
def verify_skill(
    skill_id: str,
    data: SkillVerify,
    db: Session = Depends(get_db),
    x_user_id: Annotated[str | None, Header()] = None,
):
    skill = db.query(SkillNode).filter(SkillNode.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    # Ownership check
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header. Authentication required.")
    if skill.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: you can only verify your own skills.")
    skill.evidence_type = data.evidence_type
    skill.evidence_url = data.evidence_url
    skill.evidence_weight = EVIDENCE_WEIGHTS.get(data.evidence_type, 0.4)
    skill.last_updated = datetime.datetime.utcnow()
    db.commit()
    db.refresh(skill)
    return skill
