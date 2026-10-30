"""Status of a learner's background job (e.g. planning next week)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import current_identity
from app.services import jobs

router = APIRouter(prefix="/api/background-jobs", tags=["background-jobs"])


@router.get("/{job_id}")
def job_status(job_id: str, identity=Depends(current_identity), db: Session = Depends(get_db)):
    job = jobs.get(db, job_id)
    if not job or job.user_id != identity[0]:
        raise HTTPException(status_code=404, detail="Job not found.")
    return jobs.job_dict(job)
