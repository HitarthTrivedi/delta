"""Company roadmaps (build order phase 5): a company's skill needs become a
roadmap from the reviewed library, a Delta admin approves it, students in the
company's pool follow it as an extra track with a per-roadmap consent, and
the company sees progress, skill scores and its own tests' results.

    .venv/Scripts/python -m pytest tests/test_company_roadmaps.py -q
"""
import csv
import datetime
import io
import json
import os
import sys
import tempfile
import uuid

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "company_roadmaps_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (CompanyRoadmap, CompanyRoadmapMember, CompanyTest, MarketSnapshot, Recruiter,  # noqa: E402
                        SandboxSession, User)
from app.services import central_engine, company_roadmaps, job_match, skill_library  # noqa: E402
import app.routers.recruiter as rr  # noqa: E402
import app.services.compliance as comp  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
ADMIN = {"X-User-Id": "cr-boss", "X-User-Email": "boss@delta.test"}
V = comp.POLICY_VERSION
GEN_CALLS, EXTRACT_CALLS = [], []
QUESTIONS = [{"question": f"Q{i}?", "options": ["a", "b", "c", "d"], "skill": "SQL", "answer_index": i % 4,
              "explanation": f"because {i}"} for i in range(5)]


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    from app.limiter import limiter
    limiter.reset()  # every test request shares one client address
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "boss@delta.test")
    monkeypatch.setattr(rr, "_supabase_admin_email", lambda *_a, **_k: None, raising=False)

    def fake_generate(user_id, topic, n, difficulty, category, area, personalize=True):
        GEN_CALLS.append((user_id, topic, personalize))
        return topic or "Aptitude", [dict(q) for q in QUESTIONS[:n]]
    monkeypatch.setattr(company_roadmaps, "generate_test", fake_generate)

    def fake_extract(text):
        EXTRACT_CALLS.append(text)
        return {"title": "Data Analyst", "company": "Acme", "seniority": "entry",
                "skills": [{"name": "SQL", "importance": "must", "task": {"title": "t", "detail": "d"}},
                           {"name": "Excel", "importance": "must", "task": {"title": "t", "detail": "d"}},
                           {"name": "Looker Studio", "importance": "nice", "task": {"title": "t", "detail": "d"}}]}
    monkeypatch.setattr(job_match, "_extract", fake_extract)


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _student(uid, audience="student"):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=f"{uid} Student", target_role="Analyst",
                    profile_data=json.dumps({"audience": audience})))
        db.commit()
        comp.record_consent(db, uid, comp.TERMS, True)
    db.close()
    return {"X-User-Id": uid, "X-User-Email": f"{uid}@gmail.com"}


def _recruiter(uid, pool="open"):
    db = SessionLocal()
    if not db.get(Recruiter, uid):
        db.add(Recruiter(id=uid, email=f"{uid}@company.test", name=uid, company=f"{uid} Co", status="approved",
                         pool=pool))
        db.commit()
    db.close()
    return {"X-User-Id": uid, "X-User-Email": f"{uid}@company.test"}


def _approved_roadmap(rec, skills=("SQL", "Excel"), weeks=4, title="Analyst track"):
    r = ok(client.post("/api/company/roadmaps", headers=rec, json={"title": title, "skills": list(skills),
                                                                   "weeks": weeks}))
    ok(client.post(f"/api/company/roadmaps/{r['id']}/submit", headers=rec))
    ok(client.post(f"/api/company/admin/roadmaps/{r['id']}/review", headers=ADMIN, json={"approve": True}))
    return r["id"]


def _college_with_student(name, tpo_email, student_uid, link_recruiter=None):
    c = ok(client.post("/api/college/admin/colleges", headers=ADMIN, json={
        "name": name, "seat_limit": 50, "first_tpo_email": tpo_email}))
    tpo = {"X-User-Id": f"tpo-{student_uid}", "X-User-Email": tpo_email}
    ok(client.post("/api/college/me/accept", headers=tpo, json={"policy_version": V}))
    b = ok(client.post(f"/api/college/{c['id']}/batches", headers=tpo, json={"name": "CSE"}))
    if link_recruiter:
        ok(client.post(f"/api/college/admin/colleges/{c['id']}/recruiters", headers=ADMIN,
                       json={"email": f"{link_recruiter}@company.test"}))
    h = _student(student_uid)
    ok(client.post(f"/api/college/student/{student_uid}/join", headers=h, json={"code": b["join_code"]}))
    return h


def _visible(uid, h):
    return {r["id"] for r in ok(client.get(f"/api/company/student/{uid}/roadmaps", headers=h))["roadmaps"]}


def test_library_and_drafts():
    for key, (_aliases, _steps) in skill_library.LIBRARY.items():
        milestones = company_roadmaps.build_milestones([key])
        assert skill_library.validate_milestones(milestones) == [], key
    draft = company_roadmaps.draft_from_skills(["SQL", "Kubernetes", "sql"], 6)
    assert draft["skills"] == ["SQL", "Kubernetes"]
    k8s = [m for m in draft["milestones"] if m["skill"] == "Kubernetes"]
    assert [m["kind"] for m in k8s] == ["learn", "project", "test"] and k8s[0]["title"] == "Learn the essentials of Kubernetes"
    with pytest.raises(ValueError):
        company_roadmaps.draft_from_skills([], 6)
    with pytest.raises(ValueError):
        company_roadmaps.draft_from_skills(["SQL"], 30)

    rec = _recruiter("cr-text")
    ad = "We are hiring a data analyst who knows SQL, Excel and Looker Studio for reporting. " * 2
    EXTRACT_CALLS.clear()
    d1 = ok(client.post("/api/company/drafts/text", headers=rec, json={"text": ad}))
    d2 = ok(client.post("/api/company/drafts/text", headers=rec, json={"text": ad}))
    assert len(EXTRACT_CALLS) == 1 and d1 == d2  # Job match's cached read
    assert d1["skills"] == ["SQL", "Excel", "Looker Studio"] and d1["title"] == "Data Analyst"
    db = SessionLocal()  # the suite shares one database: don't leave a cached ad for Job match's own tests
    db.query(job_match.JobDescription).filter(job_match.JobDescription.id == job_match.job_key(ad)).delete()
    db.commit()
    db.close()
    assert client.post("/api/company/drafts/skills", headers=_student("cr-notrec"),
                       json={"skills": ["SQL"]}).status_code in (403, 404)


def test_lifecycle_review_and_locking():
    rec = _recruiter("cr-life")
    solo = _student("cr-life-s")
    r = ok(client.post("/api/company/roadmaps", headers=rec, json={"title": "Support track", "skills": ["Customer Service"],
                                                                   "weeks": 6}))
    assert r["status"] == "draft" and all(m["id"].startswith(f"co-{r['id'][:8]}-") for m in r["milestones"])
    edited = ok(client.patch(f"/api/company/roadmaps/{r['id']}", headers=rec, json={"milestones": [
        {**r["milestones"][0], "title": "Handle three tricky calls"}, {"title": "Role-play a refund", "skill": "Customer Service",
                                                                      "detail": "With a friend.", "kind": "practice",
                                                                      "url": "http://insecure.example"}]}))
    assert edited["milestones"][1]["url"] is None  # non-https links are dropped
    assert client.patch(f"/api/company/roadmaps/{r['id']}", headers=rec, json={"milestones": [
        {"title": "Start from zero", "skill": "x", "detail": "y"}]}).status_code == 400
    ok(client.post(f"/api/company/roadmaps/{r['id']}/submit", headers=rec))
    assert r["id"] not in _visible("cr-life-s", solo)  # not before approval
    assert client.post(f"/api/company/admin/roadmaps/{r['id']}/review", headers=rec, json={"approve": True}).status_code == 403
    assert client.post(f"/api/company/admin/roadmaps/{r['id']}/review", headers=ADMIN,
                       json={"approve": False}).status_code == 400  # needs a note
    ok(client.post(f"/api/company/admin/roadmaps/{r['id']}/review", headers=ADMIN,
                   json={"approve": False, "note": "Add a link for the second step."}))
    ok(client.post(f"/api/company/roadmaps/{r['id']}/submit", headers=rec))
    assert [x["id"] for x in ok(client.get("/api/company/admin/roadmaps", headers=ADMIN))["roadmaps"]] == [r["id"]]
    ok(client.post(f"/api/company/admin/roadmaps/{r['id']}/review", headers=ADMIN, json={"approve": True}))
    assert r["id"] in _visible("cr-life-s", solo)
    assert client.patch(f"/api/company/roadmaps/{r['id']}", headers=rec, json={"title": "Changed"}).status_code == 400
    copy = ok(client.post(f"/api/company/roadmaps/{r['id']}/duplicate", headers=rec))
    assert copy["status"] == "draft" and copy["milestones"][0]["title"] == "Handle three tricky calls"
    ok(client.post(f"/api/company/roadmaps/{r['id']}/archive", headers=rec))
    assert r["id"] not in _visible("cr-life-s", solo)
    other = _recruiter("cr-life-other")
    assert client.get(f"/api/company/roadmaps/{r['id']}", headers=other).status_code == 404


def test_roadmaps_follow_the_two_pools():
    open_rec, campus_rec = _recruiter("cr-open"), _recruiter("cr-campus", "campus")
    open_id, campus_id = _approved_roadmap(open_rec), _approved_roadmap(campus_rec, title="Campus track")
    solo = _student("cr-pool-solo")
    linked = _college_with_student("Linked College", "tpo@linked.edu", "cr-pool-linked", link_recruiter="cr-campus")
    unlinked = _college_with_student("Unlinked College", "tpo@unlinked.edu", "cr-pool-unlinked")
    pro = _student("cr-pool-pro", audience="professional")
    assert _visible("cr-pool-solo", solo) >= {open_id} and campus_id not in _visible("cr-pool-solo", solo)
    assert campus_id in _visible("cr-pool-linked", linked) and open_id not in _visible("cr-pool-linked", linked)
    assert _visible("cr-pool-unlinked", unlinked) == set()
    state = ok(client.get("/api/company/student/cr-pool-pro/roadmaps", headers=pro))
    assert state["roadmaps"] == [] and state["reason"] == "professional"
    assert client.post(f"/api/company/student/cr-pool-solo/roadmaps/{campus_id}/join", headers=solo).status_code == 404
    assert client.post(f"/api/company/student/cr-pool-pro/roadmaps/{open_id}/join", headers=pro).status_code == 404


def _forbidden_keys(obj, found=None):
    found = found if found is not None else []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(f in k.lower() for f in ("chat", "resume", "xp", "streak", "circle", "league", "email", "reminder")):
                found.append(k)
            _forbidden_keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _forbidden_keys(v, found)
    return found


def test_consent_controls_what_the_company_sees():
    rec = _recruiter("cr-see")
    rid = _approved_roadmap(rec)
    h = _student("cr-see-s")
    assert ok(client.get(f"/api/company/roadmaps/{rid}/students", headers=rec))["students"] == []
    tracks = ok(client.post(f"/api/company/student/cr-see-s/roadmaps/{rid}/join", headers=h))["tracks"]
    assert [t["roadmap_id"] for t in tracks] == [rid]
    db = SessionLocal()
    latest = (db.query(comp.ConsentRecord).filter(comp.ConsentRecord.user_id == "cr-see-s",
                                                  comp.ConsentRecord.purpose == comp.COMPANY_ROADMAP)
              .order_by(comp.ConsentRecord.created_at.desc()).first())
    assert (latest.action, latest.subject_id) == ("granted", rid)
    db.close()
    view = ok(client.get(f"/api/company/roadmaps/{rid}/students", headers=rec))
    s = view["students"][0]
    assert s["user_id"] == "cr-see-s" and [x["skill"] for x in s["skills"]] == ["SQL", "Excel"]
    assert _forbidden_keys(view["students"]) == []
    ok(client.post(f"/api/company/student/cr-see-s/roadmaps/{rid}/leave", headers=h))
    assert ok(client.get(f"/api/company/roadmaps/{rid}/students", headers=rec))["students"] == []

    ok(client.post(f"/api/company/student/cr-see-s/roadmaps/{rid}/join", headers=h))
    assert len(ok(client.get(f"/api/company/roadmaps/{rid}/students", headers=rec))["students"]) == 1
    # Joining a college changes the student's pool: the company track ends on its own.
    c = ok(client.post("/api/college/admin/colleges", headers=ADMIN, json={
        "name": "Switch College", "seat_limit": 5, "first_tpo_email": "tpo@switch.edu"}))
    tpo = {"X-User-Id": "cr-switch-tpo", "X-User-Email": "tpo@switch.edu"}
    ok(client.post("/api/college/me/accept", headers=tpo, json={"policy_version": V}))
    b = ok(client.post(f"/api/college/{c['id']}/batches", headers=tpo, json={"name": "IT"}))
    ok(client.post("/api/college/student/cr-see-s/join", headers=h, json={"code": b["join_code"]}))
    assert ok(client.get(f"/api/company/roadmaps/{rid}/students", headers=rec))["students"] == []
    assert ok(client.get("/api/company/student/cr-see-s/roadmaps", headers=h))["tracks"] == []


def test_two_tracks_max_and_tasks_in_the_weekly_plan(monkeypatch):
    rec = _recruiter("cr-plan")
    ids = [_approved_roadmap(rec, skills=(s,), title=f"{s} track") for s in ("SQL", "Excel", "Statistics")]
    h = _student("cr-plan-s")
    ok(client.post(f"/api/company/student/cr-plan-s/roadmaps/{ids[0]}/join", headers=h))
    ok(client.post(f"/api/company/student/cr-plan-s/roadmaps/{ids[1]}/join", headers=h))
    assert client.post(f"/api/company/student/cr-plan-s/roadmaps/{ids[2]}/join", headers=h).status_code == 400

    db = SessionLocal()
    acts = company_roadmaps.track_actions(db, "cr-plan-s")
    assert len(acts) <= 4 and {a["source"] for a in acts} == {"cr-plan Co"}
    assert any(a["skill"] == "SQL" for a in acts)
    # Proving SQL in a test skips its non-test steps (a self-claim wouldn't).
    when = datetime.datetime.utcnow()
    db.add(SandboxSession(id=str(uuid.uuid4()), user_id="cr-plan-s", type="theory", title="SQL", status="completed",
                          score=90, created_at=when, completed_at=when, data=json.dumps(
                              {"topic": "SQL", "result": {"skill_breakdown": {"SQL": {"correct": 9, "total": 10}}}})))
    db.commit()
    sql = [a for a in company_roadmaps.track_actions(db, "cr-plan-s") if a["skill"] == "SQL"]
    assert sql and all(a["title"] == "Take a SQL test" for a in sql)

    # The weekly plan: job tasks first, then company tasks.
    db.add(MarketSnapshot(id=str(uuid.uuid4()), user_id="cr-plan-s", target_role="Analyst",
                          snapshot_date=datetime.date.today(), top_demanded_skills="[]", emerging_skills="[]",
                          raw_data="{}", confidence_score=0.6))
    db.commit()
    from app.services import roadmap_templates
    roadmap_templates.start(db, "cr-plan-s", "data_analyst_6m")  # no AI on the template path
    job = {"id": "job-abc-sql", "type": "project", "title": "Practise SQL for the job", "skill": "SQL",
           "description": "x", "source": "Job match: Analyst"}
    monkeypatch.setattr("app.services.job_match.weekly_job_actions", lambda db, uid: [job])
    monkeypatch.setattr(central_engine, "generate_weekly_brief", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    roadmap = central_engine.get_or_create_roadmap_state(db, db.get(User, "cr-plan-s"),
                                                         db.query(MarketSnapshot).filter_by(user_id="cr-plan-s").first(),
                                                         regenerate=True)
    actions = json.loads(roadmap.weekly_focus)["primary_actions"]
    assert actions[0]["id"] == "job-abc-sql" and actions[1]["source"] == "cr-plan Co"
    db.close()


def test_company_tests_once_hidden_answers_and_results():
    GEN_CALLS.clear()
    rec = _recruiter("cr-test")
    draft = ok(client.post("/api/company/roadmaps", headers=rec, json={"title": "Draft", "skills": ["SQL"], "weeks": 4}))
    assert client.post(f"/api/company/roadmaps/{draft['id']}/tests", headers=rec,
                       json={"topic": "SQL"}).status_code == 400  # only approved roadmaps
    rid = _approved_roadmap(rec, skills=("SQL",))
    s1, s2, outsider = _student("cr-test-1"), _student("cr-test-2"), _student("cr-test-3")
    for uid, h in (("cr-test-1", s1), ("cr-test-2", s2)):
        ok(client.post(f"/api/company/student/{uid}/roadmaps/{rid}/join", headers=h))
    t = ok(client.post(f"/api/company/roadmaps/{rid}/tests", headers=rec, json={"topic": "SQL", "num_questions": 5}))
    assert GEN_CALLS == [(None, "SQL", False)] and t["members"] == 2
    assert [x["id"] for x in ok(client.get("/api/company/student/cr-test-1/tests", headers=s1))["tests"]] == [t["id"]]
    r1 = ok(client.post("/api/sandbox/theory/cr-test-1/start", headers=s1, json={"assignment_id": t["id"]}))
    r2 = ok(client.post("/api/sandbox/theory/cr-test-2/start", headers=s2, json={"assignment_id": t["id"]}))
    assert r1["questions"] == r2["questions"] and "answer_index" not in json.dumps(r1) and len(GEN_CALLS) == 1
    assert client.post("/api/sandbox/theory/cr-test-3/start", headers=outsider,
                       json={"assignment_id": t["id"]}).status_code == 404
    done = ok(client.post(f"/api/sandbox/theory/cr-test-1/sessions/{r1['session_id']}/submit", headers=s1, json={
        "answers": [q["answer_index"] for q in QUESTIONS], "integrity": {"tab_switches": 1}}))
    assert done["result"]["answers_hidden"] is True and done["result"]["questions"] == []
    view = ok(client.get(f"/api/company/roadmaps/{rid}/students", headers=rec))
    t1 = next(s for s in view["students"] if s["user_id"] == "cr-test-1")["tests"][0]
    assert t1["score"] == 100 and "Left the tab 1 time" in t1["notes"]
    rows = list(csv.reader(io.StringIO(client.get(f"/api/company/roadmaps/{rid}/students.csv",
                                                  headers=rec).content.decode("utf-8-sig"))))
    assert rows[0][-1] == f"test: {t['title']}" and len(rows) == 3
    ok(client.post(f"/api/company/tests/{t['id']}/close", headers=rec))
    review = ok(client.get(f"/api/sandbox/theory/cr-test-1/sessions/{r1['session_id']}", headers=s1))
    assert review["result"]["questions"][0]["explanation"] == "because 0"
    assert client.post(f"/api/company/tests/{t['id']}/close", headers=_recruiter("cr-test-other")).status_code == 404


def test_erasure_covers_members_and_company_content():
    rec = _recruiter("cr-erase")
    rid = _approved_roadmap(rec)
    h = _student("cr-erase-s")
    ok(client.post(f"/api/company/student/cr-erase-s/roadmaps/{rid}/join", headers=h))
    ok(client.post(f"/api/company/roadmaps/{rid}/tests", headers=rec, json={"topic": "Excel", "num_questions": 5}))
    db = SessionLocal()
    assert "company_roadmap_members" in comp.export_user_data(db, "cr-erase-s")
    comp.erase_student(db, "cr-erase-s")
    assert db.query(CompanyRoadmapMember).filter_by(user_id="cr-erase-s").count() == 0
    comp.erase_recruiter(db, "cr-erase")
    assert db.query(CompanyRoadmap).filter_by(recruiter_id="cr-erase").count() == 0
    assert db.query(CompanyTest).filter_by(recruiter_id="cr-erase").count() == 0
    db.close()
