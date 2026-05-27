"""Competitive opportunities calendar service."""
from app.services.opportunity_adapters import collect_opportunities


def generate_upcoming_events(
    user_skills: list,
    days_ahead: int = 30,
    target_role: str | None = None,
    sources: list[str] | None = None,
) -> list:
    """
    Generate a normalized calendar of contests, hackathons, market research
    tasks, and domain opportunities using pluggable adapters.
    """
    return collect_opportunities(
        user_skills=user_skills,
        target_role=target_role,
        days_ahead=days_ahead,
        sources=sources,
    )
