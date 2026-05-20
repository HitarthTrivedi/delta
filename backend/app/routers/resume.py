from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    filename = file.filename or "resume.pdf"

    # For now, return a mock parsed result
    return {
        "filename": filename,
        "size": len(content),
        "parsed_skills": [
            {"name": "Python", "confidence": 0.95},
            {"name": "React", "confidence": 0.85},
            {"name": "FastAPI", "confidence": 0.80},
            {"name": "SQL", "confidence": 0.75},
        ],
        "parsed_experience": "2+ years software development",
        "status": "parsed",
    }
