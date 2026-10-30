"""Production backlog #4: planning a week runs as a background job. Requests
answer immediately (the gate is still checked up front), jobs are deduped per
learner, claimed exclusively (SKIP LOCKED on Postgres), recovered when stuck,
and page loads never wait on the model.

    .venv/Scripts/python -m pytest tests/test_background_jobs.py -q
"""
import datetime
import json
import os
import sys
import tempfile
import threading
import uuid

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "background_jobs_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import BackgroundJob, JourneyEvent, MarketSnapshot, RoadmapState, User  # noqa: E402
from app.services import central_engine, jobs  # noqa: E402
import app.services.compliance as comp  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
BRIEF = {"phases": [{"id": "p1", "name": "Foundations", "description": "Basics", "nodes": [
    {"id": "n-sql", "label": "SQL", "skill_name": "SQL", "status": "locked", "complexity_score": 2.0},
    {"id": "n-excel", "label": "Excel", "skill_name": "Excel", "status": "locked", "complexity_score": 2.0}]}]}


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    from app.limiter import limiter
    limiter.reset()  # every test request shares one client address
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(settings, "DEV_MODE", False)


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _user(uid, days_old=3):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=uid, target_role="Analyst", hours_per_week=10,
                    created_at=datetime.datetime.utcnow() - datetime.timedelta(days=days_old),
                    profile_data=json.dumps({"audience": "student", "target_role": "Analyst"})))
        db.commit()
        comp.record_consent(db, uid, comp.TERMS, True)
        db.add(MarketSnapshot(id=str(uuid.uuid4()), user_id=uid, target_role="Analyst",
                              snapshot_date=datetime.date.today(), top_demanded_skills="[]", emerging_skills="[]",
                              raw_data="{}", confidence_score=0.6))
        db.commit()
    db.close()
    return {"X-User-Id": uid, "X-User-Email": f"{uid}@gmail.com"}


def _clear_queue():
    db = SessionLocal()
    db.query(BackgroundJob).delete()
    db.commit()
    db.close()


def test_enqueue_dedupes_plan_jobs_and_claims_are_exclusive():
    _clear_queue()
    _user("bj-dedupe")
    db = SessionLocal()
    a = jobs.enqueue(db, "bj-dedupe", "weekly_cycle")
    b = jobs.enqueue(db, "bj-dedupe", "first_roadmap")  # same plan group: no second job
    assert a.id == b.id and db.query(BackgroundJob).count() == 1
    first, second = jobs._claim(db), jobs._claim(db)
    assert first.id == a.id and first.status == "running" and first.attempts == 1 and second is None
    db.close()
    _clear_queue()


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL", "").startswith("postgres"), reason="SKIP LOCKED needs Postgres")
def test_two_workers_never_take_the_same_job_on_postgres():
    _clear_queue()
    _user("bj-pg")
    db = SessionLocal()
    jobs.enqueue(db, "bj-pg", "weekly_cycle")
    db.close()
    got, barrier = [], threading.Barrier(4)

    def worker():
        s = SessionLocal()
        barrier.wait()
        job = jobs._claim(s)
        if job:
            got.append(job.id)
        s.close()
    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(got) == 1
    _clear_queue()


def test_weekly_cycle_route_checks_the_gate_then_queues(monkeypatch):
    _clear_queue()
    h = _user("bj-week")
    db = SessionLocal()
    db.add(RoadmapState(id=str(uuid.uuid4()), user_id="bj-week", destination="{}", phases=json.dumps(BRIEF["phases"]),
                        weekly_focus=json.dumps({"primary_actions": [{"id": "t1", "title": "Unfinished task"}],
                                                 "manual": True})))
    db.commit()
    db.close()
    gate = client.post("/api/career-os/user/bj-week/weekly-cycle", headers=h)
    assert gate.status_code == 400 and "Complete or skip the remaining 1 task" in gate.json()["detail"]
    assert jobs.active_plan_job(SessionLocal(), "bj-week") is None

    db = SessionLocal()
    roadmap = db.query(RoadmapState).filter_by(user_id="bj-week").first()
    roadmap.weekly_focus = json.dumps({"primary_actions": [], "manual": True})  # nothing left to finish
    db.commit()
    db.close()
    monkeypatch.setattr(central_engine, "generate_weekly_brief", lambda *a, **k: BRIEF)
    first = ok(client.post("/api/career-os/user/bj-week/weekly-cycle", headers=h), 202)["job"]
    again = ok(client.post("/api/career-os/user/bj-week/weekly-cycle", headers=h), 202)["job"]
    assert first["id"] == again["id"] and first["status"] == "queued"
    status = ok(client.get(f"/api/background-jobs/{first['id']}", headers=h))
    assert status["status"] == "queued"
    assert client.get(f"/api/background-jobs/{first['id']}", headers=_user("bj-stranger")).status_code == 404

    done = jobs.run_next()
    assert done.id == first["id"] and done.status == "done"
    db = SessionLocal()
    assert db.query(JourneyEvent).filter_by(user_id="bj-week", event_type="weekly_cycle_completed").count() == 1
    focus = json.loads(db.query(RoadmapState).filter_by(user_id="bj-week").first().weekly_focus)
    assert [a["title"] for a in focus["primary_actions"]]
    db.close()
    assert ok(client.get(f"/api/background-jobs/{first['id']}", headers=h))["status"] == "done"


def test_first_page_load_never_waits_on_the_model(monkeypatch):
    _clear_queue()
    h = _user("bj-first")

    def no_inline_ai(*_a, **_k):
        raise AssertionError("the page load must not call the model")
    monkeypatch.setattr(central_engine, "generate_weekly_brief", no_inline_ai)
    ctx = ok(client.get("/api/career-os/user/bj-first/context", headers=h))
    assert ctx["roadmap_job"]["kind"] == "first_roadmap" and ctx["roadmap_job"]["status"] == "queued"
    assert ctx["roadmap"]["weekly_focus"]["primary_actions"] == []
    again = ok(client.get("/api/career-os/user/bj-first/context", headers=h))
    assert again["roadmap_job"]["id"] == ctx["roadmap_job"]["id"]  # still one job

    monkeypatch.setattr(central_engine, "generate_weekly_brief", lambda *a, **k: BRIEF)
    assert jobs.run_next().status == "done"
    monkeypatch.setattr(central_engine, "generate_weekly_brief", no_inline_ai)
    ready = ok(client.get("/api/career-os/user/bj-first/context", headers=h))
    assert ready["roadmap_job"] is None and ready["roadmap"]["weekly_focus"]["primary_actions"]


def test_failures_and_stuck_jobs(monkeypatch):
    _clear_queue()
    _user("bj-fail")
    db = SessionLocal()
    job_id = jobs.enqueue(db, "bj-fail", "weekly_cycle").id
    db.close()

    def broken(*_a, **_k):
        raise RuntimeError("model exploded")
    monkeypatch.setattr(central_engine, "run_weekly_career_cycle", broken)
    failed = jobs.run_next()
    assert failed.id == job_id and failed.status == "failed"
    assert failed.error == "Something went wrong preparing your plan."  # internals stay out of the UI

    def gate(*_a, **_k):
        raise ValueError("Please wait about 2 more minute(s) before requesting the next week.")
    monkeypatch.setattr(central_engine, "run_weekly_career_cycle", gate)
    db = SessionLocal()
    jobs.enqueue(db, "bj-fail", "weekly_cycle")
    db.close()
    assert jobs.run_next().error.startswith("Please wait about 2")  # learner-facing messages pass through

    db = SessionLocal()
    old = datetime.datetime.utcnow() - datetime.timedelta(minutes=settings.JOB_STALE_MINUTES + 5)
    retry = BackgroundJob(id=str(uuid.uuid4()), user_id="bj-fail", kind="weekly_cycle", status="running",
                          attempts=1, started_at=old)
    give_up = BackgroundJob(id=str(uuid.uuid4()), user_id="bj-fail", kind="first_roadmap", status="running",
                            attempts=2, started_at=old)
    db.add_all([retry, give_up])
    db.commit()
    assert jobs.recover_stale(db) == 2
    db.refresh(retry)
    db.refresh(give_up)
    assert retry.status == "queued" and give_up.status == "failed"

    finished_long_ago = BackgroundJob(id=str(uuid.uuid4()), user_id="bj-fail", kind="weekly_cycle", status="done",
                                      finished_at=datetime.datetime.utcnow() - datetime.timedelta(days=settings.JOB_KEEP_DAYS + 1))
    db.add(finished_long_ago)
    db.commit()
    old_id = finished_long_ago.id
    assert jobs.cleanup(db) >= 1 and db.get(BackgroundJob, old_id) is None
    assert "background_jobs" in comp.export_user_data(db, "bj-fail")
    db.close()
    _clear_queue()
