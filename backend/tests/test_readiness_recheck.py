"""Master Plan backlog #9: verified readiness re-check. A strictly timed
re-check from a shared bank (made once, no learner data, never repeated)
plus one coding problem for tech fields; verified only when it holds the
practice score with no serious integrity flags; recruiters see passes only
and can ask a candidate to verify.

    .venv/Scripts/python -m pytest tests/test_readiness_recheck.py -q
"""
import datetime
import json
import os
import sys
import tempfile
import uuid

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "readiness_recheck_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (CodingPackage, ReadinessCheck, Recruiter, SandboxSession, User, VerificationRequest,  # noqa: E402
                        VerifiedItem, VerifiedSeen)
from app.services import code_runner, jobs, sandbox_problems, theory_test_ai, verification  # noqa: E402
import app.services.compliance as comp  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
GEN_CALLS = []
PACKAGE = {"statement": "Sum two numbers.", "examples": [{"input": "1 2", "output": "3", "explanation": "1+2"}],
           "starter_code": {"python": "a, b = map(int, input().split())\n"},
           "test_cases": [{"input": "1 2", "expected_output": "3"}, {"input": "5 5", "expected_output": "10"}]}


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    from app.limiter import limiter
    limiter.reset()  # every test request shares one client address
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(settings, "AI_CAPS_JSON", "")

    def fake_generate(user_id, topic, n=10, difficulty="medium", category="technical", area=None, personalize=True):
        GEN_CALLS.append((user_id, topic, personalize, difficulty))
        return topic, [{"question": f"{topic} Q{i} {uuid.uuid4().hex[:6]}?", "options": ["a", "b", "c", "d"],
                        "answer_index": i % 4, "explanation": "x", "skill": topic} for i in range(n)]
    monkeypatch.setattr(theory_test_ai, "generate_test", fake_generate)
    monkeypatch.setattr(sandbox_problems, "generate_json", lambda *a, **k: json.loads(json.dumps(PACKAGE)))
    sandbox_problems._package_cache.clear()
    expected = {c["input"]: c["expected_output"] for c in PACKAGE["test_cases"]}
    # The fake runner "solves" the problem when the code says SOLVE, otherwise prints nothing.
    monkeypatch.setattr(code_runner, "run_code", lambda lang, code, stdin="": {
        "stdout": expected.get(stdin, "") if "SOLVE" in code else "", "stderr": "", "exit_code": 0, "error": None})


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _student(uid, field="cs_ai", coding=True, dob=None):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=uid, date_of_birth=dob,
                    profile_data=json.dumps({"audience": "student", "field": field, "target_role": "Engineer"})))
        db.commit()
        comp.record_consent(db, uid, comp.TERMS, True)
        when = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        db.add(SandboxSession(id=str(uuid.uuid4()), user_id=uid, type="theory", title="SQL test", status="completed",
                              score=80, created_at=when, completed_at=when, data=json.dumps(
                                  {"topic": "SQL", "result": {"skill_breakdown": {"SQL": {"correct": 4, "total": 5}}}})))
        if coding:
            db.add(SandboxSession(id=str(uuid.uuid4()), user_id=uid, type="coding", title="Two Sum", status="completed",
                                  score=100, created_at=when, completed_at=when, data=json.dumps({"topic": "Arrays"})))
        db.commit()
    db.close()
    return {"X-User-Id": uid, "X-User-Email": f"{uid}@gmail.com"}


def _ready_check(uid, h):
    """Start, letting the bank job run when the questions aren't ready yet."""
    r = client.post(f"/api/verify/{uid}/start", headers=h)
    if r.status_code == 202:
        while (job := jobs.run_next()) is not None:  # run everything queued, including this bank job
            assert job.status == "done", job.error
        r = client.post(f"/api/verify/{uid}/start", headers=h)
    return ok(r)["check"]


def _answers(check_id):
    db = SessionLocal()
    c = db.get(ReadinessCheck, check_id)
    s = db.get(SandboxSession, json.loads(c.parts)["theory"]["session_id"])
    answers = [q["answer_index"] for q in json.loads(s.data)["questions"]]
    db.close()
    return answers


def _pass_check(uid, h, tab_switches=0):
    check = _ready_check(uid, h)
    ok(client.post(f"/api/verify/{uid}/checks/{check['id']}/theory", headers=h,
                   json={"answers": _answers(check["id"]), "integrity": {"tab_switches": tab_switches}}))
    if "coding" in check["parts"]:
        return ok(client.post(f"/api/verify/{uid}/checks/{check['id']}/coding/submit", headers=h,
                              json={"language": "python", "code": "# SOLVE"}))["check"]
    return ok(client.get(f"/api/verify/{uid}", headers=h))["last"]


def test_full_pass_with_bank_job_and_no_answer_key():
    GEN_CALLS.clear()
    h = _student("rc-pass")
    first = client.post("/api/verify/rc-pass/start", headers=h)
    assert first.status_code == 202 and first.json()["preparing"]["kind"] == "verified_bank"
    assert jobs.run_next().status == "done"
    assert len(GEN_CALLS) == 3 and all(c[0] is None and c[2] is False and c[3] == "medium" for c in GEN_CALLS)
    db = SessionLocal()
    assert db.query(CodingPackage).count() >= 1
    db.close()

    check = ok(client.post("/api/verify/rc-pass/start", headers=h))["check"]
    body = json.dumps(check)
    assert len(check["parts"]["theory"]["questions"]) == 12
    assert "answer_index" not in body and "test_cases" not in body and "expected_output" not in body
    assert check["parts"]["coding"]["statement"] == PACKAGE["statement"]
    again = ok(client.post("/api/verify/rc-pass/start", headers=h))["check"]
    assert again["id"] == check["id"]  # one re-check at a time: it resumes

    after = ok(client.post(f"/api/verify/rc-pass/checks/{check['id']}/theory", headers=h,
                           json={"answers": _answers(check["id"])}))
    assert after["parts"]["theory"]["done"] is True and "answer_index" not in json.dumps(after)
    sub = ok(client.post(f"/api/verify/rc-pass/checks/{check['id']}/coding/submit", headers=h,
                         json={"language": "python", "code": "print('SOLVE')"}))
    assert set(sub) == {"passed", "total", "submits_left", "check"} and "expected_output" not in json.dumps(sub)
    assert sub["check"]["status"] == "verified" and sub["check"]["score"] == 100 and sub["check"]["baseline"] == 90

    status = ok(client.get("/api/verify/rc-pass", headers=h))
    assert status["verified"]["score"] == 100 and status["current"] is None
    # The normal sandbox can't reach re-check sessions (no deadline bypass, no answer key).
    db = SessionLocal()
    sid = json.loads(db.get(ReadinessCheck, check["id"]).parts)["theory"]["session_id"]
    db.close()
    assert client.get(f"/api/sandbox/theory/rc-pass/sessions/{sid}", headers=h).status_code == 404


def test_eligibility(monkeypatch):
    h = _student("rc-none", coding=False)
    db = SessionLocal()
    db.query(SandboxSession).filter_by(user_id="rc-none").delete()
    db.commit()
    db.close()
    assert client.post("/api/verify/rc-none/start", headers=h).status_code == 400
    minor = _student("rc-minor", dob=datetime.date.today() - datetime.timedelta(days=365 * 16))
    assert client.post("/api/verify/rc-minor/start", headers=minor).status_code == 403
    assert ok(client.get("/api/verify/rc-minor", headers=minor))["reason"] == "minor"
    monkeypatch.setattr(settings, "AI_CAPS_JSON", '{"solo": {"readiness_check": 1}}')
    h = _student("rc-cap", field="marketing", coding=False)
    _pass_check("rc-cap", h)
    capped = client.post("/api/verify/rc-cap/start", headers=h)
    assert capped.status_code == 429 and "re-checks" in capped.json()["detail"]


def test_misses_stay_private_and_wait_for_the_retry(monkeypatch):
    h = _student("rc-late", field="marketing", coding=False)  # non-tech: questions only
    check = _ready_check("rc-late", h)
    assert "coding" not in check["parts"]
    db = SessionLocal()
    c = db.get(ReadinessCheck, check["id"])
    parts = json.loads(c.parts)
    parts["theory"]["deadline"] = (datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).isoformat()
    c.parts = json.dumps(parts)
    db.commit()
    db.close()
    late = ok(client.post(f"/api/verify/rc-late/checks/{check['id']}/theory", headers=h,
                          json={"answers": _answers(check["id"])}))  # all correct, but too late
    status = ok(client.get("/api/verify/rc-late", headers=h))
    assert status["last"]["status"] == "not_verified" and status["last"]["score"] == 0
    assert "Went past the time limit" in status["last"]["flags"] and status["reason"] == "cooldown"
    retry = client.post("/api/verify/rc-late/start", headers=h)
    assert retry.status_code == 400 and "try again on" in retry.json()["detail"]

    flagged = _student("rc-tabs", field="marketing", coding=False)
    result = _pass_check("rc-tabs", flagged, tab_switches=5)  # full marks, but left the tab 5 times
    assert result["status"] == "not_verified" and any("Left the tab" in f for f in result["flags"])

    again = _student("rc-again", field="marketing", coding=False)
    assert _pass_check("rc-again", again)["status"] == "verified"
    assert ok(client.get("/api/verify/rc-again", headers=again))["verified"]
    assert _pass_check("rc-again", again, tab_switches=5)["status"] == "not_verified"  # a later miss replaces the pass
    assert ok(client.get("/api/verify/rc-again", headers=again))["verified"] is None
    db = SessionLocal()
    assert verification.verified_ids(db, ["rc-again", "rc-tabs"]) == set()
    db.close()


def test_coding_limits_and_abandoned_checks():
    h = _student("rc-code")
    check = _ready_check("rc-code", h)
    for left in (2, 1):
        r = ok(client.post(f"/api/verify/rc-code/checks/{check['id']}/coding/submit", headers=h,
                           json={"language": "python", "code": "print(0)"}))
        assert (r["passed"], r["submits_left"]) == (0, left)
    third = ok(client.post(f"/api/verify/rc-code/checks/{check['id']}/coding/submit", headers=h,
                           json={"language": "python", "code": "print(0)"}))
    assert third["submits_left"] == 0 and third["check"]["parts"]["coding"]["done"] is True
    assert client.post(f"/api/verify/rc-code/checks/{check['id']}/coding/submit", headers=h,
                       json={"language": "python", "code": "# SOLVE"}).status_code == 400  # no 4th submit

    # The student walks away from the questions: once time is up, the re-check settles itself.
    db = SessionLocal()
    c = db.get(ReadinessCheck, check["id"])
    parts = json.loads(c.parts)
    for p in parts.values():
        p["deadline"] = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat()
    c.parts = json.dumps(parts)
    db.commit()
    db.close()
    status = ok(client.get("/api/verify/rc-code", headers=h))
    assert status["current"] is None and status["last"]["status"] == "not_verified" and status["last"]["score"] == 0


def test_bank_is_shared_and_never_repeats_for_a_learner():
    _pass_check("rc-pass", _student("rc-pass"))  # second re-check for the same student
    db = SessionLocal()
    seen = [r.item_id for r in db.query(VerifiedSeen).filter_by(user_id="rc-pass")]
    db.close()
    assert len(seen) == len(set(seen)) == 24  # two re-checks, no question twice
    GEN_CALLS.clear()
    h2 = _student("rc-other")  # same field and tested skill as rc-pass's first re-check
    _ready_check("rc-other", h2)
    assert GEN_CALLS == []  # the bank made for one learner serves the next


def test_a_failed_package_is_never_kept(monkeypatch):
    monkeypatch.setattr(sandbox_problems, "generate_json", lambda *a, **k: {})
    package = sandbox_problems.generate_problem_package("Arrays", "No Such Problem", "Easy")
    assert package["fallback"] is True
    db = SessionLocal()
    assert db.get(CodingPackage, "Arrays::No Such Problem") is None
    db.close()
    assert "No Such Problem" not in str(sandbox_problems._package_cache)


def test_recruiters_see_passes_only_and_can_ask():
    rec_h = {"X-User-Id": "rc-rec", "X-User-Email": "rc-rec@company.test"}
    db = SessionLocal()
    db.add(Recruiter(id="rc-rec", email="rc-rec@company.test", name="R", company="Acme", status="approved", pool="open"))
    db.commit()
    db.close()
    hidden = _student("rc-hidden", field="marketing", coding=False)
    assert client.post("/api/verify/candidates/rc-hidden/request", headers=rec_h).status_code == 404  # not opted in

    h = _student("rc-cand", field="marketing", coding=False)
    ok(client.post("/api/privacy/rc-cand/consent", headers=h, json={"purpose": "recruiter_visibility", "granted": True}))
    req = ok(client.post("/api/verify/candidates/rc-cand/request", headers=rec_h))["request"]
    again = ok(client.post("/api/verify/candidates/rc-cand/request", headers=rec_h))["request"]
    assert req["status"] == again["status"] == "open"
    status = ok(client.get("/api/verify/rc-cand", headers=h))
    assert [r["company"] for r in status["requests"]] == ["Acme"]

    detail = ok(client.get("/api/recruiter/candidates/rc-cand", headers=rec_h))
    assert detail["verification"] == {"verified": False} and detail["verification_request"]["status"] == "open"
    _pass_check("rc-cand", h)
    detail = ok(client.get("/api/recruiter/candidates/rc-cand", headers=rec_h))
    assert detail["verification"]["verified"] is True and detail["verification"]["score"] == 100
    assert detail["verification_request"]["status"] == "done"
    found = ok(client.post("/api/recruiter/search", headers=rec_h, json={}))["candidates"]
    assert next(c for c in found if c["id"] == "rc-cand")["verified"] is True
    assert ok(client.get("/api/verify/rc-cand", headers=h))["requests"] == []

    db = SessionLocal()
    comp.erase_student(db, "rc-cand")
    assert db.query(ReadinessCheck).filter_by(user_id="rc-cand").count() == 0
    assert db.query(VerificationRequest).filter_by(user_id="rc-cand").count() == 0
    comp.erase_recruiter(db, "rc-rec")
    assert db.query(VerificationRequest).filter_by(recruiter_id="rc-rec").count() == 0
    db.close()
