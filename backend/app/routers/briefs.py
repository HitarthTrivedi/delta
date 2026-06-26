import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
import uuid, datetime, json
from app.database import get_db

_log = logging.getLogger("delta.briefs")
from app.models import WeeklyBrief, Recommendation, DeltaScore, SkillNode, MarketSnapshot, User
from app.schemas.brief import BriefResponse, RecommendationComplete
from app.schemas.delta import DeltaScoreResponse
from app.services.brief_generator import generate_weekly_brief
from app.services.central_engine import log_journey_event
from app.services.delta_score import compute_delta_score
from app.services.portfolio_engine import assess_portfolio
from app.services.project_engine import recommend_proof_projects
from app.dependencies.auth import require_owner, verify_resource_owner
from app.limiter import limiter

router = APIRouter(prefix="/api/briefs", tags=["briefs"])

EVIDENCE_WEIGHTS = {
    "claimed": 0.4, "resume": 0.6, "github": 0.85,
    "certification": 0.9, "verified": 1.0,
}


@router.get("/user/{user_id}/latest", response_model=BriefResponse)
def get_latest_brief(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    brief = db.query(WeeklyBrief).filter(
        WeeklyBrief.user_id == user_id
    ).order_by(WeeklyBrief.week_start.desc(), WeeklyBrief.created_at.desc()).first()
    if not brief:
        raise HTTPException(status_code=404, detail="No brief found")
    return brief


@router.post("/generate/{user_id}", response_model=BriefResponse)
@limiter.limit("5/hour")
def generate_brief(request: Request, user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    market = db.query(MarketSnapshot).filter(
        MarketSnapshot.user_id == user_id
    ).order_by(MarketSnapshot.snapshot_date.desc()).first()

    if not market:
        # Create a premium default market snapshot for their target role
        market_id = str(uuid.uuid4())
        market = MarketSnapshot(
            id=market_id,
            user_id=user_id,
            target_role=user.target_role or "AI Developer / Software Engineer",
            snapshot_date=datetime.date.today(),
            top_demanded_skills=json.dumps(["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"]),
            emerging_skills=json.dumps(["AI Agents", "RAG Pipelines", "Vector Databases"]),
            confidence_score=0.85,
        )
        db.add(market)
        db.commit()
        db.refresh(market)

    # 1. Compute current dynamic delta score (using upgraded formula)
    completed_count = db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.status == "completed"
    ).count()

    market_demands = []
    if market.top_demanded_skills:
        try:
            market_demands = json.loads(market.top_demanded_skills) if isinstance(market.top_demanded_skills, str) else market.top_demanded_skills
        except Exception:
            market_demands = ["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"]

    current_score = compute_delta_score(skills, market_demands, completed_count)

    try:
        emerging_skills = json.loads(market.emerging_skills or "[]")
    except Exception:
        emerging_skills = []

    try:
        # 2. Invoke rich roadmap compiler
        roadmap_res = generate_weekly_brief(user, skills, market)
    except Exception as exc:
        _log.error("generate_weekly_brief failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Brief generation failed: {exc}") from exc

    market_context = {
        "target_role": market.target_role,
        "top_demanded_skills": market_demands,
        "emerging_skills": emerging_skills,
        "confidence_score": market.confidence_score,
    }
    memory_context = {
        "ambitions": {"target_role": user.target_role},
        "capabilities": {
            "skills": [
                {
                    "name": s.name,
                    "category": s.category,
                    "proficiency": s.proficiency,
                    "evidence_type": s.evidence_type,
                    "evidence_url": s.evidence_url,
                    "evidence_weight": s.evidence_weight,
                }
                for s in skills
            ],
        },
        "evidence": {"projects": [], "certifications": [], "portfolio_links": []},
    }
    roadmap_context = {
        "phases": roadmap_res.get("phases", []),
        "active_phase_id": next((phase.get("id") for phase in roadmap_res.get("phases", []) if phase.get("nodes")), None),
    }
    proof_projects = recommend_proof_projects(memory_context, roadmap_context, market_context)
    portfolio_assessment = assess_portfolio(memory_context, [], proof_projects, market_context)
    roadmap_res["proof_projects"] = proof_projects
    roadmap_res["portfolio_assessment"] = portfolio_assessment

    # 3. Create brief entry
    brief_id = str(uuid.uuid4())
    brief = WeeklyBrief(
        id=brief_id,
        user_id=user_id,
        week_start=datetime.date.today(),
        delta_score_start=current_score,
        recommendations=json.dumps(roadmap_res), # serialize roadmap dataset here!
    )
    db.add(brief)

    # 4. Extract target recommendations from the roadmap nodes (pick up to 3 that are not mastered)
    recs_to_add = []
    for phase in roadmap_res.get("phases", []):
        for node in phase.get("nodes", []):
            if node.get("status") in ("locked", "in_progress"):
                recs_to_add.append(node)
                if len(recs_to_add) >= 3:
                    break
        if len(recs_to_add) >= 3:
            break

    # Fallback to make sure we always have 3 recommendations to interact with
    if len(recs_to_add) < 3:
        for phase in roadmap_res.get("phases", []):
            for node in phase.get("nodes", []):
                if node not in recs_to_add:
                    recs_to_add.append(node)
                    if len(recs_to_add) >= 3:
                        break
            if len(recs_to_add) >= 3:
                break

    # Map selected node IDs to actual SkillNode database keys
    NODE_SKILL_MAP = {
        "node-python": "Python",
        "node-fastapi": "FastAPI",
        "node-sql": "SQL",
        "node-docker": "Docker",
        "node-system-design": "System Design",
        "node-llms": "LLMs",
        "node-mlops": "MLOps",
    }

    for node in recs_to_add:
        skill_name = node.get("skill_name") or NODE_SKILL_MAP.get(node["id"]) or node["label"]
        
        # Determine projected delta impact: locked nodes have higher learning impact
        impact = 4.0 if node.get("status") == "locked" else 2.5
        
        rec = Recommendation(
            id=str(uuid.uuid4()),
            brief_id=brief_id,
            user_id=user_id,
            skill=skill_name,
            resource_title=node["label"],
            resource_url=node.get("resource_url", "https://roadmap.sh"),
            resource_type="roadmap" if "roadmap" in node.get("resource_url", "") else "course",
            estimated_hours=3.0,
            market_signal_text=node.get("tech_twist", "High market demand"),
            projected_delta_impact=impact,
            evidence_collection_path=f"Build a GitHub project for {node['label']} and submit the repository link.",
        )
        db.add(rec)

    # 5. Save delta score history entry
    score_entry = DeltaScore(
        id=str(uuid.uuid4()),
        user_id=user_id,
        score=current_score,
        score_date=datetime.date.today(),
        skill_snapshot=json.dumps([{"name": s.name, "proficiency": s.proficiency} for s in skills]),
    )
    db.add(score_entry)
    try:
        db.commit()
        db.refresh(brief)
    except Exception as exc:
        db.rollback()
        _log.error("generate_brief DB commit failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Brief saved in memory but could not be persisted: {exc}") from exc
    return brief



@router.get("/scores/{user_id}/current", response_model=DeltaScoreResponse)
def get_current_score(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    score = db.query(DeltaScore).filter(
        DeltaScore.user_id == user_id
    ).order_by(DeltaScore.score_date.desc()).first()
    if not score:
        raise HTTPException(status_code=404, detail="No score found")
    return score


@router.get("/scores/{user_id}/history", response_model=list[DeltaScoreResponse])
def get_score_history(user_id: str, limit: int = 12, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return db.query(DeltaScore).filter(
        DeltaScore.user_id == user_id
    ).order_by(DeltaScore.score_date.desc()).limit(limit).all()


@router.post("/recommendations/{rec_id}/complete", response_model=BriefResponse)
def complete_recommendation(
    rec_id: str,
    data: RecommendationComplete,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    verify_resource_owner(rec.user_id, x_user_id=x_user_id, authorization=authorization)

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
    log_journey_event(
        db=db,
        user_id=rec.user_id,
        event_type="milestone_verified",
        summary=f"Verified proof of work for {rec.skill}.",
        evidence={
            "recommendation_id": rec.id,
            "evidence_type": data.evidence_type,
            "evidence_url": data.evidence_url,
        },
        impact={
            "skill": rec.skill,
            "evidence_weight": EVIDENCE_WEIGHTS.get(data.evidence_type, 0.4),
            "proficiency_increased": True,
        },
    )

    brief = db.query(WeeklyBrief).filter(WeeklyBrief.id == rec.brief_id).first()
    db.refresh(brief)
    return brief
