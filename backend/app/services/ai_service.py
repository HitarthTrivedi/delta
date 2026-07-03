"""
AI Service — unified LLM client for all delta agents.
Uses google-genai SDK with Gemini. Supports up to 5 API keys in round-robin
rotation — on quota exhaustion (429) it immediately retries with the next key.
"""

import os
import json
import re
import logging
import itertools

logger = logging.getLogger("delta.ai_service")

# ─── Key rotation pool ────────────────────────────────────────────────────────
_clients: list = []          # list of google.genai.Client objects
_client_cycle = None         # itertools.cycle over _clients
_clients_initialised = False


def _build_clients():
    global _clients, _client_cycle, _clients_initialised
    if _clients_initialised:
        return
    _clients_initialised = True
    try:
        from google import genai
        from app.config import settings
        raw_keys = [
            settings.GEMINI_API_KEY,
            settings.GEMINI_API_KEY_2,
            settings.GEMINI_API_KEY_3,
            settings.GEMINI_API_KEY_4,
            settings.GEMINI_API_KEY_5,
        ]
        keys = [k.strip().strip('"').strip("'") for k in raw_keys if k and not k.strip().startswith("your_")]
        if not keys:
            logger.warning("No valid GEMINI_API_KEY found — AI calls will use mock fallback")
            return
        for key in keys:
            try:
                # timeout is in MILLISECONDS. 120000ms = 120s gives the model
                # enough time for long responses and avoids Google's internal deadline.
                _clients.append(genai.Client(api_key=key, http_options={"timeout": 120000}))
            except Exception as e:
                logger.warning(f"Failed to init genai client for a key: {e}")
        if _clients:
            _client_cycle = itertools.cycle(_clients)
            logger.info(f"google-genai initialised with {len(_clients)} API key(s)")
    except Exception as e:
        logger.warning(f"Failed to init google-genai: {e}")


def _next_client():
    _build_clients()
    if not _client_cycle:
        return None
    return next(_client_cycle)


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_response(prompt: str, temperature: float = 0.7, max_tokens: int = 10000, model: str | None = None) -> str:
    """
    Send a prompt to Gemini and return the response text.
    Retries across all available API keys on 429/quota errors before failing.
    `model` overrides the globally configured GEMINI_MODEL for this call.
    """
    _build_clients()
    if not model:
        try:
            from app.config import settings
            model = settings.GEMINI_MODEL or "gemma-4-31b-it"
        except Exception:
            model = "gemma-4-31b-it"

    logger.info(f"[LLM] {model} | temp={temperature} | tokens={max_tokens} | prompt_len={len(prompt)}")

    if not _clients:
        logger.warning("No API clients available — using mock fallback")
        return _mock_structured_response(prompt)

    last_error = None
    # Try every client once before giving up
    for _ in range(len(_clients)):
        client = _next_client()
        if client is None:
            break
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            text = response.text
            if text:
                logger.info(f"[LLM] success | response_len={len(text)}")
                return text.strip()
        except Exception as e:
            err_str = str(e).lower()
            last_error = e
            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "rate" in err_str or "504" in err_str or "deadline" in err_str or "unavailable" in err_str:
                logger.warning(f"[LLM] retryable error on key, rotating: {type(e).__name__}: {str(e)[:120]}")
                continue  # try next key
            # Non-quota error — raise immediately
            logger.error(f"[LLM] non-quota error: {e}")
            raise ValueError("The tasks are not being loaded right now. Can you please try again some time later?")

    if last_error:
        logger.error(f"[LLM] All {len(_clients)} keys exhausted. Last error: {last_error}")
        raise ValueError("All API quota limits reached. Please try again in a few minutes.")

    return _mock_structured_response(prompt)


def generate_response_stream(prompt: str, temperature: float = 0.7, max_tokens: int = 10000, model: str | None = None):
    """Stream a Gemini response as text chunks (generator).

    Mirrors generate_response's key rotation. If streaming yields nothing or
    fails before any output, falls back to a single non-streaming reply so the
    caller always gets an answer. Never raises — the chat must not break.
    """
    _build_clients()
    if not model:
        try:
            from app.config import settings
            model = settings.GEMINI_MODEL or "gemma-4-31b-it"
        except Exception:
            model = "gemma-4-31b-it"

    logger.info(f"[LLM stream] {model} | temp={temperature} | tokens={max_tokens} | prompt_len={len(prompt)}")

    if not _clients:
        yield _mock_structured_response(prompt)
        return

    last_error = None
    for _ in range(len(_clients)):
        client = _next_client()
        if client is None:
            break
        got = False
        try:
            stream = client.models.generate_content_stream(
                model=model,
                contents=prompt,
                config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            for chunk in stream:
                text = getattr(chunk, "text", None)
                if text:
                    got = True
                    yield text
            if got:
                return
            # produced no text — try the next key
        except Exception as e:
            last_error = e
            if got:
                # already streamed partial content; stop rather than duplicate
                logger.error(f"[LLM stream] error after partial output: {e}")
                return
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "rate" in err_str:
                logger.warning(f"[LLM stream] quota hit, rotating key: {type(e).__name__}")
                continue
            logger.error(f"[LLM stream] non-quota error: {e}")
            break

    # Nothing streamed — fall back to a single non-streaming reply.
    logger.warning(f"[LLM stream] falling back to non-streaming reply. last_error={last_error}")
    try:
        yield generate_response(prompt, temperature=temperature, max_tokens=max_tokens, model=model)
    except Exception:
        yield _mock_structured_response(prompt)


_LATEX_ARROWS = {
    r"\rightarrow": "→", r"\to": "→", r"\Rightarrow": "⇒",
    r"\longrightarrow": "→", r"\leftarrow": "←", r"\Leftarrow": "⇐",
}


def sanitize_llm_json_text(text: str) -> str:
    """
    Models occasionally write LaTeX (e.g. "$\\rightarrow$") inside plain JSON
    string fields without doubling the backslash. json.loads then silently
    treats "\r" / "\t" as real control-char escapes, swallowing the backslash
    and the next letter (turning "\rightarrow" into "ightarrow"). Normalize
    common arrow macros to unicode first, then double any remaining backslash
    that precedes 2+ letters — never a valid single-char JSON escape — so it
    round-trips as literal text instead of corrupting the string.
    """
    for macro, symbol in _LATEX_ARROWS.items():
        text = text.replace(f"${macro}$", symbol).replace(macro, symbol)
    return re.sub(r"\\(?=[A-Za-z]{2,})", r"\\\\", text)


def generate_json(prompt: str, temperature: float = 0.3, model: str | None = None) -> dict | list:
    """
    Generate a JSON response. Strips markdown fences and parses automatically.
    """
    raw = generate_response(prompt, temperature=temperature, model=model)

    clean = raw
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0]
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0]
    clean = sanitize_llm_json_text(clean.strip())

    try:
        return json.loads(clean)
    except Exception as e:
        logger.warning(f"[JSON] parse failed: {e} | raw[:200]={raw[:200]}")
        return {}


# ─── Mock fallback (used when all keys are missing or exhausted) ──────────────

def _mock_structured_response(prompt: str) -> str:
    prompt_lower = prompt.lower()

    if "agent 2 weekly plan discussion" in prompt_lower or "you are agent 2 inside delta career os" in prompt_lower:
        if "resume" in prompt_lower or "skills" in prompt_lower:
            return (
                "This week's work should become a proof signal, not just a learning note. "
                "Skills you can show: evaluation design, reliability testing, adversarial testing, documentation, and project communication. "
                "Resume format: Built a small proof project that tested an agent workflow with realistic prompts, documented failure cases, and added one improvement based on results."
            )
        if "asked something else" in prompt_lower or "misunderstood" in prompt_lower:
            return "You are right. I misunderstood the intent. I will answer the question directly without changing this week's tasks."
        return (
            "For this week's task, focus on one small proof: define the goal, build or test it, record results, and write what improved. "
            "If you want, ask me for exact steps or resume wording."
        )

    if "intake agent" in prompt_lower or "opening question" in prompt_lower or "welcome them" in prompt_lower:
        return (
            "Hi! I'm your delta AI advisor. I'm here to build your personalized career roadmap. "
            "Let's start simple — what's your name, and what field or role are you working toward?"
        )

    if "missing fields:" in prompt_lower or "follow-up question" in prompt_lower or "intake advisor" in prompt_lower:
        if "hours_per_week" in prompt_lower or "hours" in prompt_lower:
            return "How many hours per week do you think you can dedicate to this learning path?"
        elif "planning_horizon" in prompt_lower:
            return "What is your target timeline for these career goals?"
        elif "relocation" in prompt_lower:
            return "Are you open to relocation, or do you prefer remote and local opportunities?"
        elif "study_year" in prompt_lower:
            return "What year of study are you currently in, or have you already graduated?"
        elif "university" in prompt_lower or "college" in prompt_lower:
            return "Which college or university do you attend?"
        return "Could you tell me a little more about your target career timeline and available weekly hours?"

    if "extract" in prompt_lower and ("name" in prompt_lower or "target_role" in prompt_lower):
        return json.dumps({})

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

    if "inspiring" in prompt_lower or "onboarding wrap" in prompt_lower or "welcome them officially" in prompt_lower:
        return (
            "Welcome to delta Career OS! Your profile has been compiled. "
            "Your top immediate focus should be building your first proof project "
            "and strengthening your core technical skills. "
            "Head to your dashboard to see your personalized roadmap!"
        )

    return "I'm here to help with your career journey. Tell me more about your goals or current progress."
