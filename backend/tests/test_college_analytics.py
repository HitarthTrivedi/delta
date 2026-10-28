"""Delta for College, P2: TPO analytics and exports. Readiness in bulk,
batch dashboards, the at-risk rules, the student drill-down (only what the
college may see) and CSV exports.

    .venv/Scripts/python -m pytest tests/test_college_analytics.py -q
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

_DB = os.path.join(tempfile.mkdtemp(), "college_analytics_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CollegeMember, DailyActivity, SandboxSession, User  # noqa: E402
from app.services import college_analytics as ca  # noqa: E402
from app.services.readiness import compute_readiness, readiness_bulk  # noqa: E402
import app.services.compliance as comp  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
ADMIN = {"X-User-Id": "ca-boss", "X-User-Email": "boss@delta.test"}
V = comp.POLICY_VERSION
TODAY = datetime.date.today()


@pytest.fixture(autouse=True)
def header_auth(monkeypatch):
    from app.limiter import limiter
    limiter.reset()  # every test request shares one client address
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "boss@delta.test")


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _student(uid, profile=None, name=None):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=name or f"{uid} Student",
                    profile_data=json.dumps(profile or {"audience": "student"})))
        db.commit()
        comp.record_consent(db, uid, comp.TERMS, True)
    db.close()
    return {"X-User-Id": uid, "X-User-Email": f"{uid}@gmail.com"}


def _college(name, tpo_uid, tpo_email):
    c = ok(client.post("/api/college/admin/colleges", headers=ADMIN, json={
        "name": name, "seat_limit": 100, "first_tpo_email": tpo_email}))
    tpo = {"X-User-Id": tpo_uid, "X-User-Email": tpo_email}
    ok(client.post("/api/college/me/accept", headers=tpo, json={"policy_version": V}))
    return c, tpo


def _batch(cid, tpo, name):
    return ok(client.post(f"/api/college/{cid}/batches", headers=tpo, json={"name": name}))


def _join(uid, code, roll_no=None, joined_days_ago=0, **student):
    h = _student(uid, **student)
    ok(client.post(f"/api/college/student/{uid}/join", headers=h, json={"code": code, "roll_no": roll_no}))
    if joined_days_ago:
        db = SessionLocal()
        m = db.query(CollegeMember).filter(CollegeMember.user_id == uid).first()
        m.joined_at = datetime.datetime.utcnow() - datetime.timedelta(days=joined_days_ago)
        db.commit()
        db.close()
    return h


def _session(uid, type_, score, days_ago=1, status="completed", **data):
    db = SessionLocal()
    when = datetime.datetime.utcnow() - datetime.timedelta(days=days_ago)
    db.add(SandboxSession(id=str(uuid.uuid4()), user_id=uid, type=type_, title=f"{type_} {score}", status=status,
                          score=score, data=json.dumps(data), created_at=when,
                          completed_at=when if status == "completed" else None))
    db.commit()
    db.close()


def _active(uid, *days_ago):
    db = SessionLocal()
    for d in days_ago:
        db.merge(DailyActivity(user_id=uid, local_date=TODAY - datetime.timedelta(days=d), xp=10, actions=1))
    db.commit()
    db.close()


def _theory(uid, score, skills, days_ago=1, **extra):
    _session(uid, "theory", score, days_ago,
             result={"skill_breakdown": {k: {"correct": c, "total": t} for k, (c, t) in skills.items()}, **extra})


def test_bulk_readiness_matches_per_learner():
    _student("ca-r1")
    _theory("ca-r1", 80, {"SQL": (4, 5), "Python": (1, 4)})
    _session("ca-r1", "coding", None, topic="Arrays")
    _session("ca-r1", "interview", 70, feedback={"rubric": {"communication": {"score": 6}}})
    _student("ca-r2", {"audience": "student", "field": "marketing"})
    _theory("ca-r2", 40, {"Branding": (1, 5)})
    _student("ca-r3")
    _session("ca-r3", "coding", None, status="in_progress", submissions=2, best_pass_pct=50, topic="Graphs")
    _student("ca-r4")
    _student("ca-r5", name="No Sessions")
    _session("ca-r5", "theory", 90, status="in_progress")
    ids = [f"ca-r{i}" for i in range(1, 6)]
    db = SessionLocal()
    bulk = readiness_bulk(db, ids)
    assert bulk == {uid: compute_readiness(db, uid) for uid in ids}
    assert readiness_bulk(db, []) == {}
    r1 = bulk["ca-r1"]
    # theory 80 (0.35), coding 100 (0.35), interview 70 (0.30) -> 84
    assert (r1["readiness"], r1["label"], r1["coverage"]) == (84, "Interview-ready", 3)
    assert {s["skill"]: s["score"] for s in r1["skills"]} == {"SQL": 80, "Python": 25, "Arrays": 100}
    assert bulk["ca-r4"]["readiness"] is None and bulk["ca-r5"]["label"] == "Not started"
    db.close()


def test_at_risk_rule_boundaries():
    def reasons(last_active=None, joined=30, readiness=60, last_practice=1):
        return ca.risk_reasons(
            today=TODAY, joined=TODAY - datetime.timedelta(days=joined),
            last_active=TODAY - datetime.timedelta(days=last_active) if last_active is not None else None,
            readiness=readiness,
            last_practice=TODAY - datetime.timedelta(days=last_practice) if last_practice is not None else None)

    assert reasons(last_active=6) == []
    assert reasons(last_active=7) == ["inactive_7d"]
    assert reasons(joined=6, last_practice=None) == []  # new and never active: not yet
    assert reasons(joined=7, last_practice=None) == ["inactive_7d"]
    assert reasons(last_active=0, readiness=44) == ["low_readiness"]
    assert reasons(last_active=0, readiness=45) == []
    assert reasons(last_active=0, readiness=None) == []  # nothing taken yet isn't "low"
    assert reasons(last_active=0, last_practice=20) == []
    assert reasons(last_active=0, last_practice=21) == ["no_practice_21d"]
    assert reasons(joined=30, readiness=30, last_practice=None) == ["inactive_7d", "low_readiness", "no_practice_21d"]


def test_batch_dashboard_overview_and_access():
    c, tpo = _college("Dash College", "ca-dtpo", "tpo@dash.edu")
    cid = c["id"]
    b = _batch(cid, tpo, "CSE 2027")
    other = _batch(cid, tpo, "ECE 2027")
    _join("ca-good", b["join_code"], joined_days_ago=40)
    _theory("ca-good", 90, {"DBMS": (9, 10), "OS": (2, 5)})
    _active("ca-good", 0, 1, 8)
    _join("ca-weak", b["join_code"], joined_days_ago=40)
    _theory("ca-weak", 30, {"DBMS": (1, 5), "OS": (1, 5)}, days_ago=25)
    _active("ca-weak", 10)
    _join("ca-new", b["join_code"])  # joined today, nothing done yet
    _join("ca-gone", b["join_code"], joined_days_ago=40)
    _join("ca-ece", other["join_code"], joined_days_ago=3)
    _active("ca-ece", 0)

    d = ok(client.get(f"/api/college/{cid}/batches/{b['id']}/dashboard", headers=tpo))
    assert d["students"] == 4 and d["batch"]["name"] == "CSE 2027"
    buckets = {x["label"]: x["students"] for x in d["buckets"]}
    assert buckets == {"Interview-ready": 1, "Almost there": 0, "Building up": 0, "Just starting": 1, "Not started": 2}
    assert d["avg_readiness"] == 60 and d["active_7d_pct"] == 25.0 and d["active_30d_pct"] == 50.0
    risky = [(s["user_id"], len(s["reasons"])) for s in d["at_risk_students"]]
    assert risky == [("ca-weak", 3), ("ca-gone", 2)]
    assert d["weak_skills"][0] == {"skill": "OS", "students_weak": 2, "students_tested": 2, "avg_score": 30}
    assert len(d["trend"]) == ca.TREND_WEEKS and d["trend"][-1]["active_pct"] == 25.0
    assert all("active_dates" not in s and "skills" not in s for s in d["students_list"])

    # Removed and pending students drop out at once (cache key follows membership).
    gone = next(m for m in ok(client.get(f"/api/college/{cid}/members", headers=tpo))["members"]
                if m["name"] == "ca-gone Student")
    ok(client.delete(f"/api/college/{cid}/members/{gone['id']}", headers=tpo))
    d = ok(client.get(f"/api/college/{cid}/batches/{b['id']}/dashboard", headers=tpo))
    assert d["students"] == 3 and "ca-gone" not in {s["user_id"] for s in d["students_list"]}
    assert client.get(f"/api/college/{cid}/students/ca-gone", headers=tpo).status_code == 404

    o = ok(client.get(f"/api/college/{cid}/overview", headers=tpo))
    assert o["students"] == 4 and [(x["name"], x["students"]) for x in o["batches"]] == [("CSE 2027", 3), ("ECE 2027", 1)]

    # Faculty can read; another college's TPO and students can't.
    ok(client.post(f"/api/college/{cid}/admins", headers=tpo, json={"email": "prof@dash.edu", "role": "faculty"}))
    prof = {"X-User-Id": "ca-prof", "X-User-Email": "prof@dash.edu"}
    ok(client.post("/api/college/me/accept", headers=prof, json={"policy_version": V}))
    ok(client.get(f"/api/college/{cid}/overview", headers=prof))
    _, outsider = _college("Other College", "ca-otpo", "tpo@other.edu")
    for h in (outsider, _student("ca-good")):
        assert client.get(f"/api/college/{cid}/batches/{b['id']}/dashboard", headers=h).status_code == 403
        assert client.get(f"/api/college/{cid}/students/ca-good", headers=h).status_code == 403
    assert client.get(f"/api/college/{cid}/batches/nope/dashboard", headers=tpo).status_code == 404


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_student_drilldown_shows_only_what_the_college_may_see():
    c, tpo = _college("View College", "ca-vtpo", "tpo@view.edu")
    b = _batch(c["id"], tpo, "IT 2026")
    _join("ca-view", b["join_code"], joined_days_ago=10)
    _theory("ca-view", 70, {"Networks": (7, 10)}, time_taken_seconds=20, total=10)
    _session("ca-view", "interview", 65, feedback={"rubric": {"communication": {"score": 6}}},
             integrity={"tab_switches": 3, "pastes": 0, "pasted_chars": 0})
    _active("ca-view", 0, 2)
    v = ok(client.get(f"/api/college/{c['id']}/students/ca-view", headers=tpo))
    assert v["student"]["name"] == "ca-view Student" and v["student"]["batch"]["name"] == "IT 2026"
    assert v["readiness"]["coverage"] == 2 and v["activity"]["active_days_30d"] == 2
    assert v["integrity"]["with_notes"] == 2
    notes = [n for p in v["practice"] for n in p["notes"]]
    assert "Left the tab 3 times" in notes and "Answered 10 questions in 20 seconds" in notes
    forbidden = ("chat", "resume", "xp", "streak", "recruiter", "job", "circle", "league", "reminder",
                 "email", "profile", "next_steps", "visib", "referral", "badge")
    leaked = [k for k in _keys(v) if any(f in k.lower() for f in forbidden)]
    assert leaked == []
    assert client.get(f"/api/college/{c['id']}/students/ca-r1", headers=tpo).status_code == 404


def test_exports_have_fixed_headers_and_safe_cells():
    c, tpo = _college("Export College", "ca-etpo", "tpo@export.edu")
    roster = ('Roll No,Student Name,Batch,Department,CGPA\n'
              'E1,"Shah, Riya ""RJ""",2027,CSE,8.2\n'
              'E2,=HYPERLINK("http://x"),2027,CSE,7\n'
              'E3,Not Joined,2027,CSE,6.5\n')
    ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo, json={"csv": roster, "dry_run": False}))
    b = ok(client.get(f"/api/college/{c['id']}/batches", headers=tpo))["batches"][0]
    _join("ca-e1", b["join_code"], roll_no="E1")
    _theory("ca-e1", 82, {"DSA": (8, 10)})
    _join("ca-e2", b["join_code"], roll_no="E2")

    def get(kind, **params):
        r = client.get(f"/api/college/{c['id']}/exports/{kind}.csv", headers=tpo, params=params)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
        return list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))

    rows = get("roster_status")
    assert rows[0] == ["roll_no", "name", "email", "batch", "cgpa", "backlogs", "status", "verified", "joined_on"]
    by_roll = {r[0]: r for r in rows[1:]}
    assert by_roll["E1"][1] == 'Shah, Riya "RJ"' and by_roll["E1"][6:8] == ["active", "yes"]
    assert by_roll["E2"][1].startswith("'=")  # never a live formula
    assert by_roll["E3"][6] == "not joined"

    rows = get("outcomes_naac")
    assert rows[0][-5:] == ["placed", "employer", "package_lpa", "higher_studies", "institution"]
    e1 = next(r for r in rows if r[0] == "E1")
    assert e1[5:7] == ["82", "Interview-ready"] and e1[-5:] == [""] * 5
    assert next(r for r in rows if r[0] == "E3")[5] == ""

    rows = get("batch_readiness", batch_id=b["id"])
    assert rows[0][:5] == ["roll_no", "name", "batch", "readiness", "label"] and len(rows) == 3
    assert client.get(f"/api/college/{c['id']}/exports/secrets.csv", headers=tpo).status_code == 404
    assert client.get(f"/api/college/{c['id']}/exports/roster_status.csv", headers=_student("ca-e1")).status_code == 403


def test_dashboard_query_count_does_not_grow_with_the_batch():
    c, tpo = _college("Scale College", "ca-stpo", "tpo@scale.edu")
    small, big = _batch(c["id"], tpo, "Small"), _batch(c["id"], tpo, "Big")
    for i in range(3):
        _join(f"ca-s{i}", small["join_code"])
        _theory(f"ca-s{i}", 60, {"SQL": (3, 5)})
    for i in range(25):
        _join(f"ca-b{i}", big["join_code"])
        _theory(f"ca-b{i}", 60, {"SQL": (3, 5)})
        _active(f"ca-b{i}", 1)

    def count(batch_id):
        n = [0]

        def hook(*_):
            n[0] += 1
        event.listen(engine, "before_cursor_execute", hook)
        db = SessionLocal()
        try:
            ca.batch_dashboard(db, c["id"], batch_id)
        finally:
            db.close()
            event.remove(engine, "before_cursor_execute", hook)
        return n[0]

    assert count(big["id"]) == count(small["id"]) <= 10
