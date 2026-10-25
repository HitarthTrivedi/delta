"""Phase 3 retention: study circles, referrals, the reminder-wording bandit and
the suggested study time.

    .venv/Scripts/python -m pytest tests/test_gamification_phase3.py -q
"""
import datetime
import os
import random
import sys
import tempfile
import uuid

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "phase3_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (CircleMember, DailyActivity, NudgeLog, Referral, StudyCircle, User,  # noqa: E402
                        UserEngagement, XpEvent)
from app.services import compliance, engagement as eng, reminder_service as rs  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
UTC = datetime.timezone.utc
MONDAY = datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC)  # 11:30 IST


@pytest.fixture(autouse=True)
def header_auth(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        now = MONDAY

        def days(self, n):
            self.now += datetime.timedelta(days=n)
    c = Clock()
    monkeypatch.setattr(eng, "_now", lambda: c.now)
    return c


def _user(uid, name=None, terms=True, created=None):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=name or f"{uid} Tester", created_at=created or datetime.datetime.utcnow()))
        db.commit()
        if terms:
            compliance.record_consent(db, uid, compliance.TERMS, True)
    db.close()
    return {"X-User-Id": uid}


def _do(uid, source="quick_review", sid=None):
    db = SessionLocal()
    try:
        return eng.record_activity(db, uid, source, sid or str(uuid.uuid4()))
    finally:
        db.close()


def _consent(uid, purpose):
    db = SessionLocal()
    try:
        rec = compliance.latest_consent(db, uid, purpose)
        return rec.action if rec else None
    finally:
        db.close()


# ── study circles ───────────────────────────────────────────────────────────

def test_create_join_and_what_members_see(clock):
    owner, friend = _user("ca", "Asha Rao"), _user("cb", "Vikram Mehta")
    nope = _user("c-noterms", terms=False)
    assert client.post("/api/circles/c-noterms", headers=nope, json={"name": "X"}).status_code == 400

    r = client.post("/api/circles/ca", headers=owner, json={"name": "  Night owls  "})
    assert r.status_code == 200
    circle = r.json()["circles"][0]
    assert circle["name"] == "Night owls" and circle["you_own"] and _consent("ca", compliance.STUDY_CIRCLES) == "granted"

    pv = client.get(f"/api/circles/cb/preview/{circle['invite_code'].lower()}", headers=friend).json()
    assert pv == {"name": "Night owls", "members": 1, "full": False, "max_members": 6}
    joined = client.post("/api/circles/cb/join", headers=friend, json={"code": circle["invite_code"]}).json()
    members = joined["circles"][0]["members"]
    assert [m["name"] for m in members] == ["Asha R.", "Vikram M."]
    assert set(members[0]) == {"id", "name", "you", "owner", "studied_today", "days_this_week"}
    assert not {"ca", "cb"} & {v for m in members for v in m.values() if isinstance(v, str)}  # handles, never user ids
    assert client.get("/api/circles/ca", headers=friend).status_code == 403


def test_full_circles_and_bad_codes_are_refused(clock):
    h = _user("f0")
    code = client.post("/api/circles/f0", headers=h, json={"name": "Full house"}).json()["circles"][0]["invite_code"]
    for i in range(1, 6):
        _user(f"f{i}")
        assert client.post(f"/api/circles/f{i}/join", headers={"X-User-Id": f"f{i}"}, json={"code": code}).status_code == 200
    _user("f6")
    r = client.post("/api/circles/f6/join", headers={"X-User-Id": "f6"}, json={"code": code})
    assert r.status_code == 400 and "full" in r.json()["detail"]
    assert client.post("/api/circles/f6/join", headers={"X-User-Id": "f6"}, json={"code": "NOPE1234"}).status_code == 400


def test_owner_controls_and_leaving(clock):
    a, b = _user("oa", "Owner One"), _user("ob", "Member Two")
    circle = client.post("/api/circles/oa", headers=a, json={"name": "Crew"}).json()["circles"][0]
    client.post("/api/circles/ob/join", headers=b, json={"code": circle["invite_code"]})
    me_b = client.get("/api/circles/ob", headers=b).json()["circles"][0]
    member_a = next(m for m in me_b["members"] if m["owner"])
    assert client.delete(f"/api/circles/ob/{circle['id']}/members/{member_a['id']}", headers=b).status_code == 403
    new = client.post(f"/api/circles/oa/{circle['id']}/new-code", headers=a).json()["circles"][0]["invite_code"]
    assert new != circle["invite_code"]

    client.delete(f"/api/circles/oa/{circle['id']}", headers=a)  # owner leaves: the next member takes over
    assert client.get("/api/circles/ob", headers=b).json()["circles"][0]["you_own"] is True
    assert _consent("oa", compliance.STUDY_CIRCLES) == "withdrawn"
    client.delete(f"/api/circles/ob/{circle['id']}", headers=b)  # last one out closes the circle
    db = SessionLocal()
    assert db.get(StudyCircle, circle["id"]) is None
    db.close()


def test_circle_streak_counts_days_everyone_kept_and_freezes_count(clock):
    a, b = _user("sa"), _user("sb")
    circle = client.post("/api/circles/sa", headers=a, json={"name": "Streakers"}).json()["circles"][0]
    client.post("/api/circles/sb/join", headers=b, json={"code": circle["invite_code"]})
    for _ in range(2):  # Mon, Tue: both study
        _do("sa"); _do("sb"); clock.days(1)
    _do("sa")  # Wed: only A so far
    assert client.get("/api/circles/sa", headers=a).json()["circles"][0]["streak"] == 2
    _do("sb")
    assert client.get("/api/circles/sa", headers=a).json()["circles"][0]["streak"] == 3
    db = SessionLocal()  # Thu: B is covered by a freeze, A studies
    db.add(DailyActivity(user_id="sb", local_date=datetime.date(2026, 10, 8), xp=0, actions=0,
                         goal_met=False, freeze_used=True, on_break=False))
    db.commit()
    db.close()
    clock.days(1)
    _do("sa")
    assert client.get("/api/circles/sa", headers=a).json()["circles"][0]["streak"] == 4
    clock.days(2)  # nobody studied Friday
    assert client.get("/api/circles/sa", headers=a).json()["circles"][0]["streak"] == 0


def test_weekly_circle_goal_pays_every_member_once(clock):
    a, b = _user("ga"), _user("gb")
    circle = client.post("/api/circles/ga", headers=a, json={"name": "Goal getters"}).json()["circles"][0]
    client.post("/api/circles/gb/join", headers=b, json={"code": circle["invite_code"]})
    for _ in range(3):  # 3 days each = 6 = 3 x 2 members
        _do("ga"); r = _do("gb"); clock.days(1)
    assert r["circle_goals"] == ["Goal getters"]
    db = SessionLocal()
    assert db.query(XpEvent).filter_by(user_id="gb", source_type="circle_goal").count() == 1
    assert db.query(XpEvent).filter_by(user_id="ga", source_type="circle_goal").count() == 0  # A was away since
    db.close()
    week = client.get("/api/circles/ga", headers=a).json()["circles"][0]["week"]  # A's visit books A's share
    assert week["met"] and week["rewarded"] and week["done"] == week["target"] == 6
    _do("ga")
    db = SessionLocal()
    assert db.query(XpEvent).filter_by(user_id="ga", source_type="circle_goal").count() == 1
    db.close()


# ── referrals ───────────────────────────────────────────────────────────────

def test_referral_rules(clock):
    inviter, friend = _user("ra", "Riya Sharma"), _user("rb", "Kabir Singh")
    code = client.get("/api/engagement/ra/referrals", headers=inviter).json()["code"]
    assert client.get("/api/engagement/ra/referrals", headers=inviter).json()["code"] == code  # stable
    assert client.post("/api/engagement/ra/referrals/claim", headers=inviter, json={"code": code}).status_code == 400
    old = _user("rold", created=datetime.datetime.utcnow() - datetime.timedelta(days=30))
    assert client.post("/api/engagement/rold/referrals/claim", headers=old, json={"code": code}).status_code == 400

    pv = client.get(f"/api/engagement/rb/referrals/preview/{code}", headers=friend).json()
    assert pv["inviter"] == "Riya S." and pv["eligible"] is True
    ok = client.post("/api/engagement/rb/referrals/claim", headers=friend, json={"code": code.lower()})
    assert ok.status_code == 200 and ok.json()["linked_to"]["name"] == "Riya S."
    assert _consent("rb", compliance.REFERRAL_LINK) == "granted"
    assert client.post("/api/engagement/rb/referrals/claim", headers=friend, json={"code": code}).status_code == 400

    back = client.get("/api/engagement/rb/referrals", headers=friend).json()["code"]
    assert client.post("/api/engagement/ra/referrals/claim", headers=inviter, json={"code": back}).status_code == 400
    assert client.get("/api/engagement/ra/referrals", headers=inviter).json()["invited"] == [{"name": "Kabir S.", "rewarded": False}]


def test_both_get_a_freeze_after_three_study_days(clock):
    inviter, friend = _user("wa"), _user("wb")
    code = client.get("/api/engagement/wa/referrals", headers=inviter).json()["code"]
    client.post("/api/engagement/wb/referrals/claim", headers=friend, json={"code": code})
    for d in range(3):
        r = _do("wb")
        assert r["referral_rewarded"] is (d == 2)
        clock.days(1)
    db = SessionLocal()
    assert db.get(UserEngagement, "wb").streak_freezes == 1
    assert db.get(UserEngagement, "wa").streak_freezes == 1
    db.close()
    assert client.get("/api/engagement/wa/referrals", headers=inviter).json()["invited"][0]["rewarded"] is True

    # Unlinking hides the friend from the inviter; the rewards stay.
    client.post("/api/privacy/wb/consent", headers=friend, json={"purpose": compliance.REFERRAL_LINK, "granted": False})
    assert client.get("/api/engagement/wa/referrals", headers=inviter).json()["invited"] == []


def test_inviter_rewards_are_capped_each_month(clock, monkeypatch):
    from app.services import referrals
    monkeypatch.setattr(referrals, "MONTHLY_CAP", 1)
    monkeypatch.setattr(referrals, "ACTIVE_DAYS_TO_REWARD", 1)
    inviter = _user("ma")
    code = client.get("/api/engagement/ma/referrals", headers=inviter).json()["code"]
    for f in ("mb", "mc"):
        client.post(f"/api/engagement/{f}/referrals/claim", headers=_user(f), json={"code": code})
        _do(f)
    db = SessionLocal()
    assert db.get(UserEngagement, "ma").streak_freezes == 1  # second reward capped
    assert db.get(UserEngagement, "mc").streak_freezes == 1  # the friend still gets theirs
    db.close()


# ── reminders ───────────────────────────────────────────────────────────────

def test_bandit_prefers_the_wording_that_works_but_keeps_exploring():
    _user("bandit")
    db = SessionLocal()
    now = datetime.datetime.utcnow()
    for i in range(40):
        db.add(NudgeLog(id=str(uuid.uuid4()), user_id="bandit", local_date=now.date(), variant="tiny",
                        sent_at=now, returned=i < 30))
        db.add(NudgeLog(id=str(uuid.uuid4()), user_id="bandit", local_date=now.date(), variant="quests",
                        sent_at=now, returned=i < 4))
    db.commit()
    e = eng.get_or_create(db, "bandit")
    rng = random.Random(7)
    picks = [rs.choose_variant(db, e, ["tiny", "quests"], rng) for _ in range(200)]
    db.close()
    assert picks.count("tiny") > 180


def test_sweep_logs_the_wording_and_studying_marks_it_returned(clock, monkeypatch):
    h = _user("rem", "Meera Iyer")
    db = SessionLocal()
    e = eng.get_or_create(db, "rem")
    e.reminders_opt_in, e.reminder_channel, e.study_time = True, "email", "07:00"
    db.commit()
    db.close()
    sent = {}
    monkeypatch.setattr(rs, "_resolve_email", lambda db, user: "meera@example.org")
    monkeypatch.setattr(rs, "send_nudge_email", lambda **kw: sent.update(kw) or True)
    assert rs.run_daily_reminders()["sent"] >= 1
    db = SessionLocal()
    log = db.query(NudgeLog).filter_by(user_id="rem").one()
    assert log.variant in ("tiny", "quests") and log.returned is False
    db.close()
    assert sent["message"]["subject"].startswith("Meera")
    _do("rem")
    db = SessionLocal()
    assert db.query(NudgeLog).filter_by(user_id="rem").one().returned is True
    db.close()
    assert h


def test_suggested_study_time_follows_when_you_actually_study(clock):
    _user("st")
    db = SessionLocal()
    e = eng.get_or_create(db, "st")
    e.study_time = "21:00"
    db.commit()
    for d in range(6):  # 18:10 IST = 12:40 UTC
        day = datetime.date(2026, 9, 28) + datetime.timedelta(days=d)
        db.add(XpEvent(id=str(uuid.uuid4()), user_id="st", source_type="quick_review", source_id=f"st{d}",
                       xp=10, local_date=day, created_at=datetime.datetime.combine(day, datetime.time(12, 40))))
    db.commit()
    assert eng.suggested_study_time(db, e) == "18:00"
    e.study_time = "18:30"
    assert eng.suggested_study_time(db, e) is None  # close enough already
    db.close()


def test_erasure_covers_circles_referrals_and_reminder_log(clock, monkeypatch):
    import app.services.compliance as comp
    a, b = _user("xa"), _user("xb")
    circle = client.post("/api/circles/xa", headers=a, json={"name": "Temp"}).json()["circles"][0]
    client.post("/api/circles/xb/join", headers=b, json={"code": circle["invite_code"]})
    code = client.get("/api/engagement/xa/referrals", headers=a).json()["code"]
    client.post("/api/engagement/xb/referrals/claim", headers=b, json={"code": code})
    db = SessionLocal()
    db.add(NudgeLog(id=str(uuid.uuid4()), user_id="xa", local_date=datetime.date(2026, 10, 5), variant="tiny"))
    db.commit()
    db.close()
    monkeypatch.setattr(comp, "delete_auth_user", lambda uid: True)
    assert client.request("DELETE", "/api/privacy/xa", headers=a, json={"confirm": "DELETE"}).status_code == 200
    db = SessionLocal()
    assert db.query(CircleMember).filter_by(user_id="xa").count() == 0
    assert db.query(Referral).filter_by(referrer_id="xa").count() == 0
    assert db.query(NudgeLog).filter_by(user_id="xa").count() == 0
    db.close()
    left = client.get("/api/circles/xb", headers=b).json()["circles"][0]
    assert left["you_own"] is True and len(left["members"]) == 1
