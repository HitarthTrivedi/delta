"""Shared helpers for both practice sandboxes (coding + interview)."""
from __future__ import annotations

import datetime
import uuid

from sqlalchemy.orm import Session

from app.models.skill_node import SkillNode


def bump_skill(db: Session, user_id: str, skill_name: str, amount: int = 1) -> None:
    """Nudge (or create) a skill's proficiency after a completed practice
    session. Same pattern as briefs.py's complete_recommendation — small,
    capped bump rather than a full re-assessment. Caller commits."""
    if not skill_name:
        return
    skill = db.query(SkillNode).filter(
        SkillNode.user_id == user_id,
        SkillNode.name.ilike(skill_name.strip()),
    ).first()
    if skill:
        skill.proficiency = min((skill.proficiency or 0) + amount, 10)
        skill.last_updated = datetime.datetime.utcnow()
    else:
        db.add(SkillNode(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=skill_name.strip(),
            category="core",
            proficiency=min(3 + amount, 10),
            evidence_type="practiced",
            evidence_weight=0.4,
        ))
