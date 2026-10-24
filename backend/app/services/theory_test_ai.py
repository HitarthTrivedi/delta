"""Technical Theory Test — AI-generated MCQ tests.

Generates a multiple-choice test on a topic (or the user's target role when no
topic is given), grounded in the user's profile so difficulty matches their
level. Each question is tagged with the skill it tests, so a completed test
yields a per-skill breakdown recruiters can read later. Grading happens in the
router against the stored answer key — the model never grades.
"""
from __future__ import annotations

import logging

from app.services.ai_service import generate_json
from app.services.profile_store import profile_as_compact_context, load_profile

logger = logging.getLogger("delta.theory_test_ai")

MIN_QUESTIONS = 5
MAX_QUESTIONS = 20

DIFFICULTIES = {
    "easy": "EASY: core definitions applied to simple cases; a well-prepared beginner should get most right",
    "medium": "MEDIUM: applied understanding, typical interview-screen level",
    "hard": "HARD: tricky edge cases, multi-step reasoning and trade-offs; strong candidates only",
}
APTITUDE_AREAS = {
    "quantitative": "Quantitative aptitude: percentages, ratios, profit and loss, time and work, speed-distance-time, averages, simple and compound interest, number series",
    "logical": "Logical reasoning: syllogisms, seating arrangements, blood relations, coding-decoding, direction sense, puzzles, data sufficiency",
    "verbal": "Verbal ability: reading comprehension (short passages), sentence correction, synonyms and antonyms, para-jumbles, fill in the blanks",
}


def _valid_question(q) -> bool:
    if not isinstance(q, dict):
        return False
    options = q.get("options")
    if not isinstance(q.get("question"), str) or not q["question"].strip():
        return False
    if not isinstance(options, list) or len(options) != 4 or not all(isinstance(o, str) and o.strip() for o in options):
        return False
    idx = q.get("answer_index")
    return isinstance(idx, int) and not isinstance(idx, bool) and 0 <= idx < 4


def generate_test(user_id: str, topic: str | None, num_questions: int = 10, difficulty: str = "medium",
                  category: str = "technical", area: str | None = None, personalize: bool = True) -> tuple[str, list[dict]]:
    """Returns (topic, questions). Raises ValueError if the model output is
    unusable — callers must not substitute placeholder questions.

    personalize=False leaves the learner's profile out of the prompt, for
    questions stored in the shared practice bank and reused by everyone."""
    difficulty = difficulty if difficulty in DIFFICULTIES else "medium"
    if category == "aptitude":
        area = area if area in APTITUDE_AREAS else "quantitative"
        topic = f"{area.capitalize()} aptitude"
        prompt = f"""You are writing a placement-style aptitude test (multiple choice), like those used by Indian campus recruiters (TCS NQT, Infosys, AMCAT).

Area: {APTITUDE_AREAS[area]}
Difficulty: {DIFFICULTIES[difficulty]}

Write exactly {num_questions} questions. Each must have ONE unambiguous correct answer; for numerical questions, compute the answer carefully and make sure exactly one option matches it. Questions must be solvable in about one minute each without a calculator. Vary the sub-types within the area.
"""
    else:
        profile = (load_profile(user_id) or {}) if user_id else {}
        target_role = profile.get("target_role") or profile.get("goal_direction") or ""
        from app.services.domain_packs import resolve_field
        topic = (topic or "").strip()[:120] or target_role or f"Core concepts of {resolve_field(profile)['label']}"
        candidate = (profile_as_compact_context(user_id) if personalize else "") or \
            "No detailed profile — pitch questions at an intermediate student level."
        prompt = f"""You are writing a technical theory test (multiple choice) on: {topic}.

━━ CANDIDATE PROFILE ━━
{candidate}

Difficulty: {DIFFICULTIES[difficulty]}

Write exactly {num_questions} multiple-choice questions that test real conceptual understanding (not trivia or memorized definitions). Cover several distinct sub-skills of the topic rather than repeating one idea.
"""
    prompt += f"""

Return ONLY valid JSON in exactly this shape:
[
  {{
    "question": "question text",
    "options": ["option A", "option B", "option C", "option D"],
    "answer_index": 0-3 integer index of the single correct option,
    "explanation": "1-2 sentences on why the correct answer is right",
    "skill": "short name of the sub-skill tested, e.g. 'SQL joins' or 'Percentages'"
  }}
]
Rules: exactly 4 options per question, exactly one correct; vary the position of the correct answer; no "all of the above"; no text outside the JSON."""

    try:
        data = generate_json(prompt, temperature=0.5, max_tokens=8000)
    except Exception as exc:
        logger.error(f"theory test generation failed: {exc}")
        raise ValueError("generation failed") from exc

    if isinstance(data, dict):
        data = data.get("questions") or []
    questions = [
        {
            "question": q["question"].strip(),
            "options": [o.strip() for o in q["options"]],
            "answer_index": q["answer_index"],
            "explanation": str(q.get("explanation") or "").strip(),
            "skill": str(q.get("skill") or topic).strip() or topic,
        }
        for q in (data if isinstance(data, list) else [])
        if _valid_question(q)
    ][:num_questions]

    if len(questions) < MIN_QUESTIONS:
        raise ValueError(f"only {len(questions)} usable questions generated")
    return topic, questions
