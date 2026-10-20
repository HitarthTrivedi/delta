"""Mock Interview Sandbox — AI interviewer.

Generates a role-appropriate interview flow (opening question -> follow-ups ->
structured feedback), grounded in the user's profile so questions match their
actual target role and experience level. Reuses the same AI service and
profile-context helpers as Agent 2 chat / the Opportunities matcher — no new
model configuration.

Questions are spoken aloud by the video interviewer, so they are kept short
and conversational. The feedback report is evidence recruiters may read, so
if it can't be generated we raise rather than invent a score.
"""
from __future__ import annotations

import logging

from app.services.ai_service import generate_response, generate_json
from app.services.profile_store import profile_as_compact_context, load_profile
from app.services.domain_packs import resolve_field, get_domain_pack

logger = logging.getLogger("delta.interview_ai")

DEFAULT_QUESTIONS = 6
MIN_QUESTIONS, MAX_QUESTIONS = 3, 10

# ai_service.generate_response falls back to a generic onboarding mock string
# when the model returns no usable text (rare, but observed — the reasoning
# model occasionally spends its whole token budget on hidden chain-of-thought).
# That fallback text is wrong-context for an interview, so detect and swap it
# for an interview-appropriate line instead of showing it to the candidate.
_MOCK_FALLBACK_MARKERS = ("delta ai advisor", "career roadmap", "career journey")


def _is_mock_fallback(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _MOCK_FALLBACK_MARKERS)


ROLE_TYPE_LABELS = {
    "technical": "Role knowledge (the core concepts, tools and practice of the candidate's field)",
    "behavioral": "Behavioral (past experience, teamwork, conflict)",
    "case": "Case / scenario (a realistic situation from the field to work through)",
    "system_design": "System Design",
}

DIFFICULTY_LABELS = {
    "entry": "entry level (intern / fresher): fundamentals, clear and fair",
    "intermediate": "intermediate (1-3 years): applied understanding and trade-offs",
    "advanced": "advanced (senior): depth, edge cases, design trade-offs and leadership",
}

RUBRIC_KEYS = ("communication", "technical_depth", "problem_solving", "clarity")
VERDICTS = ("strong", "ready", "almost", "not_yet")


class FeedbackUnavailable(Exception):
    """The report could not be generated; the caller must not invent one."""


def normalize_settings(role_type: str, target_role: str | None, difficulty: str | None,
                       num_questions: int | None, user_id: str) -> dict:
    profile = load_profile(user_id) or {}
    try:
        n = int(num_questions or DEFAULT_QUESTIONS)
    except (TypeError, ValueError):
        n = DEFAULT_QUESTIONS
    target = (target_role or "").strip()[:120] or profile.get("target_role") or profile.get("goal_direction") or ""
    pack = resolve_field({**profile, "target_role": target or profile.get("target_role")})
    return {
        "role_type": role_type if role_type in ROLE_TYPE_LABELS else "technical",
        "target_role": target or "their target role",
        "difficulty": difficulty if difficulty in DIFFICULTY_LABELS else "entry",
        "num_questions": max(MIN_QUESTIONS, min(MAX_QUESTIONS, n)),
        "field": pack["id"],
        "field_label": pack["label"],
    }


def _field_guidance(settings: dict) -> str:
    """How this round should look in the candidate's field."""
    pack = get_domain_pack(settings.get("field") or "general")
    role_type = settings["role_type"]
    if role_type == "technical":
        if pack["is_tech"]:
            return "Ask about CS fundamentals, coding concepts and the candidate's projects."
        return (f"Ask about the core knowledge and practice of {pack['label']} (not software or coding), "
                f"e.g. {', '.join(pack['skill_taxonomy'][:4])}.")
    if role_type == "case":
        return (f"Run this as the kind of scenario round used in {pack['label']}: {'; '.join(pack['interview_formats'])}. "
                "Present one realistic situation, let the candidate reason through it, and probe their decisions.")
    return ""


def _role_prompt_block(user_id: str, settings: dict) -> str:
    label = ROLE_TYPE_LABELS.get(settings["role_type"], "General")
    level = DIFFICULTY_LABELS.get(settings["difficulty"], DIFFICULTY_LABELS["entry"])
    field_line = f"\nThe candidate's field is {settings.get('field_label') or 'not specified'}. {_field_guidance(settings)}"
    return f"""You are Aria, an experienced interviewer conducting a {label} mock interview for a candidate targeting: {settings["target_role"]}.
Pitch the questions at: {level}.{field_line}

━━ CANDIDATE PROFILE ━━
{profile_as_compact_context(user_id) or 'No detailed profile yet — ask general questions appropriate to the target role and adjust based on their answers.'}

Interview style: ask ONE question at a time, professional but warm, like a real interviewer on a video call. Your words are SPOKEN ALOUD, so keep each turn under 45 words, conversational, with no markdown, bullet points, code blocks or symbols. Follow up on their previous answer when it makes sense (probe deeper, ask for a concrete example) rather than jumping to an unrelated topic every time."""


def _clean_spoken(text: str) -> str:
    return (text or "").strip().strip('"').replace("*", "").replace("`", "")


def generate_opening_question(user_id: str, settings: dict) -> str:
    prompt = f"""{_role_prompt_block(user_id, settings)}

This is the FIRST question. Greet the candidate in one short sentence (you are Aria), then ask an appropriate opening question for this interview type. Return ONLY what you would say, no labels, no quotes."""
    fallback = f"Hi, I'm Aria, and I'll be your interviewer today. To start, tell me about yourself and what draws you to the {settings['target_role']} role."
    try:
        # Gemini 2.5 models spend output tokens on hidden thinking before the
        # visible answer, so a short question still needs a generous
        # max_tokens budget — too small silently yields empty text.
        question = _clean_spoken(generate_response(prompt, temperature=0.7, max_tokens=3000))
        if not question or _is_mock_fallback(question):
            return fallback
        return question
    except Exception as exc:
        logger.error(f"opening question generation failed: {exc}")
        return fallback


def generate_next_question(user_id: str, settings: dict, transcript: list[dict], question_count: int) -> dict:
    """Returns {"question": str | None, "done": bool}. Done after num_questions."""
    total = settings["num_questions"]
    if question_count >= total:
        return {"question": None, "done": True}

    convo = "\n".join(f"{turn['role'].upper()}: {turn['content']}" for turn in transcript)
    last = question_count + 1 == total
    prompt = f"""{_role_prompt_block(user_id, settings)}

━━ INTERVIEW SO FAR ━━
{convo}

This is question {question_count + 1} of {total}{" (the LAST one)" if last else ""}. React to the candidate's last answer in at most one short sentence (genuine, not gushing), then ask the next question: either a natural follow-up probing deeper, or a new relevant area if the topic is exhausted. Return ONLY what you would say, no labels, no quotes."""
    fallback = "Can you walk me through your reasoning on that, with a concrete example?"
    try:
        question = _clean_spoken(generate_response(prompt, temperature=0.7, max_tokens=3000))
        if not question or _is_mock_fallback(question):
            return {"question": fallback, "done": False}
        return {"question": question, "done": False}
    except Exception as exc:
        logger.error(f"next question generation failed: {exc}")
        return {"question": fallback, "done": False}


def _clamp(value, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def generate_feedback(user_id: str, settings: dict, transcript: list[dict]) -> dict:
    """Structured, evidence-based report. Raises FeedbackUnavailable on failure."""
    convo = "\n".join(f"{turn['role'].upper()}: {turn['content']}" for turn in transcript)
    label = ROLE_TYPE_LABELS.get(settings["role_type"], "General")
    prompt = f"""You just conducted a {label} mock interview for a {settings["target_role"]} candidate (field: {settings.get("field_label") or "not specified"}), pitched at {DIFFICULTY_LABELS.get(settings["difficulty"])}. Evaluate the candidate honestly and constructively. "technical_depth" means depth of subject knowledge in THEIR field (clinical, legal, financial, engineering, etc.), not coding unless the field is software. Answers may come from speech-to-text, so ignore small transcription errors and filler words.

━━ FULL TRANSCRIPT ━━
{convo}

Return ONLY valid JSON in exactly this shape:
{{
  "overall_score": 0-100 integer,
  "verdict": "strong" | "ready" | "almost" | "not_yet",
  "summary": "2-3 sentences: how the candidate came across overall",
  "rubric": {{
    "communication": {{"score": 0-10, "comment": "one sentence"}},
    "technical_depth": {{"score": 0-10, "comment": "one sentence"}},
    "problem_solving": {{"score": 0-10, "comment": "one sentence"}},
    "clarity": {{"score": 0-10, "comment": "one sentence"}}
  }},
  "per_question": [
    {{"question": "the interviewer question", "answer_excerpt": "short quote or paraphrase of what they said", "score": 0-10, "feedback": "1-2 sentences on this answer", "model_answer": "2-4 sentences: what a strong answer would cover"}}
  ],
  "strengths": ["specific strength referencing what they actually said"],
  "improvements": ["specific, actionable improvement"]
}}
Rules: be honest, not just encouraging. If answers were vague, missing or shallow, score them low and say what a stronger answer includes. Unanswered questions score 0. Base every point on what was actually said. One per_question entry per interviewer question that the candidate answered. No text outside the JSON."""
    try:
        data = generate_json(prompt, temperature=0.3, max_tokens=5000)
    except Exception as exc:
        logger.error(f"feedback generation failed: {exc}")
        raise FeedbackUnavailable() from exc

    if not isinstance(data, dict) or "overall_score" not in data:
        raise FeedbackUnavailable()

    rubric_in = data.get("rubric") if isinstance(data.get("rubric"), dict) else {}
    rubric = {}
    for key in RUBRIC_KEYS:
        item = rubric_in.get(key) if isinstance(rubric_in.get(key), dict) else {}
        rubric[key] = {"score": _clamp(item.get("score"), 0, 10, 0), "comment": str(item.get("comment") or "").strip()}

    per_question = []
    for q in data.get("per_question") or data.get("per_question_feedback") or []:
        if not isinstance(q, dict) or not q.get("question"):
            continue
        per_question.append({
            "question": str(q.get("question")).strip(),
            "answer_excerpt": str(q.get("answer_excerpt") or "").strip(),
            "score": _clamp(q.get("score"), 0, 10, 0),
            "feedback": str(q.get("feedback") or "").strip(),
            "model_answer": str(q.get("model_answer") or "").strip(),
        })

    verdict = data.get("verdict") if data.get("verdict") in VERDICTS else None
    overall = _clamp(data.get("overall_score"), 0, 100, 0)
    if not verdict:
        verdict = "strong" if overall >= 85 else "ready" if overall >= 70 else "almost" if overall >= 50 else "not_yet"

    return {
        "overall_score": overall,
        "verdict": verdict,
        "summary": str(data.get("summary") or "").strip(),
        "rubric": rubric,
        "per_question": per_question,
        "strengths": [str(s) for s in (data.get("strengths") or []) if s],
        "improvements": [str(s) for s in (data.get("improvements") or []) if s],
    }
