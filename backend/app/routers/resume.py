"""Resume router — delta Career OS."""
from __future__ import annotations

import datetime
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.resume_parser import parse_resume, parse_resume_llm
from app.services.resume_service import (
    apply_suggestions,
    build_resume_from_profile,
    export_to_docx,
    generate_suggestions,
    get_market_skills,
    get_or_create_resume_profile,
    optimize_for_ats,
    save_resume,
    serialize_resume,
    suggestions_are_due,
)
from typing import Optional
from fastapi import Header
from app.dependencies.auth import require_owner, verify_resource_owner

logger = logging.getLogger("delta.resume")
router = APIRouter(prefix="/api/resume", tags=["resume"])


# ── Pydantic payloads ──────────────────────────────────────────────────────────

class ApplySuggestionsPayload(BaseModel):
    accepted_adds: list[dict] = Field(default_factory=list)
    accepted_removes: list[str] = Field(default_factory=list)


# ── GET /api/resume/{user_id} ─────────────────────────────────────────────────

@router.get("/{user_id}")
def get_resume(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Fetch the current structured resume for the user (or null if none exists)."""
    resume = get_or_create_resume_profile(user_id, db)
    if not resume:
        return {"exists": False, "resume": None, "suggestions_due": False}
    return {
        "exists": True,
        "resume": serialize_resume(resume),
        "suggestions_due": suggestions_are_due(resume),
    }


# ── POST /api/resume/{user_id}/generate ──────────────────────────────────────

@router.post("/{user_id}/generate")
def generate_resume(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Generate a structured resume from the user's delta Career OS profile."""
    try:
        structured = build_resume_from_profile(user_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    market_skills = get_market_skills(user_id, db)
    resume = save_resume(user_id, db, structured, source="generated", market_skills=market_skills)
    return {
        "status": "generated",
        "resume": serialize_resume(resume),
    }


# ── POST /api/resume/{user_id}/upload ────────────────────────────────────────

@router.post("/{user_id}/upload")
async def upload_resume(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    """Upload an existing PDF or DOCX resume; parse, structure and store it."""
    content = await file.read()
    filename = file.filename or "resume.pdf"
    parsed = parse_resume(content, filename)
    raw_text = parsed.get("raw_text") or ""

    try:
        # Try high-fidelity LLM parsing first
        if raw_text.strip():
            structured = parse_resume_llm(raw_text)
            structured["_meta"] = {"source": "uploaded", "filename": filename}
        else:
            raise ValueError("No readable text in the uploaded file")
    except Exception as exc:
        logger.warning("LLM Resume Parsing failed for user %s: %s. Falling back to heuristic parsing.", user_id, type(exc).__name__)
        # Minimal fallback structured dict from regex parsed signals
        structured = {
            "contact": {"name": "", "email": "", "role": ""},
            "summary": "",
            "skills": [s["name"] for s in (parsed.get("parsed_skills") or [])],
            "experience": [{"title": parsed.get("parsed_experience", "") or "Uploaded Experience", "company": "", "description": "", "date": ""}],
            "projects": [],
            "achievements": [],
            "education": [{"degree": parsed.get("education", ""), "institution": "", "year": ""}],
            "certifications": [],
            "_meta": {"source": "uploaded_fallback", "filename": filename},
        }

    market_skills = get_market_skills(user_id, db)
    resume = save_resume(
        user_id,
        db,
        structured,
        raw_text=raw_text[:4000],
        source="uploaded",
        market_skills=market_skills,
    )
    return {
        "status": "uploaded",
        "filename": filename,
        "resume": serialize_resume(resume),
        "parsed_skills_count": len(structured.get("skills") or []),
    }


# ── GET /api/resume/{user_id}/suggestions ────────────────────────────────────

@router.get("/{user_id}/suggestions")
def get_suggestions(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """
    Return bi-weekly resume update suggestions.
    Always returns a response; the frontend checks to_add/to_remove lengths.
    """
    resume = get_or_create_resume_profile(user_id, db)
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found. Generate one first.")

    suggestions = generate_suggestions(user_id, db, resume)

    # Update last_suggested_at timestamp
    resume.last_suggested_at = datetime.datetime.utcnow()
    db.commit()

    return {
        "suggestions_due": True,
        "to_add": suggestions["to_add"],
        "to_remove": suggestions["to_remove"],
        "since": suggestions["since"],
        "generated_at": suggestions["generated_at"],
    }


# ── POST /api/resume/{user_id}/apply-suggestions ─────────────────────────────

@router.post("/{user_id}/apply-suggestions")
def apply_resume_suggestions(
    user_id: str,
    payload: ApplySuggestionsPayload,
    db: Session = Depends(get_db),
    _: str = Depends(require_owner),
):
    """Accept/reject suggestions, regenerate and persist the updated resume."""
    resume = get_or_create_resume_profile(user_id, db)
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found.")

    import json
    try:
        structured = json.loads(resume.structured_data or "{}")
    except Exception:
        structured = {}

    updated = apply_suggestions(structured, payload.accepted_adds, payload.accepted_removes)
    market_skills = get_market_skills(user_id, db)
    saved = save_resume(user_id, db, updated, source=resume.source or "generated", market_skills=market_skills)
    return {
        "status": "updated",
        "resume": serialize_resume(saved),
    }


# ── GET /api/resume/{user_id}/download ───────────────────────────────────────

@router.get("/{user_id}/download")
def download_resume(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Return the resume as an ATS-friendly .docx file."""
    resume = get_or_create_resume_profile(user_id, db)
    if not resume or not resume.structured_data:
        raise HTTPException(status_code=404, detail="No resume found. Generate one first.")

    import json
    try:
        structured = json.loads(resume.structured_data)
    except Exception:
        structured = {}

    try:
        docx_bytes = export_to_docx(structured)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate .docx: {exc}") from exc

    name = (structured.get("contact") or {}).get("name") or "resume"
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip()
    filename = f"{safe_name}_resume.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── POST /api/resume/{user_id}/ats-optimize ──────────────────────────────────

@router.post("/{user_id}/ats-optimize")
def ats_optimize(user_id: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Rewrite resume bullet points using market demand keywords (ATS mode)."""
    resume = get_or_create_resume_profile(user_id, db)
    if not resume or not resume.structured_data:
        raise HTTPException(status_code=404, detail="No resume found. Generate one first.")

    import json
    try:
        structured = json.loads(resume.structured_data)
    except Exception:
        structured = {}

    market_skills = get_market_skills(user_id, db)
    optimized = optimize_for_ats(structured, market_skills)
    saved = save_resume(user_id, db, optimized, source=resume.source or "generated", market_skills=market_skills)
    return {
        "status": "ats_optimized",
        "resume": serialize_resume(saved),
        "keywords_applied": market_skills[:15],
    }


# ── Legacy upload endpoint (keep for backward compat) ────────────────────────

@router.post("/upload")
async def upload_resume_legacy(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    if not x_user_id and not authorization:
        raise HTTPException(status_code=401, detail="Authentication required.")
    content = await file.read()
    filename = file.filename or "resume.pdf"
    parsed = parse_resume(content, filename)
    return {
        "filename": filename,
        "size": len(content),
        "parsed_skills": parsed["parsed_skills"],
        "parsed_experience": f"{parsed['experience_years']} years",
        "education": parsed["education"],
        "status": parsed["status"],
    }
