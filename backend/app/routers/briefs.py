from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid, datetime, json
from app.database import get_db
from app.models import WeeklyBrief, Recommendation, DeltaScore, SkillNode, MarketSnapshot
from app.schemas.brief import BriefResponse, RecommendationComplete
from app.schemas.delta import DeltaScoreResponse

router = APIRouter(prefix="/api/briefs", tags=["briefs"])

EVIDENCE_WEIGHTS = {
    "claimed": 0.4, "resume": 0.6, "github": 0.85,
    "certification": 0.9, "verified": 1.0,
}


@router.get("/user/{user_id}/latest", response_model=BriefResponse)
def get_latest_brief(user_id: str, db: Session = Depends(get_db)):
    brief = db.query(WeeklyBrief).filter(
        WeeklyBrief.user_id == user_id
    ).order_by(WeeklyBrief.week_start.desc()).first()
    if not brief:
        raise HTTPException(status_code=404, detail="No brief found")
    return brief


@router.post("/generate/{user_id}", response_model=BriefResponse)
def generate_brief(user_id: str, db: Session = Depends(get_db)):
    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    market = db.query(MarketSnapshot).filter(
        MarketSnapshot.user_id == user_id
    ).order_by(MarketSnapshot.snapshot_date.desc()).first()

    # Compute current delta score
    total_weight = sum(s.evidence_weight * s.proficiency for s in skills) if skills else 0
    max_weight = len(skills) * 10 if skills else 1
    current_score = round((total_weight / max(max_weight, 1)) * 100, 1)

    # Determine gaps
    gaps = []
    if market and market.top_demanded_skills:
        try:
            demanded = json.loads(market.top_demanded_skills)
        except (json.JSONDecodeError, TypeError):
            demanded = []
        user_names = {s.name.lower() for s in skills}
        gaps = [d for d in demanded if d.lower() not in user_names]

    # Create brief
    brief_id = str(uuid.uuid4())
    brief = WeeklyBrief(
        id=brief_id,
        user_id=user_id,
        week_start=datetime.date.today(),
        delta_score_start=current_score,
    )
    db.add(brief)

    # Generate 3 recommendations
    resources = [
        {"skill": gaps[0] if len(gaps) > 0 else "Python", "title": "AI Engineer - Developer Roadmaps", "url": "https://roadmap.sh/ai-engineer", "type": "roadmap", "hours": 2.5, "signal": "Critical demand in market", "impact": 3.5},
        {"skill": gaps[1] if len(gaps) > 1 else "React", "title": "Software Engineer to AI Engineer Roadmap (2026 Guide)", "url": "https://roadmap.sh/ai-engineer", "type": "course", "hours": 4.0, "signal": "Emerging skill requirement", "impact": 2.8},
        {"skill": gaps[2] if len(gaps) > 2 else "FastAPI", "title": "AI Learning Roadmap: From Beginner to Expert (2026) - Coursera", "url": "https://www.coursera.org/ai", "type": "course", "hours": 3.0, "signal": "High market signal", "impact": 2.5},
    ]
    for r in resources:
        rec = Recommendation(
            id=str(uuid.uuid4()),
            brief_id=brief_id,
            user_id=user_id,
            skill=r["skill"],
            resource_title=r["title"],
            resource_url=r["url"],
            resource_type=r["type"],
            estimated_hours=r["hours"],
            market_signal_text=r["signal"],
            projected_delta_impact=r["impact"],
            evidence_collection_path=f"Complete {r['title']} and submit evidence",
        )
        db.add(rec)

    # Save delta score
    score_entry = DeltaScore(
        id=str(uuid.uuid4()),
        user_id=user_id,
        score=current_score,
        score_date=datetime.date.today(),
        skill_snapshot=json.dumps([{"name": s.name, "proficiency": s.proficiency} for s in skills]),
    )
    db.add(score_entry)
    db.commit()
    db.refresh(brief)
    return brief


@router.get("/scores/{user_id}/current", response_model=DeltaScoreResponse)
def get_current_score(user_id: str, db: Session = Depends(get_db)):
    score = db.query(DeltaScore).filter(
        DeltaScore.user_id == user_id
    ).order_by(DeltaScore.score_date.desc()).first()
    if not score:
        raise HTTPException(status_code=404, detail="No score found")
    return score


@router.get("/scores/{user_id}/history", response_model=list[DeltaScoreResponse])
def get_score_history(user_id: str, limit: int = 12, db: Session = Depends(get_db)):
    return db.query(DeltaScore).filter(
        DeltaScore.user_id == user_id
    ).order_by(DeltaScore.score_date.desc()).limit(limit).all()


@router.post("/recommendations/{rec_id}/complete", response_model=BriefResponse)
def complete_recommendation(rec_id: str, data: RecommendationComplete, db: Session = Depends(get_db)):
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.status = "completed"
    rec.completed_at = datetime.datetime.utcnow()
    rec.evidence_type = data.evidence_type
    rec.evidence_url = data.evidence_url

    # Update the user's skill
    skill = db.query(SkillNode).filter(
        SkillNode.user_id == rec.user_id,
        SkillNode.name == rec.skill,
    ).first()
    if skill:
        skill.evidence_type = data.evidence_type
        skill.evidence_url = data.evidence_url
        skill.evidence_weight = EVIDENCE_WEIGHTS.get(data.evidence_type, skill.evidence_weight)
        skill.proficiency = min(skill.proficiency + 1, 10)
        skill.last_updated = datetime.datetime.utcnow()
    else:
        new_skill = SkillNode(
            id=str(uuid.uuid4()),
            user_id=rec.user_id,
            name=rec.skill,
            category="core",
            proficiency=3,
            evidence_type=data.evidence_type,
            evidence_weight=EVIDENCE_WEIGHTS.get(data.evidence_type, 0.4),
            evidence_url=data.evidence_url,
        )
        db.add(new_skill)

    db.commit()

    brief = db.query(WeeklyBrief).filter(WeeklyBrief.id == rec.brief_id).first()
    db.refresh(brief)
    return brief
