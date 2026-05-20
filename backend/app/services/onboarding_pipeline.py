"""Onboarding pipeline — processes user intake data."""

def process_onboarding(user_data: dict, chat_history: list) -> dict:
    """Process onboarding conversation into structured profile."""
    return {
        "ambitions": user_data.get("target_role", ""),
        "current_level": user_data.get("current_role", "student"),
        "time_commitment": user_data.get("hours_per_week", 10),
        "learning_style": user_data.get("learning_style", "hands-on"),
        "extracted_skills": [],
        "status": "processed",
    }
