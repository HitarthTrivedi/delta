from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.resume_parser import parse_resume

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
