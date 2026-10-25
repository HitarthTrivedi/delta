"""Phase 2 gamification: daily quests, weekly challenge, badges, opt-in leagues,
and the consented "Consistent learner" recruiter badge.

    .venv/Scripts/python -m pytest tests/test_gamification_phase2.py -q
"""
import datetime
import os
import sys
import tempfile
import uuid

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "phase2_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import DailyActivity, LeagueMember, SkillNode, User, UserBadge  # noqa: E402
from app.services import compliance, engagement as eng, leagues, quests  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
UTC = datetime.timezone.utc
MONDAY = datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC)  # 11:30 IST, a Monday


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


def _user(uid, name=None, terms=True):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=name or f"{uid} Tester"))
        db.commit()
        if terms:
            compliance.record_consent(db, uid, compliance.TERMS, True)
    db.close()
    return {"X-User-Id": uid}


def _do(uid, source="quick_review", sid=None, **kw):
    db = SessionLocal()
    try:
        return eng.record_activity(db, uid, source, sid or str(uuid.uuid4()), **kw)
    finally:
        db.close()


def _summary(uid):
    db = SessionLocal()
    try:
        return eng.summary(db, uid)
    finally:
        db.close()


def _fixed_quests(monkeypatch, keys=("quick5", "practice", "goal")):
    monkeypatch.setattr(quests, "todays_quests", lambda db, uid, today: list(keys))


# ── quests ──────────────────────────────────────────────────────────────────

def test_quests_are_stable_for_the_day_and_always_include_quick5(clock):
    _user("dq0")
    db = SessionLocal()
    today = datetime.date(2026, 10, 5)
    a = quests.todays_quests(db, "dq0", today)
    b = quests.todays_quests(db, "dq0", today)
    db.close()
    assert a == b and a[0] == "quick5" and len(set(a)) == 3
    assert "plan_task" not in a  # no plan yet, so no plan quest


def test_finishing_all_quests_pays_a_bonus_once(clock, monkeypatch):
    _user("dq1")
    _fixed_quests(monkeypatch)
    _do("dq1", "quick_review", "2026-10-05")
    assert _summary("dq1")["quests"]["all_done"] is False
    r = _do("dq1", "interview", "iv-dq1")  # practice; 10 + 30 XP passes the 20 XP goal
    assert r["quests_done"] is True
    s = _summary("dq1")
    assert s["quests"]["all_done"] and all(i["done"] for i in s["quests"]["items"])
    # quick 10 + interview 30 + goal 10 + quests 15
    assert s["xp_total"] == 65
    again = _do("dq1", "test", "t-dq1")
    assert again["quests_done"] is False and _summary("dq1")["xp_total"] == 80


def test_weekly_challenge_earns_a_freeze_then_xp_when_freezes_are_full(clock, monkeypatch):
    _user("dq2")
    _fixed_quests(monkeypatch, ("quick5", "practice", "goal"))
    for day in range(4):
        _do("dq2", "quick_review", f"day{day}")
        r = _do("dq2", "interview", f"iv{day}")
        clock.days(1)
    assert r["challenge_won"] == "freeze"
    s = _summary("dq2")
    assert s["freezes"] == 1 and s["quests"]["challenge"]["won"] and s["quests"]["challenge"]["reward"] == "freeze"

    clock.days(3)  # next Monday
    for day in range(4):
        if day == 3:  # freezes already full on the deciding day
            db = SessionLocal()
            e = eng.get_or_create(db, "dq2")
            eng.roll_forward(db, e, eng.local_today(e))
            e.streak_freezes = eng.MAX_FREEZES
            db.commit()
            db.close()
        _do("dq2", "quick_review", f"w2day{day}")
        r = _do("dq2", "interview", f"w2iv{day}")
        clock.days(1)
    assert r["challenge_won"] == "xp"


# ── badges ──────────────────────────────────────────────────────────────────

def test_first_quick5_earns_a_badge_and_the_summary_shows_it(clock):
    _user("b1")
    r = _do("b1", "quick_review", "2026-10-05")
    assert [b["key"] for b in r["badges"]] == ["quick5"]
    s = _summary("b1")
    assert s["badges"]["count"] == 1 and s["badges"]["latest"]["title"] == "First Quick 5"
    assert _do("b1", "test", "t-b1")["badges"][0]["title"] == "First test"


def test_badges_list_progress_and_mastery_needs_evidence(clock):
    h = _user("b2")
    db = SessionLocal()
    for i, ev in enumerate(["claimed", "claimed", "practiced"]):
        db.add(SkillNode(id=str(uuid.uuid4()), user_id="b2", name=f"skill{i}", proficiency=9, evidence_type=ev))
    db.commit()
    db.close()
    body = client.get("/api/engagement/b2/badges", headers=h).json()["badges"]
    mastery = next(b for b in body if b["key"] == "mastery")
    assert mastery["tier"] == 1 and mastery["progress"] == 1  # the two claimed skills don't count
    quick = next(b for b in body if b["key"] == "quick5")
    assert quick["tier"] == 0 and quick["next"]["at"] == 1
    assert client.get("/api/engagement/b2/badges", headers={"X-User-Id": "other"}).status_code == 403


# ── leagues ─────────────────────────────────────────────────────────────────

def test_leagues_are_opt_in_with_consent_and_show_only_first_name_and_initial(clock):
    h = _user("l1", "Asha Rao")
    _user("l2", "Vikram Mehta Singh")
    assert client.get("/api/engagement/l1/league", headers=h).json() == {"opted_in": False}
    nope = _user("l-noterms", terms=False)
    assert client.put("/api/engagement/l-noterms/league", headers=nope, json={"enabled": True}).status_code == 400

    r = client.put("/api/engagement/l1/league", headers=h, json={"enabled": True})
    assert r.status_code == 200 and r.json()["tier_name"] == "Bronze"
    db = SessionLocal()
    assert compliance.latest_consent(db, "l1", compliance.LEADERBOARD_VISIBILITY).action == "granted"
    db.close()
    client.put("/api/engagement/l2/league", headers={"X-User-Id": "l2"}, json={"enabled": True})
    _do("l2", "interview", "iv-l2")
    board = client.get("/api/engagement/l1/league", headers=h).json()
    assert [row["name"] for row in board["rows"]] == ["Vikram S.", "Asha R."]
    assert board["rows"][1]["you"] is True and board["rows"][0]["xp"] == 40

    client.put("/api/engagement/l2/league", headers={"X-User-Id": "l2"}, json={"enabled": False})
    assert [row["name"] for row in client.get("/api/engagement/l1/league", headers=h).json()["rows"]] == ["Asha R."]


def test_a_full_group_opens_a_new_one(clock, monkeypatch):
    monkeypatch.setattr(leagues, "GROUP_SIZE", 2)
    for uid in ("g1", "g2", "g3"):
        _user(uid)
        client.put(f"/api/engagement/{uid}/league", headers={"X-User-Id": uid}, json={"enabled": True})
    db = SessionLocal()
    groups = {db.get(LeagueMember, (uid, datetime.date(2026, 10, 5))).cohort_id for uid in ("g1", "g2", "g3")}
    db.close()
    assert len(groups) == 2


def test_top_of_the_week_moves_up_and_demotion_is_forgiving(clock, monkeypatch):
    monkeypatch.setattr(leagues, "NEW_MEMBER_WEEKS", 0)  # skip the new-member protection here
    ids = [f"p{i}" for i in range(10)]
    for uid in ids:
        _user(uid)
    db = SessionLocal()
    for uid in ids:
        e = eng.get_or_create(db, uid)
        e.leagues_opt_in, e.league_tier = True, 1  # everyone in Silver
    db.commit()
    for uid in ids:
        leagues.ensure_membership(db, eng.get_or_create(db, uid))
    db.close()
    # p0..p7 earn XP; p8 studies on 3 days (small XP), p9 does nothing.
    for i, uid in enumerate(ids[:8]):
        _do(uid, "interview", f"iv-{uid}", bonus_xp=100 - i)
    for d in range(3):
        _do("p8", "quick_review", f"p8-{d}")
        clock.days(1)
    clock.days(4)  # next Monday
    out = {}
    for uid in ids:
        out[uid] = client.get(f"/api/engagement/{uid}/league", headers={"X-User-Id": uid}).json()["tier_name"]
    up, down = leagues.zones(10)
    assert (up, down) == (3, 3)
    assert out["p0"] == out["p1"] == out["p2"] == "Gold"
    assert out["p8"] == "Silver"  # bottom three, but studied on 3 days: safe
    assert out["p9"] == "Bronze"  # bottom three and inactive: moves down one


def test_new_members_are_never_moved_down_and_skipped_weeks_cost_nothing(clock):
    for i in range(10):
        _user(f"n{i}")
    db = SessionLocal()
    for i in range(10):
        e = eng.get_or_create(db, f"n{i}")
        e.leagues_opt_in, e.league_tier = True, 2
    db.commit()
    for i in range(10):
        leagues.ensure_membership(db, eng.get_or_create(db, f"n{i}"))
    db.close()
    for i in range(7):
        _do(f"n{i}", "interview", f"iv-n{i}")
    clock.days(14)  # two Mondays later; n9 never came back in between
    assert client.get("/api/engagement/n9/league", headers={"X-User-Id": "n9"}).json()["tier_name"] == "Gold"


# ── recruiter "Consistent learner" ─────────────────────────────────────────

def test_consistent_learner_needs_its_own_consent_and_20_active_days(clock):
    _user("c1")
    _user("c2")
    db = SessionLocal()
    start = clock.now.date() - datetime.timedelta(days=24)
    for uid in ("c1", "c2"):
        for k in range(21):
            db.add(DailyActivity(user_id=uid, local_date=start + datetime.timedelta(days=k), xp=10, actions=1,
                                 goal_met=False, freeze_used=False, on_break=False))
    db.commit()
    assert eng.consistent_learners(db, ["c1", "c2"]) == set()
    client.post("/api/privacy/c1/consent", headers={"X-User-Id": "c1"},
                json={"purpose": compliance.RECRUITER_HABIT_BADGE, "granted": True})
    assert eng.consistent_learners(db, ["c1", "c2"]) == {"c1"}
    db.close()


def test_erasure_removes_badges_and_league_places(clock, monkeypatch):
    import app.services.compliance as comp
    h = _user("e1")
    client.put("/api/engagement/e1/league", headers=h, json={"enabled": True})
    _do("e1", "quick_review", "2026-10-05")
    monkeypatch.setattr(comp, "delete_auth_user", lambda uid: True)
    assert client.request("DELETE", "/api/privacy/e1", headers=h, json={"confirm": "DELETE"}).status_code == 200
    db = SessionLocal()
    assert db.query(UserBadge).filter_by(user_id="e1").count() == 0
    assert db.query(LeagueMember).filter_by(user_id="e1").count() == 0
    db.close()
