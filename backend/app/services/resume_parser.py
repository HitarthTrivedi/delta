"""Resume parser service — extracts skills from uploaded resumes."""

def parse_resume(content: bytes, filename: str) -> dict:
    """Parse resume file and extract skills. Currently returns mock data."""
    return {
        "skills": ["Python", "React", "FastAPI", "SQL"],
        "experience_years": 2,
        "education": "B.Tech Computer Science",
        "status": "parsed",
    }
