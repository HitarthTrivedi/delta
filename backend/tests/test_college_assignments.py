"""Delta for College, P4: roadmaps and tests a college sets for a batch.
Batch roadmaps apply to members (now and on joining) and can't be stopped
while they're members; batch tests are generated once, the answer key never
reaches a student while open, only the batch can take them, and results carry
integrity notes.

    .venv/Scripts/python -m pytest tests/test_college_assignments.py -q
"""
import csv
import datetime
import io
import json
import os
import sys
import tempfile

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "college_assignments_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import RoadmapEnrollment, User  # noqa: E402
from app.services import college_assignments  # noqa: E402
import app.services.compliance as comp  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
ADMIN = {"X-User-Id": "as-boss", "X-User-Email": "boss@delta.test"}
V = comp.POLICY_VERSION
CALLS = []
QUESTIONS = [{"question": f"Q{i}?", "options": ["a", "b", "c", "d"], "skill": "Arrays" if i < 3 else "Trees",
              "answer_index": i % 4, "explanation": f"because {i}"} for i in range(5)]


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    from app.limiter import limiter
    limiter.reset()  # every test request shares one client address
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "boss@delta.test")

    def fake_generate(user_id, topic, n, difficulty, category, area, personalize=True):
        CALLS.append((user_id, topic, personalize))
        return topic or "Aptitude", [dict(q) for q in QUESTIONS[:n]]
    monkeypatch.setattr(college_assignments, "generate_test", fake_generate)


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _student(uid):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=f"{uid} Student", profile_data=json.dumps({"audience": "student"})))
        db.commit()
        comp.record_consent(db, uid, comp.TERMS, True)
    db.close()
    return {"X-User-Id": uid, "X-User-Email": f"{uid}@gmail.com"}


def _college(name, tpo_uid, tpo_email):
    c = ok(client.post("/api/college/admin/colleges", headers=ADMIN, json={
        "name": name, "seat_limit": 100, "first_tpo_email": tpo_email}))
    tpo = {"X-User-Id": tpo_uid, "X-User-Email": tpo_email}
    ok(client.post("/api/college/me/accept", headers=tpo, json={"policy_version": V}))
    return c["id"], tpo


def _join(uid, code, roll_no=None):
    h = _student(uid)
    ok(client.post(f"/api/college/student/{uid}/join", headers=h, json={"code": code, "roll_no": roll_no}))
    return h


def _enrollment(uid):
    db = SessionLocal()
    e = db.query(RoadmapEnrollment).filter(RoadmapEnrollment.user_id == uid).first()
    out = (e.template_id, e.status, e.assigned_by_batch_id) if e else None
    db.close()
    return out


def test_batch_roadmap_applies_to_members_and_locks_until_they_leave():
    cid, tpo = _college("Plan College", "as-ptpo", "tpo@plan.edu")
    b = ok(client.post(f"/api/college/{cid}/batches", headers=tpo, json={"name": "CSE 2027"}))
    s1 = _join("as-p1", b["join_code"])
    target = (datetime.date.today() + datetime.timedelta(weeks=20)).isoformat()
    t = ok(client.put(f"/api/college/{cid}/batches/{b['id']}/template", headers=tpo,
                      json={"template_id": "placement_6m", "target_date": target}))["template"]
    assert t["template_id"] == "placement_6m" and t["following"] == 1
    assert _enrollment("as-p1") == ("placement_6m", "active", b["id"])
    assert client.post("/api/templates/user/as-p1/stop", headers=s1).status_code == 403
    assert ok(client.get("/api/templates/user/as-p1", headers=s1))["current"]["college_assigned"] is True

    _join("as-p2", b["join_code"])  # joins later: gets it too
    assert _enrollment("as-p2") == ("placement_6m", "active", b["id"])
    batches = ok(client.get(f"/api/college/{cid}/batches", headers=tpo))["batches"]
    assert batches[0]["template"]["following"] == 2

    ok(client.post("/api/college/student/as-p1/leave", headers=s1))  # leaving: keeps it, but as their own choice
    assert _enrollment("as-p1") == ("placement_6m", "active", None)
    ok(client.post("/api/templates/user/as-p1/stop", headers=s1))

    assert ok(client.put(f"/api/college/{cid}/batches/{b['id']}/template", headers=tpo,
                         json={"template_id": None}))["template"] is None
    assert _enrollment("as-p2") == ("placement_6m", "active", None)  # released, not taken away
    assert client.put(f"/api/college/{cid}/batches/{b['id']}/template", headers=tpo,
                      json={"template_id": "nope"}).status_code == 404


def test_pending_member_gets_the_roadmap_only_when_approved():
    cid, tpo = _college("Pending College", "as-qtpo", "tpo@pending.edu")
    ok(client.post(f"/api/college/{cid}/roster", headers=tpo, json={
        "csv": "Roll No,Name,Batch,Department\nR1,Ravi,2027,CSE\n", "dry_run": False}))
    b = ok(client.get(f"/api/college/{cid}/batches", headers=tpo))["batches"][0]
    ok(client.put(f"/api/college/{cid}/batches/{b['id']}/template", headers=tpo, json={"template_id": "swe_google_12m"}))
    _join("as-q1", b["join_code"], roll_no="NOT-ON-ROSTER")  # waits for the TPO
    assert _enrollment("as-q1") is None
    member = ok(client.get(f"/api/college/{cid}/members", headers=tpo))["members"][0]
    ok(client.post(f"/api/college/{cid}/members/{member['id']}/approve", headers=tpo))
    assert _enrollment("as-q1") == ("swe_google_12m", "active", b["id"])


def test_batch_test_is_generated_once_and_hides_answers_while_open():
    CALLS.clear()
    cid, tpo = _college("Test College", "as-ttpo", "tpo@test.edu")
    b = ok(client.post(f"/api/college/{cid}/batches", headers=tpo, json={"name": "IT 2026"}))
    other = ok(client.post(f"/api/college/{cid}/batches", headers=tpo, json={"name": "ECE 2026"}))
    s1, s2 = _join("as-t1", b["join_code"]), _join("as-t2", b["join_code"])
    s3 = _join("as-t3", other["join_code"])
    outsider = _student("as-t4")
    due = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    test = ok(client.post(f"/api/college/{cid}/batches/{b['id']}/tests", headers=tpo, json={
        "topic": "Data Structures", "num_questions": 5, "due_date": due}))
    assert CALLS == [(None, "Data Structures", False)]  # one call, no learner data
    assert test["members"] == 2 and test["open"] is True and test["time_limit_seconds"] == 300

    mine = ok(client.get("/api/college/student/as-t1/tests", headers=s1))["tests"]
    assert [(t["id"], t["status"]) for t in mine] == [(test["id"], "not started")]
    assert ok(client.get("/api/college/student/as-t3/tests", headers=s3))["tests"] == []

    r1 = ok(client.post("/api/sandbox/theory/as-t1/start", headers=s1, json={"assignment_id": test["id"]}))
    r2 = ok(client.post("/api/sandbox/theory/as-t2/start", headers=s2, json={"assignment_id": test["id"]}))
    assert r1["questions"] == r2["questions"] and len(CALLS) == 1
    assert "answer_index" not in json.dumps(r1) and "explanation" not in json.dumps(r1)
    again = ok(client.post("/api/sandbox/theory/as-t1/start", headers=s1, json={"assignment_id": test["id"]}))
    assert again["session_id"] == r1["session_id"]  # resumes, doesn't restart
    for h, uid in ((s3, "as-t3"), (outsider, "as-t4")):
        assert client.post(f"/api/sandbox/theory/{uid}/start", headers=h,
                           json={"assignment_id": test["id"]}).status_code == 404

    done = ok(client.post(f"/api/sandbox/theory/as-t1/sessions/{r1['session_id']}/submit", headers=s1, json={
        "answers": [q["answer_index"] for q in QUESTIONS], "integrity": {"tab_switches": 2}}))
    assert done["result"]["score"] == 100 and done["result"]["answers_hidden"] is True
    assert done["result"]["questions"] == [] and "explanation" not in json.dumps(done)
    view = ok(client.get(f"/api/sandbox/theory/as-t1/sessions/{r1['session_id']}", headers=s1))
    assert view["result"]["answers_hidden"] is True
    assert client.post("/api/sandbox/theory/as-t1/start", headers=s1,
                       json={"assignment_id": test["id"]}).status_code == 400  # one attempt

    res = ok(client.get(f"/api/college/{cid}/tests/{test['id']}/results", headers=tpo))
    assert [(s["user_id"], s["status"], s["score"]) for s in res["students"]] == [
        ("as-t1", "done", 100), ("as-t2", "started", None)]
    assert "Left the tab 2 times" in res["students"][0]["notes"]
    rows = list(csv.reader(io.StringIO(client.get(f"/api/college/{cid}/exports/test_results.csv", headers=tpo,
                                                  params={"assignment_id": test["id"]}).content.decode("utf-8-sig"))))
    assert rows[0] == ["roll_no", "name", "test", "status", "score", "completed_at", "notes"] and len(rows) == 3

    ok(client.post(f"/api/college/{cid}/tests/{test['id']}/close", headers=tpo))
    view = ok(client.get(f"/api/sandbox/theory/as-t1/sessions/{r1['session_id']}", headers=s1))
    assert view["result"]["questions"][0]["explanation"] == "because 0"  # closed: review unlocked
    assert client.post(f"/api/sandbox/theory/as-t2/sessions/{r2['session_id']}/submit", headers=s2,
                       json={"answers": [0] * 5}).status_code == 200


def test_staff_rules_and_generator_failure(monkeypatch):
    cid, tpo = _college("Rules College", "as-rtpo", "tpo@rules.edu")
    b = ok(client.post(f"/api/college/{cid}/batches", headers=tpo, json={"name": "MECH"}))
    ok(client.post(f"/api/college/{cid}/admins", headers=tpo, json={"email": "prof@rules.edu", "role": "faculty"}))
    prof = {"X-User-Id": "as-prof", "X-User-Email": "prof@rules.edu"}
    ok(client.post("/api/college/me/accept", headers=prof, json={"policy_version": V}))
    assert client.post(f"/api/college/{cid}/batches/{b['id']}/tests", headers=prof,
                       json={"topic": "Thermo"}).status_code == 403
    assert client.put(f"/api/college/{cid}/batches/{b['id']}/template", headers=prof,
                      json={"template_id": "placement_6m"}).status_code == 403
    assert ok(client.get(f"/api/college/{cid}/batches/{b['id']}/tests", headers=prof))["tests"] == []
    assert len(ok(client.get("/api/templates", headers=tpo))["catalog"]) == 5
    assert client.post(f"/api/college/{cid}/batches/{b['id']}/tests", headers=tpo, json={}).status_code == 400

    def broken(*_a, **_k):
        raise ValueError("unusable")
    monkeypatch.setattr(college_assignments, "generate_test", broken)
    assert client.post(f"/api/college/{cid}/batches/{b['id']}/tests", headers=tpo,
                       json={"topic": "Thermo"}).status_code == 503
    assert ok(client.get(f"/api/college/{cid}/batches/{b['id']}/tests", headers=tpo))["tests"] == []
    other_cid, other_tpo = _college("Other Rules", "as-otpo", "tpo@other-rules.edu")
    assert client.get(f"/api/college/{cid}/batches/{b['id']}/tests", headers=other_tpo).status_code == 403


def test_open_college_tests_join_the_weekly_plan():
    cid, tpo = _college("Week College", "as-wtpo", "tpo@week.edu")
    b = ok(client.post(f"/api/college/{cid}/batches", headers=tpo, json={"name": "CSE"}))
    s = _join("as-w1", b["join_code"])
    test = ok(client.post(f"/api/college/{cid}/batches/{b['id']}/tests", headers=tpo, json={
        "category": "aptitude", "area": "logical", "num_questions": 5}))
    db = SessionLocal()
    actions = college_assignments.weekly_college_actions(db, "as-w1")
    assert [a["url"] for a in actions] == [f"/practice/theory?assignment={test['id']}"]
    db.close()
    r = ok(client.post("/api/sandbox/theory/as-w1/start", headers=s, json={"assignment_id": test["id"]}))
    ok(client.post(f"/api/sandbox/theory/as-w1/sessions/{r['session_id']}/submit", headers=s, json={"answers": [0] * 5}))
    db = SessionLocal()
    assert college_assignments.weekly_college_actions(db, "as-w1") == []
    db.close()
