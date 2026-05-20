"""Delta score computation service with habit and market alignment metrics."""

def compute_delta_score(skills, market_demands: list = None, completed_recs_count: int = 0) -> float:
    """
    Compute Delta Career Score (0-100) based on:
    1. Skill Proficiency & Evidence Quality (50% weight)
    2. Market Alignment (30% weight)
    3. Consistency and Recommendation Completion Streak (20% weight)
    """
    if not skills:
        return 0.0

    # 1. Skills & Evidence Score (50%)
    total_weighted = sum(s.evidence_weight * s.proficiency for s in skills)
    max_possible = len(skills) * 10.0  # max proficiency = 10, max weight = 1.0 (verified)
    skills_score = (total_weighted / max(max_possible, 1.0)) * 100.0

    # 2. Market Alignment Score (30%)
    alignment_score = 50.0  # Default baseline alignment
    if market_demands:
        user_skills_lower = {s.name.lower() for s in skills}
        
        # Defensive normalization to support both string list and object list formats
        demanded_names = []
        for item in market_demands:
            if isinstance(item, dict):
                name = item.get("name") or item.get("skill") or ""
                if name:
                    demanded_names.append(name)
            elif isinstance(item, str):
                demanded_names.append(item)

        matches = sum(1 for m in demanded_names if m.lower() in user_skills_lower)
        alignment_score = (matches / max(len(demanded_names), 1)) * 100.0

    # 3. Consistency and Habit Score (20%)
    # Base level consistency is 60; each completed recommendation adds a bonus of +10 up to 100 max
    habit_score = 60.0 + min(completed_recs_count * 10.0, 40.0)

    # 4. Final Weighted aggregation
    final_score = (skills_score * 0.5) + (alignment_score * 0.3) + (habit_score * 0.2)
    return round(min(max(final_score, 0.0), 100.0), 1)
