"""Seed the guest user with sample data for development."""
import uuid, json, datetime, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base
from app.models import User, SkillNode, DeltaScore, WeeklyBrief, Recommendation, MarketSnapshot

GUEST_ID = "00000000-0000-0000-0000-000000000000"

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if already seeded
    if db.query(User).filter(User.id == GUEST_ID).first():
        print("Guest user already exists, skipping seed.")
        db.close()
        return

    # 1. Create guest user
    user = User(
        id=GUEST_ID,
        email="guest@delta.dev",
        name="Guest Pro",
        current_role="CS Student",
        years_experience=1,
        target_role="AI Developer / Software Engineer",
        hours_per_week=15,
        learning_style="hands-on",
    )
    db.add(user)

    # 2. Create skills
    skills_data = [
        ("Python", "core", 8, "github", 0.85, "https://github.com/guest/python-projects"),
        ("React", "core", 6, "resume", 0.6, None),
        ("FastAPI", "core", 7, "github", 0.85, "https://github.com/guest/fastapi-app"),
        ("SQL", "core", 5, "claimed", 0.4, None),
        ("Docker", "devops", 3, "claimed", 0.4, None),
    ]
    for name, cat, prof, ev_type, weight, url in skills_data:
        db.add(SkillNode(
            id=str(uuid.uuid4()),
            user_id=GUEST_ID,
            name=name,
            category=cat,
            proficiency=prof,
            evidence_type=ev_type,
            evidence_weight=weight,
            evidence_url=url,
        ))

    # 3. Market snapshot
    market_id = str(uuid.uuid4())
    db.add(MarketSnapshot(
        id=market_id,
        user_id=GUEST_ID,
        target_role="AI Developer / Software Engineer",
        snapshot_date=datetime.date.today(),
        top_demanded_skills=json.dumps(["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"]),
        emerging_skills=json.dumps(["AI Agents", "RAG Pipelines", "Vector Databases"]),
        confidence_score=0.82,
    ))

    # 4. Delta score
    db.add(DeltaScore(
        id=str(uuid.uuid4()),
        user_id=GUEST_ID,
        score=42.5,
        score_date=datetime.date.today(),
        skill_snapshot=json.dumps([
            {"name": "Python", "proficiency": 8},
            {"name": "React", "proficiency": 6},
            {"name": "FastAPI", "proficiency": 7},
            {"name": "SQL", "proficiency": 5},
            {"name": "Docker", "proficiency": 3},
        ]),
        market_snapshot_id=market_id,
    ))

    # 5. Weekly brief with 3 recommendations
    brief_id = str(uuid.uuid4())
    db.add(WeeklyBrief(
        id=brief_id,
        user_id=GUEST_ID,
        week_start=datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday()),
        delta_score_start=42.5,
    ))

    recs = [
        {
            "skill": "LLMs",
            "title": "AI Engineer - Developer Roadmaps",
            "url": "https://roadmap.sh/ai-engineer",
            "type": "roadmap",
            "hours": 2.5,
            "signal": "This supports your target role: AI Developer / Software Engineer.",
            "impact": 3.5,
        },
        {
            "skill": "Docker",
            "title": "Software Engineer to AI Engineer Roadmap (2026 Guide)",
            "url": "https://roadmap.sh/ai-engineer",
            "type": "course",
            "hours": 4.0,
            "signal": "This supports your target role: AI Developer / Software Engineer.",
            "impact": 2.8,
        },
        {
            "skill": "System Design",
            "title": "AI Learning Roadmap: From Beginner to Expert (2026) - Coursera",
            "url": "https://www.coursera.org/ai",
            "type": "course",
            "hours": 3.0,
            "signal": "This supports your target role: AI Developer / Software Engineer.",
            "impact": 2.5,
        },
    ]
    for r in recs:
        db.add(Recommendation(
            id=str(uuid.uuid4()),
            brief_id=brief_id,
            user_id=GUEST_ID,
            skill=r["skill"],
            resource_title=r["title"],
            resource_url=r["url"],
            resource_type=r["type"],
            estimated_hours=r["hours"],
            market_signal_text=r["signal"],
            projected_delta_impact=r["impact"],
            evidence_collection_path=f"Complete {r['title']} and submit evidence",
        ))

    db.commit()
    db.close()
    print("✅ Guest user seeded successfully!")

if __name__ == "__main__":
    seed()
