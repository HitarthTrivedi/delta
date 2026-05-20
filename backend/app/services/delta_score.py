"""Delta score computation service."""

def compute_delta_score(skills, market_alignment=0.5):
    """Compute delta score (0-100) from skills and market alignment."""
    if not skills:
        return 0.0

    total_weighted = sum(s.evidence_weight * s.proficiency for s in skills)
    max_possible = len(skills) * 10  # max proficiency = 10, max weight = 1.0
    raw_score = (total_weighted / max(max_possible, 1)) * 100

    # Factor in market alignment (30% weight)
    final = raw_score * 0.7 + market_alignment * 100 * 0.3
    return round(min(final, 100), 1)
