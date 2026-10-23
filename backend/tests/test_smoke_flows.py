"""End-to-end smoke test of the main API flows (testing suite, readiness,
privacy, recruiter, school). Run from backend/:

    .venv/Scripts/python -m pytest tests/test_smoke_flows.py -q

Throwaway SQLite DB, header auth, all AI calls stubbed.
"""
import json
import os
import sys
import tempfile

_DB = os.path.join(tempfile.mkdtemp(), "smoke_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
import app.services.interview_ai as iai  # noqa: E402
import app.services.theory_test_ai as tai  # noqa: E402
import app.services.compliance as comp  # noqa: E402
import app.routers.recruiter as rr  # noqa: E402
import app.routers.school as sr  # noqa: E402

settings.ALLOW_HEADER_AUTH = True
Base.metadata.create_all(bind=engine)
client = TestClient(app)
V = comp.POLICY_VERSION


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _student(uid, role):
    db = SessionLocal()
    db.add(User(id=uid, name=uid, target_role=role, profile_data=json.dumps({"target_role": role, "name": uid})))
    db.commit()
    db.close()
    return {"X-User-Id": uid}


def test_interview_theory_and_readiness_for_a_nurse(monkeypatch):
    H = _student("nurse1", "Staff Nurse")
    monkeypatch.setattr(iai, "generate_response", lambda p, **k: "Tell me how you would handle a patient with chest pain.")
    st = ok(client.post("/api/sandbox/interview/nurse1/start", headers=H, json={"role_type": "case", "num_questions": 3}))
    assert st["settings"]["field"] == "healthcare"
    sid = st["session_id"]
    for _ in range(3):
        r = ok(client.post(f"/api/sandbox/interview/nurse1/sessions/{sid}/respond", headers=H, json={"answer": "I would assess ABC first."}))
    assert r["done"]
    monkeypatch.setattr(iai, "generate_json", lambda *a, **k: {
        "overall_score": 74, "rubric": {"communication": {"score": 8}, "technical_depth": {"score": 7},
                                        "problem_solving": {"score": 7}, "clarity": {"score": 7}},
        "per_question": [], "strengths": [], "improvements": []})
    assert ok(client.post(f"/api/sandbox/interview/nurse1/sessions/{sid}/finish", headers=H))["feedback"]["verdict"] == "ready"
    assert ok(client.get(f"/api/sandbox/interview/nurse1/sessions/{sid}", headers=H))["title"] == "Case / Scenario Interview"

    qs = [{"question": f"Q{i}", "options": ["a", "b", "c", "d"], "answer_index": 0, "explanation": "", "skill": "Pharmacology"} for i in range(5)]
    monkeypatch.setattr(tai, "generate_json", lambda *a, **k: qs)
    t = ok(client.post("/api/sandbox/theory/nurse1/start", headers=H, json={"num_questions": 5, "timed": True}))
    assert t["topic"] == "Staff Nurse" and t["time_limit_seconds"] == 300
    ok(client.post(f"/api/sandbox/theory/nurse1/sessions/{t['session_id']}/submit", headers=H, json={"answers": [0, 0, 0, 0, 1]}))

    rep = ok(client.get("/api/sandbox/report/nurse1", headers=H))
    assert rep["field"] == "healthcare" and rep["coverage"] == rep["coverage_total"] == 2
    assert rep["readiness"] == round(0.55 * 80 + 0.45 * 74)


def test_privacy_recruiter_and_school(monkeypatch):
    H = _student("acct1", "Chartered Accountant")
    ok(client.post("/api/privacy/acct1/consent", headers=H, json={"purpose": "terms_privacy", "granted": True, "policy_version": V, "age_confirmed": True}))
    ok(client.post("/api/privacy/acct1/consent", headers=H, json={"purpose": "recruiter_visibility", "granted": True}))

    R = {"X-User-Id": "rec1"}
    ok(client.post("/api/recruiter/register", headers=R, json={"name": "R", "company": "Audit Co", "accepted_terms": True, "policy_version": V}))
    app.dependency_overrides[rr.require_admin] = lambda: "admin"
    monkeypatch.setattr(rr, "_supabase_admin_email", lambda uid: None)
    ok(client.post("/api/recruiter/admin/recruiters/rec1/review", headers=R, json={"approve": True}))
    found = ok(client.post("/api/recruiter/search", headers=R, json={"target_role": "chartered accountant"}))["candidates"]
    assert found and found[0]["id"] == "acct1" and found[0]["field_label"].startswith("Finance")
    detail = ok(client.get("/api/recruiter/candidates/acct1", headers=R))
    assert "readiness" in detail and detail["field_label"].startswith("Finance")
    app.dependency_overrides.pop(rr.require_admin, None)

    child = ok(client.post("/api/school/acct1/children", headers=H, json={
        "first_name": "Kiara", "grade": 9, "pin": "2468", "is_parent_or_guardian": True, "consent": True}))
    ok(client.post(f"/api/school/acct1/children/{child['id']}/verify-pin", headers=H, json={"pin": "2468"}))

    monkeypatch.setattr(comp, "delete_auth_user", lambda uid: True)
    ok(client.request("DELETE", "/api/privacy/acct1", headers=H, json={"confirm": "DELETE"}))
    db = SessionLocal()
    assert db.query(User).filter_by(id="acct1").count() == 0
    db.close()
