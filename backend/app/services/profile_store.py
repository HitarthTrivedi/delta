"""
Profile Store — the single source of truth for all Delta agents.

Every agent (intake, roadmap, brief, dossier) reads and writes through this module.
Profiles are stored as JSON files at:
    <project_root>/data/profiles/<user_id>.json

Schema (all fields optional — partial updates are safe):
    {
      "user_id": str,
      "personal_introduction": str,
      "backstory": str,
      "transition_reason": str,
      "name": str,
      "email": str,
      "target_role": str,
      "target_exam": str,
      "target_attempt": str,
      "exam_goal_detail": str,
      "known_exam_dates": [str],
      "current_role": str,
      "education": str,           # e.g. "B.Tech CSE, 2nd year"
      "university": str,
      "location": str,
      "hours_per_week": int,
      "learning_style": str,      # "practical" | "theoretical" | "mixed"
      "skills": [str],
      "skill_depths": {str: str}, # {"Python": "intermediate", ...}
      "career_goals": [str],
      "short_term_targets": [str],
      "constraints": [str],
      "resume_text": str,         # raw extracted resume text
      "projects": [str],
      "certificates": [str],
      "study_pattern": str,
      "timeline_months": int,
      "planning_horizon_months": int,
      "inferred_planning_reason": str,
      "detected_goal_track": str,
      "agent1_search_sources": [dict],
      "confidence_score": float,
      "onboarding_complete": bool,
      "last_updated": str         # ISO timestamp
    }
"""

import json
import pathlib
import datetime
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("delta.profile_store")

# Profile directory: Delta/data/profiles/
_PROFILES_DIR = pathlib.Path(__file__).resolve().parents[3] / "data" / "profiles"


def _profile_path(user_id: str) -> pathlib.Path:
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return _PROFILES_DIR / f"{user_id}.json"


def load_profile(user_id: str) -> Dict[str, Any]:
    """Load a user profile from disk. Returns {} if not found."""
    path = _profile_path(user_id)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load profile {user_id}: {e}")
        return {}


def save_profile(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge `data` into the existing profile and persist to disk.
    Returns the merged profile.
    """
    existing = load_profile(user_id)
    merged = {**existing, **data}
    merged["user_id"] = user_id
    merged["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"

    path = _profile_path(user_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        logger.info(f"Profile saved → {path}")
    except Exception as e:
        logger.error(f"Failed to save profile {user_id}: {e}")

    return merged


def profile_exists(user_id: str) -> bool:
    """Returns True if a profile file exists for the user."""
    return _profile_path(user_id).exists()


def get_field(user_id: str, field: str, default=None):
    """Convenience helper to read a single field."""
    return load_profile(user_id).get(field, default)


def mark_onboarding_complete(user_id: str):
    """Mark that onboarding has been completed."""
    save_profile(user_id, {"onboarding_complete": True})


def profile_as_context_string(user_id: str) -> str:
    """
    Return a flat, human-readable text block of the profile —
    suitable for injecting directly into an AI prompt as context.
    Returns empty string if no profile exists.
    """
    p = load_profile(user_id)
    if not p:
        return ""

    lines = [
        f"Name: {p.get('name', 'Unknown')}",
        f"Email: {p.get('email', '')}",
        f"Personal introduction / backstory: {p.get('personal_introduction') or p.get('backstory') or 'Not specified'}",
        f"Transition reason: {p.get('transition_reason', 'Not specified')}",
        f"Target Role: {p.get('target_role', 'Not specified')}",
        f"Detected goal/exam track: {p.get('detected_goal_track') or p.get('target_exam') or 'Not specified'}",
        f"Target attempt/intake/date: {p.get('target_attempt', 'Not specified')}",
        f"Exam/goal detail: {p.get('exam_goal_detail', 'Not specified')}",
        f"Known exam dates: {', '.join(p.get('known_exam_dates', [])) if isinstance(p.get('known_exam_dates'), list) else p.get('known_exam_dates', 'None')}",
        f"Education Major: {p.get('major', 'Not specified')}",
        f"University/College: {p.get('university', 'Not specified')}",
        f"Year of study: {p.get('study_year', 'Not specified')}",
        f"GPA: {p.get('gpa', 'Not specified')}",
        f"Experience Level: {p.get('experience_level', 'beginner')}",
        f"Past experience description: {p.get('past_experience', 'Not specified')}",
        f"Hours/week available: {p.get('hours_per_week', 10)}",
        f"Preferred learning style: {p.get('learning_style', 'practical')}",
        f"Preferred Content Types: {', '.join(p.get('preferred_content_types', [])) if isinstance(p.get('preferred_content_types'), list) else p.get('preferred_content_types', 'Not specified')}",
        f"Target Industries: {', '.join(p.get('target_industries', [])) if isinstance(p.get('target_industries'), list) else p.get('target_industries', 'Not specified')}",
        f"Skills Inventory: {', '.join(p.get('skills', [])) if isinstance(p.get('skills'), list) else p.get('skills', 'None listed')}",
        f"Career aspirations / goals: {'; '.join(p.get('career_goals', [])) if isinstance(p.get('career_goals'), list) else p.get('career_goals', 'Not specified')}",
        f"Relocation openness / goals: {p.get('relocation', 'Not specified')}",
        f"Extracurricular interests: {', '.join(p.get('extracurricular_interests', [])) if isinstance(p.get('extracurricular_interests'), list) else p.get('extracurricular_interests', 'None')}",
        f"Planning horizon years: {p.get('planning_horizon_years', 1)}",
        f"Planning horizon months: {p.get('planning_horizon_months', 'Not specified')}",
        f"Planning horizon reason: {p.get('inferred_planning_reason', 'Not specified')}",
        f"Phone number: {p.get('phone_number', '')}",
        f"LinkedIn URL: {p.get('linkedin_url', '')}",
        f"GitHub URL: {p.get('github_url', '')}",
        f"Portfolio URL: {p.get('portfolio_url', '')}",
    ]
    sources = p.get("agent1_search_sources") or []
    if sources:
        lines.append("\nAgent 1 search enrichment sources:")
        for source in sources[:5]:
            lines.append(f"- {source.get('title', 'Source')}: {source.get('url', '')}")
    if p.get("resume_text"):
        lines.append(f"\n--- Resume Extract ---\n{p['resume_text'][:2000]}\n--- End Resume ---")
    return "\n".join(lines)
