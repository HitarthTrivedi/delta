"""Daily habit engine: streaks, freezes, break mode, repair, XP rules.

    .venv/Scripts/python -m pytest tests/test_engagement.py -q
"""
import datetime
import json
import os
import sys
import tempfile
import uuid

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "engagement_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import RoadmapState, SandboxSession, User, XpEvent  # noqa: E402
from app.services import engagement as eng  # noqa: E402
from app.services.central_engine import log_journey_event  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
UTC = datetime.timezone.utc


@pytest.fixture(autouse=True)
def header_auth(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)


class Clock:
    """Moves the engine's 'now' (UTC). IST = UTC+5:30."""
    def __init__(self, monkeypatch, start):
        self.now = start
        monkeypatch.setattr(eng, "_now", lambda: self.now)

    def days(self, n):
        self.now += datetime.timedelta(days=n)


def _user(uid, tasks=("Read chapter 3", "Build a small API")):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=uid))
        db.add(RoadmapState(id=str(uuid.uuid4()), user_id=uid, weekly_focus=json.dumps(
            {"primary_actions": [{"id": f"t{i}", "title": t} for i, t in enumerate(tasks)]})))
        db.commit()
    db.close()
    return {"X-User-Id": uid}


def _do(uid, source="quick_review", sid=None):
    db = SessionLocal()
    try:
        return eng.record_activity(db, uid, source, sid or str(uuid.uuid4()))
    finally:
        db.close()


def _summary(uid):
    db = SessionLocal()
    try:
        return eng.summary(db, uid)
    finally:
        db.close()


def test_streak_counts_days_in_the_learners_timezone(monkeypatch):
    _user("s1")
    # 23:00 IST on day 1 = 17:30 UTC; 00:30 IST next day = 19:00 UTC same UTC day.
    clock = Clock(monkeypatch, datetime.datetime(2026, 10, 5, 17, 30, tzinfo=UTC))
    _do("s1")
    clock.now = datetime.datetime(2026, 10, 5, 19, 0, tzinfo=UTC)
    _do("s1")
    assert _summary("s1")["streak"] == 2


def test_one_action_keeps_the_streak_and_missed_day_breaks_it(monkeypatch):
    _user("s2")
    clock = Clock(monkeypatch, datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))
    for _ in range(3):
        _do("s2")
        clock.days(1)
    assert _summary("s2")["streak"] == 3 and _summary("s2")["at_risk"] is True
    clock.days(1)  # a full day missed, no freezes
    s = _summary("s2")
    assert s["streak"] == 0 and s["repair"]["streak"] == 3


def test_freeze_is_earned_at_7_days_and_covers_a_missed_day(monkeypatch):
    _user("s3")
    clock = Clock(monkeypatch, datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))
    for _ in range(7):
        _do("s3")
        clock.days(1)
    assert _summary("s3")["freezes"] == 1
    clock.days(1)  # missed one day
    s = _summary("s3")
    assert s["streak"] == 7 and s["freezes"] == 0
    assert any(d["protected"] for d in s["week"])
    _do("s3")
    assert _summary("s3")["streak"] == 8


def test_break_mode_pauses_the_streak(monkeypatch):
    h = _user("s4")
    clock = Clock(monkeypatch, datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))
    _do("s4"); clock.days(1); _do("s4")
    r = client.post("/api/engagement/s4/break", headers=h, json={"days": 3})
    assert r.status_code == 200, r.text
    clock.days(3)
    assert _summary("s4")["streak"] == 2
    _do("s4")
    assert _summary("s4")["streak"] == 3
    over = client.post("/api/engagement/s4/break", headers=h, json={"days": 5})
    assert over.status_code == 400  # 7 break days a month


def test_broken_streak_can_be_repaired_by_meeting_the_goal_twice(monkeypatch):
    _user("s5")
    clock = Clock(monkeypatch, datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))
    for _ in range(5):
        _do("s5"); clock.days(1)
    clock.days(1)
    assert _summary("s5")["streak"] == 0
    for _ in range(2):  # goal = 20 XP; two quick reviews = 20
        _do("s5"); _do("s5"); clock.days(1)
    assert _summary("s5")["streak"] == 5 + 2


def test_xp_once_per_source_and_daily_goal_bonus(monkeypatch):
    _user("s6")
    Clock(monkeypatch, datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))
    first = _do("s6", "interview", "sess-1")
    again = _do("s6", "interview", "sess-1")
    assert first["awarded"] == 30 + 10 and first["goal_met"] is True  # 30 >= 20 goal, +10 bonus
    assert again == {"awarded": 0, "duplicate": True}
    assert _summary("s6")["xp_total"] == 40


def test_same_test_topic_again_today_earns_no_extra_xp(monkeypatch):
    _user("s7")
    Clock(monkeypatch, datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))
    db = SessionLocal()
    a = eng.record_activity(db, "s7", "test", "t-1", repeat_key="sql")
    b = eng.record_activity(db, "s7", "test", "t-2", repeat_key="sql")
    db.close()
    assert a["awarded"] == 15 and b["awarded"] == 0


def test_plan_tasks_are_verified_once_per_week_and_reopen_gives_xp_back(monkeypatch):
    _user("s8")
    Clock(monkeypatch, datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))
    db = SessionLocal()
    log_journey_event(db, "s8", "weekly_task_completed", "x", evidence={"id": "not-in-plan", "title": "Fake"})
    log_journey_event(db, "s8", "weekly_task_completed", "x", evidence={"id": "t0", "title": "Read chapter 3"})
    log_journey_event(db, "s8", "weekly_task_completed", "x", evidence={"id": "t0", "title": "Read chapter 3"})
    db.close()
    assert _summary("s8")["xp_total"] == 20 + 10  # one task (+ goal bonus), the fake one ignored
    db = SessionLocal()
    log_journey_event(db, "s8", "weekly_task_reopened", "x", evidence={"id": "t0"})
    db.close()
    assert _summary("s8")["xp_total"] == 10


def test_sandbox_claims_need_a_real_completed_session(monkeypatch):
    _user("s9")
    Clock(monkeypatch, datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))
    db = SessionLocal()
    db.add(SandboxSession(id="iv-1", user_id="s9", type="interview", title="x", status="completed", score=70))
    db.add(SandboxSession(id="iv-2", user_id="s9", type="interview", title="x", status="in_progress"))
    db.commit()
    log_journey_event(db, "s9", "task_completed", "x", evidence={"sandbox_type": "interview"}, impact={"sandbox_session_id": "iv-2"})
    log_journey_event(db, "s9", "task_completed", "x", evidence={"sandbox_type": "interview"}, impact={"sandbox_session_id": "nope"})
    assert db.query(XpEvent).filter_by(user_id="s9").count() == 0
    log_journey_event(db, "s9", "task_completed", "x", evidence={"sandbox_type": "interview"}, impact={"sandbox_session_id": "iv-1"})
    db.close()
    assert _summary("s9")["xp_total"] == 40


def test_levels_and_settings_api(monkeypatch):
    h = _user("s10")
    assert eng.level_for(0)["level"] == 1 and eng.level_for(149)["level"] == 2 and eng.level_for(3000)["level"] == 10
    assert eng.level_for(3800)["level"] == 11
    r = client.put("/api/engagement/s10", headers=h, json={"goal_minutes": 20, "study_time": "20:30", "timezone": "Asia/Kolkata"})
    assert r.status_code == 200 and r.json()["goal_xp"] == 40 and r.json()["study_time"] == "20:30"
    assert client.put("/api/engagement/s10", headers=h, json={"goal_minutes": 7}).status_code == 400
    assert client.put("/api/engagement/s10", headers=h, json={"timezone": "Mars/Base"}).status_code == 400
    assert client.get("/api/engagement/s10", headers={"X-User-Id": "someone-else"}).status_code == 403


def test_retention_metrics_are_aggregate_and_admin_only(monkeypatch):
    from app.models import DailyActivity
    from app.services.engagement_metrics import retention_metrics
    db = SessionLocal()
    signup = datetime.datetime(2026, 9, 7, 10, 0)  # a Monday
    plan = (("m1", [1, 8]), ("m2", [1]), ("m3", []))
    for uid, _ in plan:
        db.add(User(id=uid, name=uid, created_at=signup))
    db.commit()  # users first: Postgres enforces the daily_activity -> users foreign key
    for uid, active_days in plan:
        for k in active_days:
            db.add(DailyActivity(user_id=uid, local_date=signup.date() + datetime.timedelta(days=k), xp=10, actions=1,
                                 goal_met=False, freeze_used=False, on_break=False))
    db.commit()
    m = retention_metrics(db, today=datetime.date(2026, 10, 20), weeks=8)
    db.close()
    week = next(c for c in m["cohorts"] if c["week_of"] == "2026-09-07")
    assert week["signups"] == 3 and week["day_1"] == 66.7 and week["week_2"] == 33.3 and week["month_1"] == 0.0
    assert "m1" not in json.dumps(m)  # aggregates only
    h = _user("not-admin")
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "boss@delta.test")
    assert client.get("/api/engagement/admin/metrics", headers=h).status_code == 403


def test_account_erasure_removes_habit_data(monkeypatch):
    import app.services.compliance as comp
    from app.models import DailyActivity, UserEngagement
    h = _user("s11")
    Clock(monkeypatch, datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))
    _do("s11")
    monkeypatch.setattr(comp, "delete_auth_user", lambda uid: True)
    r = client.request("DELETE", "/api/privacy/s11", headers=h, json={"confirm": "DELETE"})
    assert r.status_code == 200, r.text
    db = SessionLocal()
    assert db.query(XpEvent).filter_by(user_id="s11").count() == 0
    assert db.query(DailyActivity).filter_by(user_id="s11").count() == 0
    assert db.get(UserEngagement, "s11") is None
    db.close()
