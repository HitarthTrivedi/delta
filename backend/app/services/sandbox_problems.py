"""Coding Sandbox problem content.

The curated (topic, title, difficulty) index comes from the existing
NeetCode-150 bank in central_engine.py — already used to build weekly LeetCode
tasks, so problem naming/difficulty/skill-tagging stays consistent with the
rest of the app. The actual displayable statement, starter code, and hidden
test cases don't exist anywhere yet, so they're generated on demand via the
shared AI service and cached per (topic, title) so repeat opens don't re-call
the model.
"""
from __future__ import annotations

import logging

from app.services.ai_service import generate_json
from app.services.central_engine import LEETCODE_PROBLEMS, LEETCODE_SEQUENCE

logger = logging.getLogger("delta.sandbox_problems")

# In-process cache — problem content is deterministic-enough per (topic, title)
# that regenerating per user/session would just waste AI calls for identical
# content. Cleared on process restart, which is fine (regenerates on demand).
_package_cache: dict[str, dict] = {}


def list_topics() -> list[dict]:
    """Curated topic -> problems index, in the app's established learning order."""
    return [
        {
            "topic": topic,
            "tip": tip,
            "problems": [
                {"id": p["id"], "title": p["title"], "difficulty": p["difficulty"], "url": p["url"]}
                for p in LEETCODE_PROBLEMS.get(topic, [])
            ],
        }
        for topic, tip in LEETCODE_SEQUENCE
    ]


def find_problem(topic: str, problem_id: int) -> dict | None:
    for p in LEETCODE_PROBLEMS.get(topic, []):
        if p["id"] == problem_id:
            return p
    return None


def generate_problem_package(topic: str, title: str, difficulty: str) -> dict:
    """Return {statement, examples, starter_code: {lang: str}, test_cases: [{input, expected_output}]}.
    Problems are I/O-contract based (read stdin, print stdout) so grading is a
    plain stdout diff across every supported language."""
    cache_key = f"{topic}::{title}"
    if cache_key in _package_cache:
        return _package_cache[cache_key]

    prompt = f"""You are writing a practice coding problem for a DSA interview-prep sandbox.
Topic: {topic}
Problem name (for reference — write your own self-contained statement, don't assume the solver knows this exact LeetCode problem): {title}
Difficulty: {difficulty}

The problem MUST be an I/O-contract problem: the solution reads input from stdin and prints the answer to stdout — NOT a function signature to implement. This lets one grader work identically across Python/JavaScript/Java/C++.

Return ONLY valid JSON in exactly this shape:
{{
  "statement": "Full problem description, 2-4 paragraphs, self-contained. Explicitly state the stdin input format and the stdout output format.",
  "examples": [
    {{"input": "exact stdin text", "output": "exact expected stdout text", "explanation": "why"}}
  ],
  "starter_code": {{
    "python": "starter code with a comment showing how to read stdin, no solution logic",
    "javascript": "same, idiomatic Node.js (readline or process.stdin)",
    "java": "same, idiomatic java.util.Scanner, public class Main",
    "cpp": "same, idiomatic #include <iostream>, int main()"
  }},
  "test_cases": [
    {{"input": "exact stdin text", "expected_output": "exact expected stdout text"}}
  ]
}}
Rules: include 2-3 "examples" (shown to the solver) and 4-6 "test_cases" (used for grading — can overlap with examples but must also cover edge cases like empty input, single element, duplicates, negatives, or large-ish values as appropriate to the topic). Output format must be exact and consistent across every example/test case (same number formatting, same separators). No text outside the JSON."""

    try:
        data = generate_json(prompt, temperature=0.4, max_tokens=4000)
    except Exception as exc:
        logger.error(f"problem generation failed for {cache_key}: {exc}")
        data = {}

    if not isinstance(data, dict) or not data.get("test_cases"):
        # Fail-safe minimal package so the sandbox never hard-errors on a bad
        # generation — a trivial echo problem the user can still interact with.
        data = {
            "statement": f"({title}) Problem generation is temporarily unavailable. Read an integer n from stdin and print n doubled.",
            "examples": [{"input": "5", "output": "10", "explanation": "5 * 2 = 10"}],
            "starter_code": {
                "python": "n = int(input())\n",
                "javascript": "const n = parseInt(require('fs').readFileSync(0, 'utf8').trim());\n",
                "java": "import java.util.Scanner;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int n = sc.nextInt();\n  }\n}\n",
                "cpp": "#include <iostream>\nint main() {\n  int n; std::cin >> n;\n}\n",
            },
            "test_cases": [{"input": "5", "expected_output": "10"}, {"input": "0", "expected_output": "0"}],
        }

    _package_cache[cache_key] = data
    return data
