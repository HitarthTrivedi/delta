"""Mock Interview Sandbox — AI interviewer.

Generates a role-appropriate interview flow (opening question -> follow-ups ->
structured feedback), grounded in the user's profile so questions match their
actual target role and experience level. Reuses the same AI service and
profile-context helpers as Agent 2 chat / the Opportunities matcher — no new
model configuration.
"""
from __future__ import annotations

import logging

from app.services.ai_service import generate_response, generate_json
from app.services.profile_store import profile_as_compact_context, load_profile

logger = logging.getLogger("delta.interview_ai")

MAX_QUESTIONS = 6

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
    "technical": "Technical (coding/CS fundamentals)",
    "behavioral": "Behavioral (past experience, teamwork, conflict)",
    "system_design": "System Design",
}


def _role_prompt_block(user_id: str, role_type: str) -> str:
    profile = load_profile(user_id) or {}
    target_role = profile.get("target_role") or profile.get("goal_direction") or "their target role"
    label = ROLE_TYPE_LABELS.get(role_type, "General")
    return f"""You are conducting a {label} mock interview for a candidate targeting: {target_role}.

━━ CANDIDATE PROFILE ━━
{profile_as_compact_context(user_id) or 'No detailed profile yet — ask general questions appropriate to the target role and adjust based on their answers.'}

Interview style: ask ONE question at a time, professional but warm, like a real interviewer. Questions should be appropriately scoped to the candidate's actual experience level shown in their profile — don't ask senior/staff-level questions of a beginner. Follow up on their previous answer when it makes sense (probe deeper, ask for a concrete example) rather than jumping to an unrelated topic every time."""


def generate_opening_question(user_id: str, role_type: str) -> str:
    prompt = f"""{_role_prompt_block(user_id, role_type)}

This is the FIRST question of the interview. Ask an appropriate opening question for this interview type. Return ONLY the question text, no preamble, no "Question 1:", no quotes."""
    try:
        # gemma-4-31b-it spends output tokens on hidden chain-of-thought before
        # the visible answer, so a short question still needs a generous
        # max_tokens budget — too small silently yields empty text.
        text = generate_response(prompt, temperature=0.7, max_tokens=3000)
        question = text.strip().strip('"')
        if not question or _is_mock_fallback(question):
            return "Tell me about yourself and what draws you to this role."
        return question
    except Exception as exc:
        logger.error(f"opening question generation failed: {exc}")
        return "Tell me about yourself and what draws you to this role."


def generate_next_question(user_id: str, role_type: str, transcript: list[dict], question_count: int) -> dict:
    """Returns {"question": str | None, "done": bool}. Done after MAX_QUESTIONS."""
    if question_count >= MAX_QUESTIONS:
        return {"question": None, "done": True}

    convo = "\n".join(f"{turn['role'].upper()}: {turn['content']}" for turn in transcript)
    prompt = f"""{_role_prompt_block(user_id, role_type)}

━━ INTERVIEW SO FAR ━━
{convo}

This is question {question_count + 1} of {MAX_QUESTIONS}. Based on the candidate's last answer, ask the next question — either a natural follow-up probing deeper, or a new question covering a different relevant area if the previous topic is exhausted. Return ONLY the question text, no preamble, no numbering, no quotes."""
    try:
        text = generate_response(prompt, temperature=0.7, max_tokens=3000)
        question = text.strip().strip('"')
        if not question or _is_mock_fallback(question):
            return {"question": "Can you walk me through your reasoning on that?", "done": False}
        return {"question": question, "done": False}
    except Exception as exc:
        logger.error(f"next question generation failed: {exc}")
        return {"question": "Can you walk me through your reasoning on that?", "done": False}


def generate_feedback(user_id: str, role_type: str, transcript: list[dict]) -> dict:
    convo = "\n".join(f"{turn['role'].upper()}: {turn['content']}" for turn in transcript)
    label = ROLE_TYPE_LABELS.get(role_type, "General")
    prompt = f"""You just finished conducting a {label} mock interview. Evaluate the candidate's performance honestly and constructively.

━━ FULL TRANSCRIPT ━━
{convo}

Return ONLY valid JSON in exactly this shape:
{{
  "overall_score": 0-100 integer,
  "strengths": ["specific strength referencing what they actually said", "..."],
  "improvements": ["specific, actionable improvement", "..."],
  "per_question_feedback": [
    {{"question": "the interviewer question", "feedback": "1-2 sentences on this specific answer"}}
  ]
}}
Rules: be honest, not just encouraging — if answers were vague or shallow, say so and explain what a stronger answer would include. Base every point on what was actually said, not generic advice. No text outside the JSON."""
    try:
        data = generate_json(prompt, temperature=0.4, max_tokens=2000)
    except Exception as exc:
        logger.error(f"feedback generation failed: {exc}")
        data = {}

    if not isinstance(data, dict) or "overall_score" not in data:
        data = {
            "overall_score": 50,
            "strengths": ["You completed the interview — that's the hardest part of starting."],
            "improvements": ["Feedback generation hit an issue this time — try finishing another mock interview for a full report."],
            "per_question_feedback": [],
        }

    try:
        data["overall_score"] = max(0, min(100, int(data.get("overall_score", 50))))
    except (TypeError, ValueError):
        data["overall_score"] = 50
    data["strengths"] = data.get("strengths") or []
    data["improvements"] = data.get("improvements") or []
    data["per_question_feedback"] = data.get("per_question_feedback") or []
    return data
