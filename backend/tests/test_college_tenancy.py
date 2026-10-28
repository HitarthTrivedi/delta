"""Delta for College, P1: colleges, staff, batches, roster import, joining,
seats, removal, licence expiry, cross-college isolation, export and erasure.

    .venv/Scripts/python -m pytest tests/test_college_tenancy.py -q
"""
import datetime
import json
import os
import sys
import tempfile

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "college_tenancy_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CollegeAdmin, CollegeMember, CollegeRecruiter, Recruiter, RosterEntry, User  # noqa: E402
import app.services.compliance as comp  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
ADMIN = {"X-User-Id": "ct-boss", "X-User-Email": "boss@delta.test"}
V = comp.POLICY_VERSION


@pytest.fixture(autouse=True)
def header_auth(monkeypatch):
    from app.limiter import limiter
    limiter.reset()  # every test request shares one client address
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "boss@delta.test")


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _student(uid, email=None, audience="student", name=None):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=name or f"{uid} Student", profile_data=json.dumps({"audience": audience})))
        db.commit()
        comp.record_consent(db, uid, comp.TERMS, True)
    db.close()
    return {"X-User-Id": uid, "X-User-Email": email or f"{uid}@gmail.com"}


def _college(name, tpo_email, seats=50, domains=(), **extra):
    body = {"name": name, "seat_limit": seats, "email_domains": list(domains), "first_tpo_email": tpo_email, **extra}
    return ok(client.post("/api/college/admin/colleges", headers=ADMIN, json=body))


def _tpo(uid, email):
    h = {"X-User-Id": uid, "X-User-Email": email}
    ok(client.post("/api/college/me/accept", headers=h, json={"policy_version": V}))
    return h


ROSTER = """Roll No,Student Name,Email,Batch,Department,Section,CGPA,Backlogs
cs101,Asha Rao,asha@svce.ac.in,2027,CSE,A,8.4,0
CS102,Vikram Mehta,vikram@svce.ac.in,2027,CSE,A,7.1,1
CS103,Riya Shah,,2027,CSE,B,9.0,0
"""


def test_platform_admin_creates_a_college_and_the_tpo_accepts():
    assert client.post("/api/college/admin/colleges", headers={"X-User-Id": "x", "X-User-Email": "x@y.com"},
                       json={"name": "N", "seat_limit": 5, "first_tpo_email": "a@b.com"}).status_code == 403
    c = _college("SVCE", "tpo@svce.ac.in", domains=["svce.ac.in"])
    assert c["seats_used"] == 0 and c["live"] is True
    assert client.post("/api/college/admin/colleges", headers=ADMIN, json={
        "name": "Clash", "seat_limit": 5, "email_domains": ["svce.ac.in"], "first_tpo_email": "z@z.com"}).status_code == 400

    me = ok(client.get("/api/college/me", headers={"X-User-Id": "ct-tpo", "X-User-Email": "TPO@svce.ac.in"}))
    assert me["pending_invites"] == [{"college": "SVCE", "role": "tpo"}] and me["colleges"] == []
    student = _student("ct-studentlogin", "tpo@svce.ac.in")
    assert client.post("/api/college/me/accept", headers=student, json={"policy_version": V}).status_code == 400
    h = _tpo("ct-tpo", "tpo@svce.ac.in")
    assert [x["role"] for x in ok(client.get("/api/college/me", headers=h))["colleges"]] == ["tpo"]
    db = SessionLocal()
    assert comp.latest_consent(db, "ct-tpo", comp.COLLEGE_ADMIN_TERMS).action == "granted"
    db.close()
    # A college staff login can't register as a recruiter.
    assert client.post("/api/recruiter/register", headers=h, json={
        "name": "T", "company": "SVCE", "accepted_terms": True, "policy_version": V}).status_code == 409


def test_faculty_can_view_but_not_change():
    c = _college("Faculty Uni", "tpo@fac.edu")
    tpo = _tpo("ct-ftpo", "tpo@fac.edu")
    ok(client.post(f"/api/college/{c['id']}/admins", headers=tpo, json={"email": "prof@fac.edu", "role": "faculty"}))
    prof = _tpo("ct-prof", "prof@fac.edu")
    assert ok(client.get(f"/api/college/{c['id']}/batches", headers=prof))["batches"] == []
    assert client.post(f"/api/college/{c['id']}/batches", headers=prof, json={"name": "X"}).status_code == 403
    admins = ok(client.get(f"/api/college/{c['id']}/admins", headers=tpo))["admins"]
    only_tpo = next(a for a in admins if a["role"] == "tpo")
    assert client.delete(f"/api/college/{c['id']}/admins/{only_tpo['id']}", headers=tpo).status_code == 400


def test_roster_import_validates_previews_and_is_idempotent():
    c = _college("Roster College", "tpo@roster.edu")
    tpo = _tpo("ct-rtpo", "tpo@roster.edu")
    bad = ROSTER + "CS101,Dup Roll,,2027,CSE,A,7,0\nCS104,Bad Email,not-an-email,2027,CSE,A,11,0\n"
    preview = ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo, json={"csv": bad, "dry_run": True}))
    assert preview["created"] == 3 and preview["new_batches"] == 2
    assert {(e["row"], e["field"]) for e in preview["errors"]} == {(5, "roll_no"), (6, "email"), (6, "cgpa")}
    assert ok(client.get(f"/api/college/{c['id']}/roster", headers=tpo))["roster"] == []  # dry run wrote nothing

    done = ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo, json={"csv": ROSTER, "dry_run": False}))
    assert (done["created"], done["updated"], done["errors"]) == (3, 0, [])
    again = ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo, json={"csv": ROSTER, "dry_run": False}))
    assert (again["created"], again["updated"], again["unchanged"]) == (0, 0, 3)
    clash = "Roll No,Name,Email\nCS999,Someone,asha@svce.ac.in\n"
    assert ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo, json={"csv": clash, "dry_run": True}))["errors"][0]["field"] == "email"
    batches = ok(client.get(f"/api/college/{c['id']}/batches", headers=tpo))["batches"]
    assert sorted(b["roster"] for b in batches) == [1, 2]
    assert client.post(f"/api/college/{c['id']}/roster", headers=tpo,
                       json={"csv": "Name\nNo Roll\n", "dry_run": True}).status_code == 400


def _batch(cid, tpo, **body):
    return ok(client.post(f"/api/college/{cid}/batches", headers=tpo, json=body))


def test_join_outcomes_verified_pending_unverified_and_domain():
    c = _college("Join College", "tpo@join.edu", domains=["join.edu"])
    tpo = _tpo("ct-jtpo", "tpo@join.edu")
    ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo, json={
        "csv": "Roll,Name,Email,Batch,Branch,Section\nJ1,Asha,asha@join.edu,2027,CSE,A\nJ2,Vik,,2027,CSE,A\n",
        "dry_run": False}))
    rostered = next(b for b in ok(client.get(f"/api/college/{c['id']}/batches", headers=tpo))["batches"] if b["roster"])
    open_batch = _batch(c["id"], tpo, name="MCA 2026", program="placement_6m")

    pv = ok(client.get(f"/api/college/join/{rostered['join_code'].lower()}/preview", headers=_student("ct-j0")))
    assert pv["needs_roll_no"] is True and pv["college"] == "Join College"

    s1 = _student("ct-j1")
    state = ok(client.post("/api/college/student/ct-j1/join", headers=s1, json={"code": rostered["join_code"], "roll_no": "j2"}))
    assert state["membership"]["status"] == "active" and state["membership"]["verified"] is True
    s2 = _student("ct-j2")
    pending = ok(client.post("/api/college/student/ct-j2/join", headers=s2, json={"code": rostered["join_code"], "roll_no": "NOPE"}))
    assert pending["membership"]["status"] == "pending"
    member = next(m for m in ok(client.get(f"/api/college/{c['id']}/members?status=pending", headers=tpo))["members"])
    ok(client.post(f"/api/college/{c['id']}/members/{member['id']}/approve", headers=tpo))
    s3 = _student("ct-j3")
    unverified = ok(client.post("/api/college/student/ct-j3/join", headers=s3, json={"code": open_batch["join_code"]}))
    assert unverified["membership"]["status"] == "active" and unverified["membership"]["verified"] is False
    assert unverified["membership"]["program"] == "placement_6m"

    asha = _student("ct-asha", "asha@join.edu")
    assert ok(client.get("/api/college/student/ct-asha", headers=asha))["suggestion"] == {"college": "Join College", "on_roster": True}
    via = ok(client.post("/api/college/student/ct-asha/join", headers=asha, json={"via_domain": True}))
    assert via["membership"]["verified"] is True
    stranger = _student("ct-stranger", "who@join.edu")
    assert client.post("/api/college/student/ct-stranger/join", headers=stranger, json={"via_domain": True}).status_code == 400
    assert client.post("/api/college/student/ct-j1/join", headers=s1, json={"code": open_batch["join_code"]}).status_code == 200  # same college: no-op
    other = _college("Other College", "tpo@other.edu")
    other_tpo = _tpo("ct-otpo", "tpo@other.edu")
    other_batch = _batch(other["id"], other_tpo, name="X")
    assert client.post("/api/college/student/ct-j1/join", headers=s1, json={"code": other_batch["join_code"]}).status_code == 400


def test_seat_limit_and_code_rotation():
    c = _college("Small College", "tpo@small.edu", seats=2)
    tpo = _tpo("ct-stpo", "tpo@small.edu")
    b = _batch(c["id"], tpo, name="B")
    for uid in ("ct-s1", "ct-s2"):
        ok(client.post(f"/api/college/student/{uid}/join", headers=_student(uid), json={"code": b["join_code"]}))
    r = client.post("/api/college/student/ct-s3/join", headers=_student("ct-s3"), json={"code": b["join_code"]})
    assert r.status_code == 400 and "seats" in r.json()["detail"]
    fresh = ok(client.post(f"/api/college/{c['id']}/batches/{b['id']}/join-code", headers=tpo))
    assert fresh["join_code"] != b["join_code"]
    assert client.get(f"/api/college/join/{b['join_code']}/preview", headers=_student("ct-s3")).status_code == 404


def test_removal_and_licence_expiry_end_the_seat():
    c = _college("Expiring College", "tpo@exp.edu", seats=5)
    tpo = _tpo("ct-etpo", "tpo@exp.edu")
    b = _batch(c["id"], tpo, name="B")
    h = _student("ct-e1")
    ok(client.post("/api/college/student/ct-e1/join", headers=h, json={"code": b["join_code"]}))
    ok(client.post("/api/privacy/ct-e1/consent", headers=h, json={"purpose": "recruiter_visibility", "granted": True}))
    member = ok(client.get(f"/api/college/{c['id']}/members", headers=tpo))["members"][0]
    assert client.delete(f"/api/college/{c['id']}/members/{member['id']}", headers=tpo).status_code == 200
    db = SessionLocal()
    assert comp.latest_consent(db, "ct-e1", comp.COLLEGE_ENROLLMENT).action == "withdrawn"
    assert comp.latest_consent(db, "ct-e1", comp.RECRUITER_VISIBILITY).action == "withdrawn"
    db.close()
    assert ok(client.get(f"/api/college/{c['id']}", headers=tpo))["seats_used"] == 0

    h2 = _student("ct-e2")
    ok(client.post("/api/college/student/ct-e2/join", headers=h2, json={"code": b["join_code"]}))
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    ok(client.patch(f"/api/college/admin/colleges/{c['id']}", headers=ADMIN, json={"licence_valid_until": yesterday}))
    assert ok(client.get("/api/college/student/ct-e2", headers=h2))["membership"]["live"] is False
    assert ok(client.post("/api/college/admin/sweep", headers=ADMIN))["expired"] >= 1
    assert ok(client.get("/api/college/student/ct-e2", headers=h2))["membership"] is None
    assert client.post("/api/college/student/ct-e9/join", headers=_student("ct-e9"), json={"code": b["join_code"]}).status_code == 400


def test_a_college_only_reaches_its_own_data():
    a = _college("College A", "tpo@a.edu")
    b = _college("College B", "tpo@b.edu")
    tpo_a = _tpo("ct-atpo", "tpo@a.edu")
    _tpo("ct-btpo", "tpo@b.edu")
    assert client.get(f"/api/college/{b['id']}", headers=tpo_a).status_code == 403
    assert client.get(f"/api/college/{b['id']}/members", headers=tpo_a).status_code == 403
    assert client.get(f"/api/college/{a['id']}/members", headers=_student("ct-nosy")).status_code == 403
    assert client.get("/api/college/student/ct-nosy", headers=tpo_a).status_code == 403


def test_export_and_erasure_cover_college_links(monkeypatch):
    c = _college("Erase College", "tpo@erase.edu")
    tpo = _tpo("ct-xtpo", "tpo@erase.edu")
    ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo, json={"csv": "Roll,Name\nX1,Gone Soon\n", "dry_run": False}))
    b = ok(client.get(f"/api/college/{c['id']}/batches", headers=tpo))["batches"]
    code = b[0]["join_code"] if b else _batch(c["id"], tpo, name="B")["join_code"]
    h = _student("ct-x1")
    ok(client.post("/api/college/student/ct-x1/join", headers=h, json={"code": code, "roll_no": "X1"}))
    data = ok(client.get("/api/privacy/ct-x1/export", headers=h))
    assert data["college_members"][0]["status"] == "active" and data["college_roster"][0]["roll_no"] == "X1"
    monkeypatch.setattr(comp, "delete_auth_user", lambda uid: True)
    ok(client.request("DELETE", "/api/privacy/ct-x1", headers=h, json={"confirm": "DELETE"}))
    db = SessionLocal()
    assert db.query(CollegeMember).filter_by(user_id="ct-x1").count() == 0
    entry = db.query(RosterEntry).filter_by(college_id=c["id"], roll_no="X1").one()
    assert entry.claimed_user_id is None  # the college keeps its own record
    db.close()

    # Erasing a recruiter removes their college links.
    db = SessionLocal()
    db.add(Recruiter(id="ct-rec", email="hr@acme.com", name="HR", company="Acme", status="approved", pool="campus"))
    db.commit()
    db.close()
    ok(client.post(f"/api/college/{c['id']}/recruiters", headers=tpo, json={"email": "hr@acme.com"}))
    comp.erase_recruiter(SessionLocal(), "ct-rec")
    db = SessionLocal()
    assert db.query(CollegeRecruiter).filter_by(recruiter_id="ct-rec").count() == 0
    db.close()
    # Erasing a TPO removes their staff row.
    db = SessionLocal()
    comp.erase_student(db, "ct-xtpo")
    assert db.query(CollegeAdmin).filter_by(user_id="ct-xtpo").count() == 0
    db.close()
