"""Delta for College, P3: predefined role roadmaps. Every template validates,
the template path never calls the AI, milestones progress and adapt (proven
skills skip, self-claimed don't), gates hold then release, target dates
compress, the plan ends or hands over, and college-assigned plans can't stop.

    .venv/Scripts/python -m pytest tests/test_roadmap_templates.py -q
"""
import copy
import datetime
import json
import os
import sys
import tempfile
import uuid

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "roadmap_templates_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import MarketSnapshot, RoadmapEnrollment, RoadmapState, SandboxSession, SkillNode, User, XpEvent  # noqa: E402
from app.services import central_engine, roadmap_templates as rt  # noqa: E402
from app.services.roadmap_catalog import TEMPLATES  # noqa: E402
import app.services.compliance as comp  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
TODAY = datetime.date.today()


@pytest.fixture(autouse=True)
def header_auth(monkeypatch):
    from app.limiter import limiter
    limiter.reset()  # every test request shares one client address
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)

    def no_ai(*_a, **_k):
        raise AssertionError("the template path must not call the AI brief generator")
    monkeypatch.setattr(central_engine, "generate_weekly_brief", no_ai)


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _user(uid, hours=10):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=uid, target_role="Software Engineer", hours_per_week=hours,
                    profile_data=json.dumps({"audience": "student", "field": "cs_ai"})))
        db.commit()
        comp.record_consent(db, uid, comp.TERMS, True)
        db.add(MarketSnapshot(id=str(uuid.uuid4()), user_id=uid, target_role="Software Engineer",
                              snapshot_date=TODAY, top_demanded_skills="[]", emerging_skills="[]", raw_data="{}",
                              confidence_score=0.6))
        db.commit()
    db.close()
    return {"X-User-Id": uid}


def _start(uid, template_id="placement_6m", target=None, week_index=0):
    db = SessionLocal()
    e = rt.start(db, uid, template_id, target)
    e.week_index = week_index
    db.commit()
    db.close()


def _enrollment(db, uid):
    return db.query(RoadmapEnrollment).filter(RoadmapEnrollment.user_id == uid).first()


def _plan_week(uid):
    db = SessionLocal()
    user = db.get(User, uid)
    market = db.query(MarketSnapshot).filter(MarketSnapshot.user_id == uid).first()
    roadmap = central_engine.get_or_create_roadmap_state(db, user, market, regenerate=True)
    focus, phases = json.loads(roadmap.weekly_focus), json.loads(roadmap.phases)
    db.close()
    return focus, phases


def _done(uid, *ids):
    db = SessionLocal()
    for mid in ids:
        db.add(XpEvent(id=str(uuid.uuid4()), user_id=uid, source_type="weekly_task", source_id=f"{mid}@{TODAY}",
                       xp=20, local_date=TODAY))
    db.commit()
    db.close()


def _theory(uid, topic, score, skills=None):
    db = SessionLocal()
    when = datetime.datetime.utcnow()
    breakdown = {k: {"correct": c, "total": t} for k, (c, t) in (skills or {}).items()}
    db.add(SandboxSession(id=str(uuid.uuid4()), user_id=uid, type="theory", title=topic, status="completed",
                          score=score, data=json.dumps({"topic": topic, "result": {"skill_breakdown": breakdown}}),
                          created_at=when, completed_at=when))
    db.commit()
    db.close()


def test_every_template_validates_and_the_validator_catches_mistakes():
    for t in TEMPLATES.values():
        assert rt.validate(t) == [], t["id"]
    broken = copy.deepcopy(TEMPLATES["placement_6m"])
    broken["phases"][1]["weeks"] = [6, 10]
    broken["phases"][0]["milestones"][1]["id"] = broken["phases"][0]["milestones"][0]["id"]
    broken["phases"][0]["milestones"][2]["url"] = "http://insecure.example"
    errors = " | ".join(rt.validate(broken))
    assert "must start at 5" in errors and "duplicate milestone" in errors and "https" in errors


def test_template_week_uses_no_ai_and_survives_regenerate():
    _user("rt-a")
    _start("rt-a")
    for _ in range(2):  # a regenerate must keep the template
        focus, phases = _plan_week("rt-a")
        ids = [a["id"] for a in focus["primary_actions"]]
        assert ids and all(i.startswith("tpl-p6-") for i in ids), ids
        assert focus["template"]["week"] == 1 and focus["phase_name"] == "Foundations and a baseline"
        assert [p["id"] for p in phases][:2] == ["p6-foundations", "p6-core-dsa"]
        assert focus.get("manual") is True  # the week locks like any other
    # cap for 10 h/week is 3 tasks; week 1 of 4 gets ceil(7/4)=2 milestones
    assert ids == ["tpl-p6-baseline-aptitude", "tpl-p6-quant-basics"]
    ctx_progress = rt.progress(SessionLocal(), rt.active_enrollment(SessionLocal(), "rt-a"))
    assert ctx_progress["milestones_total"] == 33 and ctx_progress["on_track"] is True  # optional milestones included


def test_milestones_progress_proven_skills_skip_and_self_claims_dont():
    _user("rt-b", hours=20)
    _start("rt-b", week_index=2)  # week 3: 6 of phase 1's 7 milestones due
    db = SessionLocal()
    db.add(SkillNode(id=str(uuid.uuid4()), user_id="rt-b", name="Arrays", proficiency=10, evidence_type="self"))
    db.commit()
    e = _enrollment(db, "rt-b")
    first = [a["id"] for a in rt.weekly_actions(db, e, cap=10)]
    # a self-claimed 10/10 in Arrays doesn't skip anything
    assert first == ["tpl-p6-baseline-aptitude", "tpl-p6-quant-basics", "tpl-p6-logical-basics", "tpl-p6-language",
                     "tpl-p6-arrays-strings", "tpl-p6-verbal"]
    db.close()
    _done("rt-b", "tpl-p6-baseline-aptitude", "tpl-p6-quant-basics")
    _theory("rt-b", "Arrays", 90, {"Arrays": (9, 10)})  # proven in a test
    db = SessionLocal()
    e = _enrollment(db, "rt-b")
    ids = [a["id"] for a in rt.weekly_actions(db, e, cap=10)]
    # arrays-strings is skipped (proven in a test), so the next milestone (resume) is pulled forward
    assert ids == ["tpl-p6-logical-basics", "tpl-p6-language", "tpl-p6-verbal", "tpl-p6-resume-v1"]
    assert rt.progress(db, e)["milestones_skipped"] == 1
    db.close()


def test_backlog_and_weak_skill_revision():
    _user("rt-c", hours=30)
    _start("rt-c", week_index=4)  # week 5: first week of core DSA, phase 1 left undone
    _theory("rt-c", "Hashing quiz", 40, {"Hashing": (2, 5)})
    db = SessionLocal()
    acts = rt.weekly_actions(db, _enrollment(db, "rt-c"), cap=10)
    ids = [a["id"] for a in acts]
    assert ids[:2] == ["tpl-p6-hashing", "tpl-p6-two-pointers"]
    assert [a["why_now"] for a in acts[2:4]] == ["Carried over from an earlier phase."] * 2
    assert ids[-1] == "tpl-revise-hashing-w5" and acts[-1]["title"] == "Revise Hashing"
    assert rt.progress(db, _enrollment(db, "rt-c"))["on_track"] is False
    db.close()


def test_gate_holds_then_releases():
    _user("rt-d")
    _start("rt-d", week_index=9)  # week 10: last week of core DSA, gate Data Structures >= 60, hold 1
    db = SessionLocal()
    rt.advance(db, "rt-d")
    e = _enrollment(db, "rt-d")
    assert (e.week_index, e.held_weeks) == (9, 1)
    assert rt.progress(db, e)["held_at_gate"] is True
    rt.advance(db, "rt-d")  # the hold is used up: moves on anyway
    assert (e.week_index, e.held_weeks) == (10, 0)
    db.close()

    _user("rt-d2")
    _start("rt-d2", week_index=9)
    _theory("rt-d2", "Data Structures", 72)
    db = SessionLocal()
    rt.advance(db, "rt-d2")
    assert _enrollment(db, "rt-d2").week_index == 10  # passed: no hold
    db.close()


def test_target_date_compresses_the_plan():
    _user("rt-e", hours=10)
    _start("rt-e", target=TODAY + datetime.timedelta(weeks=13), week_index=1)  # 26-week plan in 13 weeks
    db = SessionLocal()
    e = _enrollment(db, "rt-e")
    t = TEMPLATES["placement_6m"]
    assert rt.compressed(e, t) and rt.template_week(e, t) == 3
    e.week_index = 7  # template week 15
    db.commit()
    assert rt.template_week(e, t) == 15
    acts = rt.weekly_actions(db, e, cap=3)
    assert len(acts) == 4  # cap + 1 while compressed
    e.week_index = 8  # template week 17: the optional heaps milestone is dropped
    db.commit()
    assert "tpl-p6-heaps" not in [m["id"] for m in rt._plan(db, e, t)["this_week"]]
    with pytest.raises(ValueError):
        rt.start(db, "rt-e", "placement_6m", TODAY + datetime.timedelta(days=7))
    db.close()


def test_template_end_falls_back_or_hands_over():
    _user("rt-f")
    _start("rt-f", week_index=25)
    db = SessionLocal()
    rt.advance(db, "rt-f")
    assert _enrollment(db, "rt-f").status == "completed" and rt.active_enrollment(db, "rt-f") is None
    db.close()
    _user("rt-g")
    _start("rt-g", "first_year_4y", week_index=155)
    db = SessionLocal()
    rt.advance(db, "rt-g")
    e = _enrollment(db, "rt-g")
    assert (e.template_id, e.week_index, e.status) == ("placement_6m", 0, "active")
    db.close()


def test_break_weeks_come_from_the_template():
    _user("rt-h")
    _start("rt-h", "swe_google_12m", week_index=12)  # template week 13 is a break
    focus, _ = _plan_week("rt-h")
    assert focus["is_break_week"] is True and focus["primary_actions"][0]["id"] == "break-week-maintenance"


def test_job_tasks_first_and_avoided_topics_dropped(monkeypatch):
    _user("rt-i", hours=20)
    _start("rt-i", week_index=1)
    job = {"id": "job-abc-sql", "type": "project", "title": "Practise SQL for the job", "skill": "SQL",
           "description": "x", "source": "Job match: Analyst"}
    monkeypatch.setattr("app.services.job_match.weekly_job_actions", lambda db, uid: [job])
    monkeypatch.setattr(central_engine, "_avoided_topics", lambda uid: ["logical reasoning"])
    focus, _ = _plan_week("rt-i")
    ids = [a["id"] for a in focus["primary_actions"]]
    assert ids[0] == "job-abc-sql" and "tpl-p6-logical-basics" not in ids


def test_api_catalog_start_stop_and_college_assigned_cannot_stop():
    h = _user("rt-j")
    state = ok(client.get("/api/templates/user/rt-j", headers=h))
    assert state["current"] is None and state["catalog"][0]["fields"] in ([], ["cs_ai"])
    assert ok(client.get("/api/templates/swe_google_12m", headers=h))["phase_list"][0]["name"] == "Foundations"
    assert client.get("/api/templates/nope", headers=h).status_code == 404
    started = ok(client.post("/api/templates/user/rt-j/start", headers=h, json={"template_id": "data_analyst_6m"}))
    assert started["current"]["template_id"] == "data_analyst_6m" and started["can_change"] is True
    assert client.post("/api/templates/user/rt-j/start", headers={"X-User-Id": "rt-other"},
                       json={"template_id": "placement_6m"}).status_code == 403
    assert ok(client.post("/api/templates/user/rt-j/stop", headers=h))["current"] is None

    db = SessionLocal()
    rt.start(db, "rt-j", "placement_6m", assigned_by_batch_id="batch-1")
    db.close()
    state = ok(client.get("/api/templates/user/rt-j", headers=h))
    assert state["can_change"] is False and state["current"]["college_assigned"] is True
    assert client.post("/api/templates/user/rt-j/stop", headers=h).status_code == 403
    assert client.post("/api/templates/user/rt-j/start", headers=h,
                       json={"template_id": "swe_google_12m"}).status_code == 403


def test_starting_a_template_replans_an_existing_week_without_ai():
    h = _user("rt-k")
    db = SessionLocal()
    db.add(RoadmapState(id=str(uuid.uuid4()), user_id="rt-k", destination="{}", phases="[]",
                        weekly_focus=json.dumps({"primary_actions": [{"id": "old", "title": "Old task"}], "manual": True})))
    db.commit()
    db.close()
    ok(client.post("/api/templates/user/rt-k/start", headers=h, json={"template_id": "placement_6m"}))
    db = SessionLocal()
    focus = json.loads(db.query(RoadmapState).filter(RoadmapState.user_id == "rt-k").first().weekly_focus)
    assert [a["id"] for a in focus["primary_actions"]][0] == "tpl-p6-baseline-aptitude"
    db.close()


def test_weekly_cycle_advances_the_roadmap_once(monkeypatch):
    monkeypatch.setattr(settings, "DEV_MODE", True)  # skip the finish-your-tasks gate
    _user("rt-l")
    _start("rt-l")
    _plan_week("rt-l")
    db = SessionLocal()
    central_engine.run_weekly_career_cycle(db, "rt-l")
    e = _enrollment(db, "rt-l")
    focus = json.loads(db.query(RoadmapState).filter(RoadmapState.user_id == "rt-l").first().weekly_focus)
    assert e.week_index == 1 and focus["template"]["week"] == 2
    db.close()
