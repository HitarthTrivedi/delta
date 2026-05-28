"""Resume parser service that extracts signals from uploaded files."""
from __future__ import annotations

import io
import re


KNOWN_SKILLS = [
    "Python", "JavaScript", "TypeScript", "React", "Node.js", "FastAPI",
    "Django", "Flask", "SQL", "PostgreSQL", "MongoDB", "Docker",
    "Kubernetes", "AWS", "GCP", "Azure", "Git", "Linux", "C++", "Java",
    "Machine Learning", "Deep Learning", "Pandas", "NumPy", "Scikit-Learn",
    "TensorFlow", "PyTorch", "LLMs", "RAG", "Vector Databases", "MLOps",
    "System Design", "REST", "GraphQL", "Redis", "Celery",
]


def parse_resume(content: bytes, filename: str) -> dict:
    """Parse PDF/text resume bytes and extract skills, education, and experience signals."""
    text = _extract_text(content, filename)
    skills = _extract_skills(text)
    return {
        "skills": [item["name"] for item in skills],
        "parsed_skills": skills,
        "experience_years": _extract_experience_years(text),
        "education": _extract_education(text),
        "text_excerpt": text[:1200],
        "status": "parsed" if text else "empty_or_unreadable",
    }


def _extract_text(content: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""

    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def _extract_skills(text: str) -> list[dict]:
    text_lower = text.lower()
    parsed = []
    for skill in KNOWN_SKILLS:
        pattern = re.escape(skill.lower()).replace("\\ ", r"[\s-]+")
        if re.search(rf"(?<![a-z0-9+#.]){pattern}(?![a-z0-9+#.])", text_lower):
            confidence = 0.9 if _has_evidence_near_skill(text, skill) else 0.68
            parsed.append({"name": skill, "confidence": confidence})
    return parsed


def _has_evidence_near_skill(text: str, skill: str) -> bool:
    text_lower = text.lower()
    idx = text_lower.find(skill.lower())
    if idx < 0:
        return False
    window = text_lower[max(0, idx - 180): idx + 180]
    evidence_terms = ["project", "built", "developed", "deployed", "intern", "github", "certified", "implemented"]
    return any(term in window for term in evidence_terms)


def _extract_experience_years(text: str) -> float:
    matches = re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", text, flags=re.IGNORECASE)
    if not matches:
        return 0
    return max(float(match) for match in matches)


def _extract_education(text: str) -> str:
    patterns = [
        r"(B\.?\s?Tech[^,\n]*)",
        r"(Bachelor[^,\n]*)",
        r"(M\.?\s?Tech[^,\n]*)",
        r"(Master[^,\n]*)",
        r"(Diploma[^,\n]*)",
        r"(Class\s*12[^,\n]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "unknown"
