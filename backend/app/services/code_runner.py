"""Code execution for the Coding Sandbox — via JDoodle's Compiler API.

Running arbitrary user code isn't safe to do in-process (no container
isolation on Render's free tier), so execution is delegated to JDoodle
(https://www.jdoodle.com/compiler-api) — a free-tier (200 runs/day), keyed
"compiler as a service" API. Problems are I/O-contract based (read stdin,
print stdout), so grading is a plain stdout diff — identical across every
supported language.

Requires JDOODLE_CLIENT_ID / JDOODLE_CLIENT_SECRET (see app.config). Without
them, run_code() returns a clear "not configured" error rather than failing
silently or crashing — the rest of the sandbox stays usable (problem browsing,
history) even if execution isn't set up yet.
"""
from __future__ import annotations

import logging

from app.services.http_client import get_session

logger = logging.getLogger("delta.code_runner")

JDOODLE_EXECUTE_URL = "https://api.jdoodle.com/v1/execute"

# JDoodle (language, versionIndex) pairs. versionIndex "0" is each language's
# default/oldest listed version in JDoodle's catalogue — adjust here if a
# specific version is later confirmed to behave better once real credentials
# are available to test against.
LANGUAGES: dict[str, tuple[str, str]] = {
    "python": ("python3", "0"),
    "javascript": ("nodejs", "0"),
    "java": ("java", "0"),
    "cpp": ("cpp17", "0"),
}


def is_configured() -> bool:
    from app.config import settings
    return bool(settings.JDOODLE_CLIENT_ID and settings.JDOODLE_CLIENT_SECRET)


def run_code(language: str, source: str, stdin: str = "") -> dict:
    """Execute `source` with `stdin` via JDoodle. Returns
    {stdout, stderr, exit_code, error} — `error` is set (and the rest empty)
    on missing config, an unsupported language, or a network/API failure, so
    callers never need to catch exceptions."""
    if language not in LANGUAGES:
        return {"stdout": "", "stderr": "", "exit_code": None, "error": f"Unsupported language: {language}"}

    from app.config import settings
    if not is_configured():
        return {
            "stdout": "", "stderr": "", "exit_code": None,
            "error": "Code execution isn't set up yet. Add JDOODLE_CLIENT_ID / JDOODLE_CLIENT_SECRET to enable it.",
        }

    lang, version_index = LANGUAGES[language]
    payload = {
        "script": source,
        "language": lang,
        "versionIndex": version_index,
        "stdin": stdin,
        "clientId": settings.JDOODLE_CLIENT_ID,
        "clientSecret": settings.JDOODLE_CLIENT_SECRET,
    }

    try:
        resp = get_session().post(JDOODLE_EXECUTE_URL, json=payload, timeout=20)
        resp.raise_for_status()
        body = resp.json()
    except Exception as exc:
        logger.warning(f"JDoodle execution failed: {exc}")
        return {"stdout": "", "stderr": "", "exit_code": None, "error": "Code execution service is unavailable right now. Try again shortly."}

    if body.get("statusCode") not in (200, None):
        return {"stdout": "", "stderr": "", "exit_code": None, "error": body.get("error") or "Code execution failed."}

    output = body.get("output", "")
    # JDoodle returns compile/runtime errors inline in `output` rather than a
    # separate stderr field — a plain successful run has no obvious error
    # markers, so anything else is treated as run output, not misclassified.
    return {"stdout": output, "stderr": "", "exit_code": 0, "error": None}


def outputs_match(actual: str, expected: str) -> bool:
    """Whitespace-tolerant stdout comparison — trims trailing whitespace on
    each line and trailing blank lines, so harmless formatting differences
    (trailing newline, trailing spaces) don't fail an otherwise-correct answer."""
    def _normalize(text: str) -> list[str]:
        lines = [line.rstrip() for line in (text or "").splitlines()]
        while lines and lines[-1] == "":
            lines.pop()
        return lines

    return _normalize(actual) == _normalize(expected)
