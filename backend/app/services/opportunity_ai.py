"""AI-matched job / internship suggestions.

Uses the profile + user preferences to have the LLM suggest roles that fit the
user *now*, and get better as the profile improves. Suggestions are role-level
(with target-company profiles) rather than fabricated live postings; each one
carries a real job-search deeplink so the user can jump straight to openings.
"""
from __future__ import annotations

import hashlib
import json
import logging
from urllib.parse import quote_plus

from app.services.ai_service import generate_json
from app.services.profile_store import load_profile, profile_as_context_string

logger = logging.getLogger("delta.opportunity_ai")

ROLE_TYPE_LABELS = {
    "internship": "Internships",
    "full_time": "Full-time roles",
    "part_time": "Part-time roles",
}


def profile_signature(user_id: str) -> str:
    """A stable hash of the profile fields that should drive opportunity fit.
    When any of these change, the board is considered stale and worth refreshing.
    """
    p = load_profile(user_id) or {}
    basis = {
        "target_role": p.get("target_role") or p.get("goal_direction"),
        "skills": sorted(p.get("skills") or []) if isinstance(p.get("skills"), list) else p.get("skills"),
        "experience_level": p.get("experience_level"),
        "projects": p.get("projects"),
        "major": p.get("major"),
        "study_year": p.get("study_year"),
        "target_industries": p.get("target_industries"),
    }
    raw = json.dumps(basis, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _search_url(query: str, location: str | None) -> str:
    keywords = quote_plus((query or "").strip())
    loc = quote_plus((location or "").strip())
    url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}"
    if loc:
        url += f"&location={loc}"
    return url


def _normalize(item: dict, preferences: dict) -> dict | None:
    title = str(item.get("title") or "").strip()
    if not title:
        return None
    role_type = str(item.get("role_type") or "").strip().lower()
    if role_type not in ("internship", "full_time", "part_time"):
        role_type = "full_time"
    location = str(item.get("location") or preferences.get("location") or "").strip()
    search_query = str(item.get("search_query") or title).strip()
    try:
        match_score = int(item.get("match_score"))
    except (TypeError, ValueError):
        match_score = 60
    match_score = max(0, min(100, match_score))

    def _as_list(v):
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()][:8]
        if isinstance(v, str) and v.strip():
            return [s.strip() for s in v.split(",") if s.strip()][:8]
        return []

    return {
        "title": title,
        "role_type": role_type,
        "target_companies": str(item.get("target_companies") or "").strip(),
        "location": location,
        "work_mode": str(item.get("work_mode") or preferences.get("work_mode") or "").strip(),
        "match_score": match_score,
        "why_it_fits": str(item.get("why_it_fits") or "").strip(),
        "skills_matched": _as_list(item.get("skills_matched")),
        "skills_to_build": _as_list(item.get("skills_to_build")),
        "search_url": _search_url(search_query, location),
    }


def generate_opportunities(user_id: str, preferences: dict | None = None, limit: int = 6) -> list[dict]:
    """Generate a fresh, profile-matched set of opportunities via the LLM."""
    preferences = preferences or {}
    profile_ctx = profile_as_context_string(user_id)
    profile = load_profile(user_id) or {}

    role_types = preferences.get("role_types") or ["internship", "full_time"]
    role_types_text = ", ".join(ROLE_TYPE_LABELS.get(rt, rt) for rt in role_types) or "Internships and full-time roles"

    pref_lines = [
        f"Preferred location: {preferences.get('location') or 'No strong preference'}",
        f"Opportunity types wanted: {role_types_text}",
        f"Work mode: {preferences.get('work_mode') or 'Any'}",
        f"Preferred industries: {preferences.get('industries') or 'Open'}",
        f"Other notes: {preferences.get('notes') or 'None'}",
    ]

    prompt = f"""You are a career opportunity matcher inside a Career OS.
Suggest {limit} realistic job/internship opportunities that fit THIS user right now, based on their current profile and preferences.
The suggestions must reflect the user's actual current level — do not suggest senior roles to a beginner. As the profile improves, the fit should improve.

━━ USER PROFILE ━━
{profile_ctx or 'No detailed profile yet. Infer from preferences and target role.'}

━━ USER PREFERENCES ━━
{chr(10).join(pref_lines)}

Return ONLY valid JSON in exactly this shape:
{{
  "opportunities": [
    {{
      "title": "specific role title, e.g. Backend Engineering Intern",
      "role_type": "internship | full_time | part_time",
      "target_companies": "the kind of companies to target (e.g. early-stage SaaS startups, mid-size fintech)",
      "location": "city/region honoring the user's preference, or Remote",
      "work_mode": "remote | hybrid | onsite",
      "match_score": 0-100 integer for how well this fits the user NOW,
      "why_it_fits": "1-2 sentences referencing the user's real skills/experience",
      "skills_matched": ["skills the user already has that this needs"],
      "skills_to_build": ["1-3 skills to strengthen to become a stronger candidate"],
      "search_query": "concise job-board search keywords for this role"
    }}
  ]
}}
Rules: honor the preferred location and opportunity types. Order by match_score descending. Be realistic and specific. No text outside the JSON."""

    try:
        data = generate_json(prompt, temperature=0.5)
    except Exception as exc:
        logger.error("opportunity generation failed for %s: %s", user_id, exc)
        return []

    raw_items = []
    if isinstance(data, dict):
        raw_items = data.get("opportunities") or data.get("results") or []
    elif isinstance(data, list):
        raw_items = data

    normalized = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        norm = _normalize(item, preferences)
        if norm:
            normalized.append(norm)

    normalized.sort(key=lambda x: -x["match_score"])
    return normalized[:limit]
