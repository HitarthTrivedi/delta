"""Background job queue on the app database (no extra infrastructure).

- `enqueue` returns the learner's existing queued/running plan job instead of
  adding a second one, so two clicks never generate a week twice.
- Workers claim jobs atomically: `FOR UPDATE SKIP LOCKED` on Postgres, a
  guarded UPDATE on SQLite. Each job runs with its own session, so the page
  request's connection is released straight away.
- A job stuck in "running" (worker died) is retried once, then marked failed.
- Finished jobs are deleted after JOB_KEEP_DAYS (daily sweep).
"""
from __future__ import annotations

import datetime
import json
import logging
import threading
import time
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.background_job import BackgroundJob

logger = logging.getLogger("delta.jobs")
PLAN_KINDS = ("weekly_cycle", "first_roadmap")  # one at a time per learner
MAX_ATTEMPTS = 2
_started = False
_start_lock = threading.Lock()


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def job_dict(job: BackgroundJob) -> dict:
    return {"id": job.id, "kind": job.kind, "status": job.status, "error": job.error,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None}


def enqueue(db: Session, user_id: str, kind: str, payload: dict | None = None) -> BackgroundJob:
    kinds = PLAN_KINDS if kind in PLAN_KINDS else (kind,)
    existing = (db.query(BackgroundJob)
                .filter(BackgroundJob.user_id == user_id, BackgroundJob.kind.in_(kinds),
                        BackgroundJob.status.in_(("queued", "running")))
                .order_by(BackgroundJob.created_at).first())
    if existing:
        return existing
    job = BackgroundJob(id=str(uuid.uuid4()), user_id=user_id, kind=kind, payload=json.dumps(payload or {}))
    db.add(job)
    db.commit()
    return job


def get(db: Session, job_id: str) -> BackgroundJob | None:
    return db.get(BackgroundJob, job_id)


def active_plan_job(db: Session, user_id: str) -> BackgroundJob | None:
    return (db.query(BackgroundJob)
            .filter(BackgroundJob.user_id == user_id, BackgroundJob.kind.in_(PLAN_KINDS),
                    BackgroundJob.status.in_(("queued", "running")))
            .order_by(BackgroundJob.created_at).first())


def _claim(db: Session) -> BackgroundJob | None:
    """Take the oldest queued job, or None. Safe with several workers/processes."""
    if db.bind.dialect.name == "postgresql":
        row = db.execute(text(
            "SELECT id FROM background_jobs WHERE status = 'queued' ORDER BY created_at "
            "FOR UPDATE SKIP LOCKED LIMIT 1")).first()
        if not row:
            db.rollback()
            return None
        db.execute(text("UPDATE background_jobs SET status = 'running', started_at = :now, "
                        "attempts = attempts + 1 WHERE id = :id"), {"now": _now(), "id": row[0]})
        db.commit()
        return db.get(BackgroundJob, row[0])
    candidate = (db.query(BackgroundJob.id).filter(BackgroundJob.status == "queued")
                 .order_by(BackgroundJob.created_at).first())
    if not candidate:
        return None
    claimed = (db.query(BackgroundJob)
               .filter(BackgroundJob.id == candidate[0], BackgroundJob.status == "queued")
               .update({BackgroundJob.status: "running", BackgroundJob.started_at: _now(),
                        BackgroundJob.attempts: BackgroundJob.attempts + 1}, synchronize_session=False))
    db.commit()
    return db.get(BackgroundJob, candidate[0]) if claimed else None


def _execute(db: Session, job: BackgroundJob) -> None:
    from app.models import MarketSnapshot, User
    from app.services import central_engine
    payload = json.loads(job.payload or "{}")
    if job.kind == "weekly_cycle":
        # The gate (finish your tasks first) was checked when the job was queued.
        central_engine.run_weekly_career_cycle(db, job.user_id, bypass_gate=True,
                                               carried_actions=payload.get("carried_actions") or None)
    elif job.kind == "first_roadmap":
        user = db.get(User, job.user_id)
        market = (db.query(MarketSnapshot).filter(MarketSnapshot.user_id == job.user_id)
                  .order_by(MarketSnapshot.created_at.desc()).first())
        if user and market:
            central_engine.get_or_create_roadmap_state(db, user, market, regenerate=True)
    else:
        raise ValueError(f"Unknown job kind {job.kind}")


def run_next(db: Session | None = None) -> BackgroundJob | None:
    """Claim and run one job. Returns it (finished), or None if nothing was queued."""
    from app.database import SessionLocal
    own = db is None
    db = db or SessionLocal()
    try:
        job = _claim(db)
        if not job:
            return None
        job_id = job.id
        try:
            _execute(db, job)
            db.rollback()  # discard anything the work left open; its own commits stand
            job = db.get(BackgroundJob, job_id)
            job.status, job.error, job.finished_at = "done", None, _now()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.error("job %s (%s) failed: %s", job_id, job.kind, exc, exc_info=True)
            job = db.get(BackgroundJob, job_id)
            # A ValueError carries a message meant for the learner (e.g. a gate).
            job.status = "failed"
            job.error = str(exc)[:500] if isinstance(exc, ValueError) else "Something went wrong preparing your plan."
            job.finished_at = _now()
        db.commit()
        db.refresh(job)
        if own:
            db.expunge(job)  # still readable after this function closes its session
        return job
    finally:
        if own:
            db.close()


def recover_stale(db: Session) -> int:
    """Running jobs whose worker died: retry once, then fail."""
    cutoff = _now() - datetime.timedelta(minutes=settings.JOB_STALE_MINUTES)
    stale = db.query(BackgroundJob).filter(BackgroundJob.status == "running", BackgroundJob.started_at < cutoff).all()
    for job in stale:
        if job.attempts < MAX_ATTEMPTS:
            job.status, job.started_at = "queued", None
        else:
            job.status, job.finished_at = "failed", _now()
            job.error = "This took too long. Please try again."
    db.commit()
    return len(stale)


def cleanup(db: Session) -> int:
    cutoff = _now() - datetime.timedelta(days=settings.JOB_KEEP_DAYS)
    n = (db.query(BackgroundJob).filter(BackgroundJob.status.in_(("done", "failed")),
                                        BackgroundJob.finished_at < cutoff).delete(synchronize_session=False))
    db.commit()
    return n


def _worker_loop(index: int) -> None:
    from app.database import SessionLocal
    last_recover = 0.0
    while True:
        try:
            if index == 0 and time.monotonic() - last_recover > 60:
                last_recover = time.monotonic()
                db = SessionLocal()
                try:
                    recover_stale(db)
                finally:
                    db.close()
            if run_next() is None:
                time.sleep(settings.JOB_POLL_SECONDS)
        except Exception as exc:  # noqa: BLE001 — a worker must never die
            logger.error("job worker %s error: %s", index, exc, exc_info=True)
            time.sleep(max(1.0, settings.JOB_POLL_SECONDS))


def start_workers() -> int:
    """Start JOB_WORKERS daemon threads once per process (called at startup)."""
    global _started
    with _start_lock:
        if _started or settings.JOB_WORKERS <= 0:
            return 0
        _started = True
    for i in range(settings.JOB_WORKERS):
        threading.Thread(target=_worker_loop, args=(i,), name=f"job-worker-{i}", daemon=True).start()
    logger.info("started %s background job worker(s)", settings.JOB_WORKERS)
    return settings.JOB_WORKERS
