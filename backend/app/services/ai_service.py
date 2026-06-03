"""
AI Service — unified LLM client for all Delta agents.
Uses google-genai SDK (new API style) with gemma-4-31b-it.
Falls back gracefully if the key or model is unavailable.
"""

import os
import json
import re
import logging

logger = logging.getLogger("delta.ai_service")

# ─── lazy-initialise the google-genai client ───────────────────────────────
_genai_client = None

def _get_client():
    global _genai_client
    if _genai_client is not None:
        return _genai_client
    try:
        from google import genai
        from app.config import settings
        key = (settings.GEMINI_API_KEY or "").strip().strip('"').strip("'")
        if key and not key.startswith("your_"):
            _genai_client = genai.Client(api_key=key)
            logger.info("google-genai client initialised")
        else:
            logger.warning("GEMINI_API_KEY not set — AI calls will use mock fallback")
    except Exception as e:
        logger.warning(f"Failed to init google-genai client: {e}")
    return _genai_client


MODEL = "gemma-4-31b-it"


def generate_response(prompt: str, temperature: float = 0.7, max_tokens: int = 10000) -> str:
    """
    Send a prompt to gemma-4-31b-it and return the response text.
    """
    print(f"\n=================== [LLM REQUEST - {MODEL}] ===================")
    print(f"Temp: {temperature} | Max Tokens: {max_tokens}")
    print(f"Prompt preview (last 300 chars):\n...{prompt[-300:] if len(prompt) > 300 else prompt}")
    print(f"===========================================================")
    
    client = _get_client()
    if client:
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            text = response.text
            if text:
                print(f"\n=================== [LLM RESPONSE SUCCESS] ===================")
                print(f"Length: {len(text)} chars | Model: {MODEL}")
                print(f"Response preview:\n{text[:250]}...")
                print(f"==============================================================")
                return text.strip()
        except Exception as e:
            print(f"\n❌ [LLM RESPONSE ERROR] Model {MODEL} call failed: {e}")
            import traceback
            traceback.print_exc()
            print(f"==============================================================")

    logger.warning("API unavailable — using mock fallback")
    return _mock_structured_response(prompt)


def generate_json(prompt: str, temperature: float = 0.3) -> dict | list:
    """
    Generate a JSON response. Strips markdown fences and parses automatically.
    """
    raw = generate_response(prompt, temperature=temperature)
    
    # Strip markdown fences
    clean_raw = raw
    if "```json" in clean_raw:
        clean_raw = clean_raw.split("```json")[1].split("```")[0]
    elif "```" in clean_raw:
        clean_raw = clean_raw.split("```")[1].split("```")[0]
    clean_raw = clean_raw.strip()
    
    try:
        parsed = json.loads(clean_raw)
        print(f"\n✅ [JSON PARSER SUCCESS] Successfully parsed raw response into structure: {type(parsed)}")
        return parsed
    except Exception as e:
        print(f"\n❌ [JSON PARSER ERROR] Failed to parse JSON: {e}")
        print(f"Raw response content that failed parsing:\n{raw}")
        print(f"==============================================================")
        return {}


# ─── Mock fallback (used when API key is missing / quota exceeded) ──────────

def _mock_structured_response(prompt: str) -> str:
    prompt_lower = prompt.lower()

    # Onboarding opening
    if "intake agent" in prompt_lower or "opening question" in prompt_lower or "welcome them" in prompt_lower:
        return (
            "Hi! I'm your Delta AI advisor. I'm here to build your personalized career roadmap. "
            "Let's start simple — what's your name, and what field or role are you working toward?"
        )

    # Next question fallback (MUST come before profile extraction fallback to prevent false matches on 'extract' in prompt context)
    if "missing fields:" in prompt_lower or "follow-up question" in prompt_lower or "intake advisor" in prompt_lower:
        if "hours_per_week" in prompt_lower or "hours" in prompt_lower:
            return "How many hours per week do you think you can dedicate to this learning path? I want to make sure the pace is just right for you!"
        elif "planning_horizon" in prompt_lower:
            return "What is your target timeline or planning horizon for these career goals? Are we looking at the next year, or a longer-term plan?"
        elif "relocation" in prompt_lower:
            return "Are you open to relocation, or do you prefer to look for remote and local opportunities?"
        elif "study_year" in prompt_lower:
            return "Could you tell me what year of study you are currently in, or if you've already graduated?"
        elif "university" in prompt_lower or "college" in prompt_lower:
            return "Which college or university do you attend? I'd love to know where you are studying!"
        return "Could you tell me a little more about your target career timeline and how many hours you can dedicate each week?"

    # Profile extraction
    if "extract" in prompt_lower and ("name" in prompt_lower or "target_role" in prompt_lower):
        return json.dumps({})

    # Roadmap generation
    if "roadmap" in prompt_lower and "phases" in prompt_lower:
        return json.dumps({
            "phases": [
                {
                    "id": "phase_1",
                    "name": "Foundation",
                    "description": "Build your core fundamentals",
                    "duration_weeks": 4,
                    "nodes": [
                        {"id": "n1", "label": "Core Skills Assessment", "status": "in_progress",
                         "description": "Identify and document your current skill level"},
                        {"id": "n2", "label": "First Project", "status": "locked",
                         "description": "Build a small proof-of-concept project"}
                    ]
                }
            ],
            "active_phase_id": "phase_1"
        })

    # Weekly brief
    if "weekly" in prompt_lower and "brief" in prompt_lower:
        return json.dumps({
            "delta_score_start": 20,
            "delta_score_end": 22,
            "track_status": "on_track",
            "actions": ["Complete one small project this week", "Review fundamentals"],
            "market_changes": ["AI tools are increasingly expected in job descriptions"],
            "personal_changes": ["You've shown consistent effort"],
            "opportunities": ["Apply to entry-level roles matching your profile"],
            "questions_for_user": ["What specific skill do you want to master first?"]
        })

    # Encouragement / completion
    if "inspiring" in prompt_lower or "onboarding wrap" in prompt_lower or "welcome them officially" in prompt_lower:
        return (
            "Welcome to Delta Career OS! Your profile has been compiled. "
            "Your top immediate focus should be building your first proof project "
            "and strengthening your core technical skills. "
            "Head to your dashboard to see your personalized roadmap!"
        )

    # Generic chat
    return "I'm here to help with your career journey. Tell me more about your goals or current progress."
