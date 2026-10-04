"""Delta for School — AI lesson drafts.

Generates ONE lesson + quiz per NCERT chapter. This is only a draft: a human
reviewer edits and approves it before any child sees it (see routers/school.py).
No child data is ever sent to the model; prompts contain only the syllabus
position (board, class, subject, chapter).
"""
from __future__ import annotations

import logging

from app.services.ai_service import generate_json

logger = logging.getLogger("delta.school_content_ai")

QUIZ_LEN = 5


def valid_quiz_item(q) -> bool:
    if not isinstance(q, dict) or not isinstance(q.get("question"), str) or not q["question"].strip():
        return False
    opts = q.get("options")
    if not isinstance(opts, list) or len(opts) != 4 or not all(isinstance(o, str) and o.strip() for o in opts):
        return False
    idx = q.get("answer_index")
    return isinstance(idx, int) and not isinstance(idx, bool) and 0 <= idx < 4


def clean_quiz(items) -> list[dict]:
    return [
        {
            "question": q["question"].strip(),
            "options": [o.strip() for o in q["options"]],
            "answer_index": q["answer_index"],
            "explanation": str(q.get("explanation") or "").strip(),
        }
        for q in (items if isinstance(items, list) else [])
        if valid_quiz_item(q)
    ]


def generate_lesson_draft(board: str, grade: int, subject_label: str, textbook: str, chapter_no: int, chapter_title: str) -> tuple[str, list[dict]]:
    """Returns (lesson_markdown, quiz). Raises ValueError on unusable output."""
    prompt = f"""You are an experienced {board} {subject_label} teacher writing a lesson for Class {grade} students (age about {grade + 5}).

Chapter {chapter_no}: "{chapter_title}" from the NCERT textbook "{textbook}".

Write a clear, accurate lesson that covers this chapter's core ideas as taught in the NCERT syllabus for Class {grade}. Requirements:
- Simple, friendly language for a Class {grade} student. Short paragraphs. Use everyday Indian examples.
- Markdown: use ## headings for each main idea, bullet points, and **bold** for key terms. For maths, show 2-3 fully worked examples step by step.
- Stay strictly within the Class {grade} syllabus for this chapter. Do not introduce higher-class concepts.
- End with a "## Quick recap" section of 4-6 bullet points.
- Be factually precise. If a fact is uncertain, leave it out.
- No links, no images, no references to any person's private data.

Also write a {QUIZ_LEN}-question multiple-choice quiz testing understanding of THIS lesson (not trick questions).

Return ONLY valid JSON:
{{
  "lesson_markdown": "the full lesson in markdown",
  "quiz": [
    {{"question": "...", "options": ["A", "B", "C", "D"], "answer_index": 0-3, "explanation": "one sentence on why"}}
  ]
}}
Exactly 4 options per question, exactly one correct, vary the correct position. No text outside the JSON."""
    try:
        data = generate_json(prompt, temperature=0.4, max_tokens=9000)
    except Exception as exc:
        logger.error(f"lesson generation failed: {exc}")
        raise ValueError("generation failed") from exc

    if not isinstance(data, dict):
        raise ValueError("unexpected output")
    lesson = str(data.get("lesson_markdown") or "").strip()
    quiz = clean_quiz(data.get("quiz"))
    if len(lesson) < 300 or len(quiz) < 3:
        raise ValueError("lesson too short or quiz unusable")
    return lesson, quiz[:QUIZ_LEN]
