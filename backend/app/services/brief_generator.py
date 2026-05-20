"""Brief generator service — generates weekly growth briefs."""
import json

def generate_weekly_brief(user, skills, market_snapshot):
    """Generate personalized recommendations based on skill gaps."""
    demanded = []
    if market_snapshot and market_snapshot.top_demanded_skills:
        try:
            demanded = json.loads(market_snapshot.top_demanded_skills)
        except (json.JSONDecodeError, TypeError):
            demanded = []

    user_skill_names = {s.name.lower() for s in skills}
    gaps = [d for d in demanded if d.lower() not in user_skill_names]

    return {
        "gaps": gaps,
        "demanded_skills": demanded,
        "user_skills": [s.name for s in skills],
        "recommendations_count": min(len(gaps), 3) or 3,
    }
