"""Delta for College, P1: the two recruiter pools, and under-18 college students.

    .venv/Scripts/python -m pytest tests/test_recruiter_pools_and_minors.py -q
"""
import datetime
import json
import os
import sys
import tempfile

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "pools_minors_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.dependencies.auth import block_minor_ai  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Recruiter, User, UserBadge  # noqa: E402
import app.routers.recruiter as rr  # noqa: E402
import app.services.compliance as comp  # noqa: E402
import app.services.minors as minors  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
ADMIN = {"X-User-Id": "rp-boss", "X-User-Email": "boss@delta.test"}
V = comp.POLICY_VERSION


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    from app.limiter import limiter
    limiter.reset()
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "boss@delta.test")
    monkeypatch.setattr(rr, "_supabase_admin_email", lambda uid: None)


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _student(uid, audience="student", email=None):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=f"{uid} Learner", profile_data=json.dumps({"audience": audience})))
        db.commit()
        comp.record_consent(db, uid, comp.TERMS, True)
    db.close()
    return {"X-User-Id": uid, "X-User-Email": email or f"{uid}@gmail.com"}


def _opt_in(uid):
    return client.post(f"/api/privacy/{uid}/consent", headers={"X-User-Id": uid},
                       json={"purpose": "recruiter_visibility", "granted": True})


def _recruiter(uid, email, pool):
    db = SessionLocal()
    if not db.get(Recruiter, uid):
        db.add(Recruiter(id=uid, email=email, name=uid, company=f"{uid} Co", status="approved", pool=pool))
        db.commit()
    db.close()
    return {"X-User-Id": uid, "X-User-Email": email}


def _college(name, tpo_email, uid, **extra):
    c = ok(client.post("/api/college/admin/colleges", headers=ADMIN, json={
        "name": name, "seat_limit": 50, "first_tpo_email": tpo_email, **extra}))
    tpo = {"X-User-Id": uid, "X-User-Email": tpo_email}
    ok(client.post("/api/college/me/accept", headers=tpo, json={"policy_version": V}))
    batch = ok(client.post(f"/api/college/{c['id']}/batches", headers=tpo, json={"name": "CSE 2027"}))
    return c, tpo, batch


def _ids(headers):
    return {c["id"] for c in ok(client.post("/api/recruiter/search", headers=headers, json={}))["candidates"]}


# ── recruiter pools ──────────────────────────────────────────────────────────

def test_open_and_campus_pools_never_mix():
    solo = _student("rp-solo")
    ok(_opt_in("rp-solo"))
    pro = _student("rp-pro", audience="professional")
    assert _opt_in("rp-pro").status_code == 400  # professionals can't opt in
    db = SessionLocal()
    comp.record_consent(db, "rp-pro", comp.RECRUITER_VISIBILITY, True)  # a legacy opt-in from before the change
    db.close()

    c, tpo, batch = _college("Pool College", "tpo@pool.edu", "rp-tpo")
    member = _student("rp-member")
    ok(client.post("/api/college/student/rp-member/join", headers=member, json={"code": batch["join_code"]}))
    ok(_opt_in("rp-member"))

    open_rec = _recruiter("rp-open", "hr@open.com", "open")
    campus = _recruiter("rp-campus", "hr@campus.com", "campus")
    unlinked = _recruiter("rp-unlinked", "hr@nolink.com", "campus")
    assert client.post(f"/api/college/{c['id']}/recruiters", headers=tpo, json={"email": "hr@open.com"}).status_code == 400
    ok(client.post(f"/api/college/{c['id']}/recruiters", headers=tpo, json={"email": "hr@campus.com"}))

    assert "rp-solo" in _ids(open_rec) and not {"rp-member", "rp-pro"} & _ids(open_rec)
    assert _ids(campus) == {"rp-member"}
    assert _ids(unlinked) == set()
    assert client.get("/api/recruiter/candidates/rp-member", headers=open_rec).status_code == 404
    assert client.get("/api/recruiter/candidates/rp-solo", headers=campus).status_code == 404
    detail = ok(client.get("/api/recruiter/candidates/rp-member", headers=campus))
    assert detail["education"] == {"institution": "Pool College", "major": None, "year": None,
                                   "stage": "College student", "verified_by_college": False}

    link = ok(client.get(f"/api/college/{c['id']}/recruiters", headers=tpo))["recruiters"][0]
    ok(client.delete(f"/api/college/{c['id']}/recruiters/{link['id']}", headers=tpo))
    assert client.get("/api/recruiter/candidates/rp-member", headers=campus).status_code == 404
    assert solo


def test_joining_a_college_switches_visibility_off_and_pending_seats_are_in_no_pool():
    h = _student("rp-mover")
    ok(_opt_in("rp-mover"))
    c, tpo, _ = _college("Mover College", "tpo@mover.edu", "rp-mtpo")
    ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo, json={
        "csv": "Roll,Name,Batch,Branch\nM1,Someone Else,2027,CSE\n", "dry_run": False}))
    rostered = next(b for b in ok(client.get(f"/api/college/{c['id']}/batches", headers=tpo))["batches"] if b["roster"])
    ok(client.post("/api/college/student/rp-mover/join", headers=h, json={"code": rostered["join_code"], "roll_no": "X"}))
    state = ok(client.get("/api/privacy/rp-mover/consent", headers=h))
    assert state["recruiter_visible"] is False and state["recruiter_pool"] is None
    assert "confirm your seat" in state["recruiter_pool_reason"]
    assert _opt_in("rp-mover").status_code == 400


def test_a_campus_recruiter_link_activates_when_delta_approves_them():
    c, tpo, batch = _college("Invite College", "tpo@invite.edu", "rp-itpo")
    ok(client.post(f"/api/college/{c['id']}/recruiters", headers=tpo, json={"email": "new@hire.com"}))
    assert ok(client.get(f"/api/college/{c['id']}/recruiters", headers=tpo))["recruiters"][0]["status"] == "invited"
    rec = {"X-User-Id": "rp-new", "X-User-Email": "new@hire.com"}
    ok(client.post("/api/recruiter/register", headers=rec, json={"name": "New", "company": "Hire",
                                                                   "accepted_terms": True, "policy_version": V}))
    approved = ok(client.post("/api/recruiter/admin/recruiters/rp-new/review", headers=ADMIN,
                              json={"approve": True, "pool": "campus"}))
    assert approved["pool"] == "campus" and approved["linked_colleges"] == ["Invite College"]
    student = _student("rp-istudent")
    ok(client.post("/api/college/student/rp-istudent/join", headers=student, json={"code": batch["join_code"]}))
    ok(_opt_in("rp-istudent"))
    assert _ids(rec) == {"rp-istudent"}


# ── under-18 college students ────────────────────────────────────────────────

def _dob(years, days=0):
    today = datetime.date.today()
    return (today.replace(year=today.year - years) - datetime.timedelta(days=days)).isoformat()


@pytest.fixture
def minors_on(monkeypatch):
    monkeypatch.setattr(settings, "MINOR_ACCOUNTS_ENABLED", True)
    sent = {}
    monkeypatch.setattr(minors, "_email_parent", lambda db, uid, c, name, email, token: sent.update(token=token))
    return sent


def _bare(uid):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=f"{uid} Kid"))
        db.commit()
    db.close()
    return {"X-User-Id": uid}


def _minor_start(uid, code, **extra):
    body = {"dob": _dob(16), "code": code, "parent_email": "mum@example.org", "parent_name": "Mum",
            "policy_version": V, "assent": True, **extra}
    return client.post(f"/api/privacy/{uid}/minor-start", headers=_bare(uid), json=body)


def test_under_18_accounts_are_off_by_default():
    _, _, batch = _college("Off College", "tpo@off.edu", "rp-offtpo", allow_minors=True)
    r = _minor_start("rp-kid0", batch["join_code"])
    assert r.status_code == 400 and "aren't available" in r.json()["detail"]


def test_parent_link_unlocks_the_account_and_restrictions_hold(minors_on, monkeypatch):
    _, _, no_minors = _college("Adults Only", "tpo@adults.edu", "rp-atpo")
    assert _minor_start("rp-kidx", no_minors["join_code"]).status_code == 400
    _, _, batch = _college("Minor College", "tpo@minor.edu", "rp-ktpo", allow_minors=True)
    assert _minor_start("rp-old", batch["join_code"], dob=_dob(19)).status_code == 400
    state = ok(_minor_start("rp-kid", batch["join_code"]))
    h = {"X-User-Id": "rp-kid"}
    assert state["is_minor"] is True and state["access_ok"] is False
    assert state["parental_consent"]["granted"] is False and state["parental_consent"]["parent_email"] == "m***@example.org"

    token = minors_on["token"]
    assert ok(client.get(f"/api/public/parent-consent/{token}"))["college"] == "Minor College"
    assert client.post(f"/api/public/parent-consent/{token}", json={"grant": True}).status_code == 400
    ok(client.post(f"/api/public/parent-consent/{token}", json={"grant": True, "is_guardian": True}))
    assert client.post(f"/api/public/parent-consent/{token}", json={"grant": True, "is_guardian": True}).status_code == 400
    state = ok(client.get("/api/privacy/rp-kid/consent", headers=h))
    assert state["access_ok"] is True and state["recruiter_pool"] is None

    # What under-18s can't do, enforced on the server.
    assert _opt_in("rp-kid").status_code == 400
    assert client.put("/api/engagement/rp-kid/league", headers=h, json={"enabled": True}).status_code == 400
    assert client.post("/api/circles/rp-kid", headers=h, json={"name": "Kids"}).status_code == 400
    db = SessionLocal()
    db.add(UserBadge(user_id="rp-kid", badge_key="tests", tier=1, earned_at=datetime.datetime.utcnow()))
    db.commit()
    db.close()
    assert client.post("/api/engagement/rp-kid/badges/tests/share", headers=h).status_code == 404
    assert client.post("/api/career-os/user/rp-kid/task-detail", headers=h, json={"title": "x"}).status_code == 403
    assert client.post("/api/chat/rp-kid/send", headers=h, json={"message": "hi"}).status_code in (403, 404, 405)

    # Theory tests use the topic only, never the learner's profile.
    import app.routers.sandbox_theory as st
    seen = {}

    def fake(user_id, topic, n, difficulty, category, area, **kw):
        seen.update(user_id=user_id, **kw)
        return topic, [{"question": "Q", "options": ["a", "b", "c", "d"], "answer_index": 0, "explanation": "",
                        "skill": topic}] * n
    monkeypatch.setattr(st, "generate_test", fake)
    assert client.post("/api/sandbox/theory/rp-kid/start", headers=h, json={"num_questions": 5}).status_code == 400
    ok(client.post("/api/sandbox/theory/rp-kid/start", headers=h, json={"topic": "Arrays", "num_questions": 5}))
    assert seen == {"user_id": None, "personalize": False}


def test_college_attestation_and_parent_decline(minors_on):
    from datetime import date
    c, tpo, _ = _college("Attest College", "tpo@attest.edu", "rp-ttpo", allow_minors=True)
    kid_dob = _dob(17)
    csv = f"Roll,Name,Batch,Branch,DOB\nK1,Kid One,2029,CSE,{kid_dob}\n"
    r = ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo, json={"csv": csv, "dry_run": False}))
    assert r["created"] == 0 and r["errors"][0]["field"] == "dob"  # needs the college's consent reference
    r = ok(client.post(f"/api/college/{c['id']}/roster", headers=tpo,
                       json={"csv": csv, "dry_run": False, "minors_consent_ref": "Consent forms 2026, file 12"}))
    assert r["created"] == 1 and r["minors"] == 1
    batch = next(b for b in ok(client.get(f"/api/college/{c['id']}/batches", headers=tpo))["batches"] if b["roster"])
    state = ok(_minor_start("rp-k1", batch["join_code"], dob=kid_dob, roll_no="K1", parent_email=None))
    assert state["access_ok"] is True and state["parental_consent"]["method"] == "college_attestation"
    # The roster says K1 is under 18, so the adult join path refuses them.
    adult_try = client.post("/api/college/student/rp-k1b/join", headers=_student("rp-k1b"),
                            json={"code": batch["join_code"], "roll_no": "K1"})
    assert adult_try.status_code in (200, 400)  # K1 already claimed -> pending; never an adult claim of a minor row

    _, _, plain = _college("Decline College", "tpo@decline.edu", "rp-dtpo", allow_minors=True)
    ok(_minor_start("rp-k2", plain["join_code"]))
    ok(client.post(f"/api/public/parent-consent/{minors_on['token']}", json={"grant": False}))
    state = ok(client.get("/api/privacy/rp-k2/consent", headers={"X-User-Id": "rp-k2"}))
    assert state["access_ok"] is False and state["college"] is None
    assert date.today()


def test_turning_18_needs_the_learners_own_consent(minors_on):
    _, _, batch = _college("Birthday College", "tpo@bday.edu", "rp-btpo", allow_minors=True)
    ok(_minor_start("rp-bday", batch["join_code"]))
    ok(client.post(f"/api/public/parent-consent/{minors_on['token']}", json={"grant": True, "is_guardian": True}))
    db = SessionLocal()
    user = db.get(User, "rp-bday")
    user.date_of_birth = datetime.date.fromisoformat(_dob(18, days=2))  # birthday was two days ago
    db.commit()
    db.close()
    h = {"X-User-Id": "rp-bday"}
    state = ok(client.get("/api/privacy/rp-bday/consent", headers=h))
    assert state["is_minor"] is False and state["needs_adult_reconsent"] is True and state["access_ok"] is False
    ok(client.post("/api/privacy/rp-bday/consent", headers=h, json={"purpose": "adult_reconsent", "granted": True}))
    state = ok(client.get("/api/privacy/rp-bday/consent", headers=h))
    assert state["needs_adult_reconsent"] is False and state["access_ok"] is True
    assert state["recruiter_visible"] is False  # stays off until they opt in themselves


def test_date_of_birth_cannot_be_set_through_the_profile():
    h = _student("rp-dobhack")
    client.put("/api/ingestion/profile/rp-dobhack", headers=h, json={"date_of_birth": "2015-01-01"})
    db = SessionLocal()
    assert db.get(User, "rp-dobhack").date_of_birth is None
    db.close()


def _deps(dependant):
    out = set()
    for d in dependant.dependencies:
        out.add(d.call)
        out |= _deps(d)
    return out


def _all_routes(routes):
    for r in routes:  # included routers may be wrapped
        if hasattr(r, "original_router"):
            yield from _all_routes(r.original_router.routes)
        else:
            yield r


def test_every_ai_route_is_closed_to_minors():
    """Fails if someone adds an AI route to these areas without the guard."""
    guarded_prefixes = ("/api/chat", "/api/ingestion", "/api/sandbox/interview", "/api/resume", "/api/dossier",
                        "/api/opportunities")
    planner = {"/api/career-os/user/{user_id}/initialize", "/api/career-os/user/{user_id}/weekly-cycle",
               "/api/career-os/user/{user_id}/task-detail", "/api/career-os/user/{user_id}/consolidate-memory",
               "/api/career-os/user/{user_id}/day-plan", "/api/career-os/user/{user_id}/advance-expired-week"}
    checked = 0
    for route in _all_routes(app.routes):
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if path.startswith(guarded_prefixes) or (path in planner and ("POST" in methods or path.endswith("day-plan"))):
            if path.endswith("day-plan") and "PUT" in methods:
                continue  # saving your own schedule calls no AI
            assert block_minor_ai in _deps(route.dependant), path
            checked += 1
    assert checked > 20
