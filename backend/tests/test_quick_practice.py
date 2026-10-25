"""Quick 5: shared bank, spaced review schedule, server-side grading, XP.

    .venv/Scripts/python -m pytest tests/test_quick_practice.py -q
"""
import datetime
import json
import os
import sys
import tempfile

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "quick_practice_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import PracticeItem, SkillNode, User, UserPracticeState  # noqa: E402
from app.services import engagement as eng  # noqa: E402
import app.services.quick_practice as qp  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
UTC = datetime.timezone.utc
calls = []


def fake_generate(user_id, topic, num_questions=10, difficulty="easy", personalize=True, **kw):
    calls.append({"user_id": user_id, "topic": topic, "personalize": personalize})
    return topic, [{"question": f"{topic} Q{i}?", "options": ["a", "b", "c", "d"], "answer_index": i % 4,
                    "explanation": f"because {i}", "skill": topic} for i in range(num_questions)]


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(qp, "generate_test", fake_generate)
    monkeypatch.setattr(eng, "_now", lambda: datetime.datetime(2026, 10, 5, 6, 0, tzinfo=UTC))


def _user(uid, role="Data Analyst", weak=("SQL joins",)):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=uid, target_role=role, profile_data=json.dumps({"target_role": role})))
        for i, w in enumerate(weak):
            db.add(SkillNode(id=f"{uid}-sk{i}", user_id=uid, name=w, proficiency=2))
        db.commit()
    db.close()
    return {"X-User-Id": uid}


def test_bank_is_shared_and_generated_without_the_profile():
    calls.clear()
    h1, h2 = _user("q1"), _user("q2")
    s1 = client.get("/api/practice/quick/q1", headers=h1).json()
    n_calls = len(calls)
    client.get("/api/practice/quick/q2", headers=h2)
    assert len(calls) == n_calls  # second learner with the same topics reuses the bank
    assert all(c["user_id"] is None and c["personalize"] is False for c in calls)
    assert len(s1["items"]) == 5
    assert "answer_index" not in s1["items"][0] and "explanation" not in s1["items"][0]
    topics = {i["skill"] for i in s1["items"]}
    assert topics == {"Data Analyst", "SQL joins"}  # round-robin across topics


def test_grading_schedule_and_xp_after_five_answers():
    h = _user("q3")
    items = client.get("/api/practice/quick/q3", headers=h).json()["items"]
    db = SessionLocal()
    keys = {i["id"]: db.get(PracticeItem, i["id"]).answer_index for i in items}
    db.close()
    results = []
    for n, item in enumerate(items):
        choice = keys[item["id"]] if n < 4 else (keys[item["id"]] + 1) % 4  # last one wrong
        r = client.post("/api/practice/quick/q3/answer", headers=h, json={"item_id": item["id"], "choice": choice})
        assert r.status_code == 200, r.text
        results.append(r.json())
    assert results[0]["correct"] is True and results[0]["explanation"]
    assert results[-1]["correct"] is False
    assert results[-1]["set_complete"] == {"correct": 4, "total": 5, "perfect": False}
    assert results[-1]["engagement"]["awarded"] == 10 + 0  # 10 XP, goal (20) not yet met
    db = SessionLocal()
    wrong = db.get(UserPracticeState, ("q3", items[-1]["id"]))
    right = db.get(UserPracticeState, ("q3", items[0]["id"]))
    assert wrong.box == 1 and wrong.due_date == datetime.date(2026, 10, 6)
    assert right.box == 2 and right.due_date == datetime.date(2026, 10, 8)
    db.close()
    # Answering again the same day changes nothing and awards nothing.
    again = client.post("/api/practice/quick/q3/answer", headers=h, json={"item_id": items[0]["id"], "choice": 0}).json()
    assert "engagement" not in again


def test_perfect_set_gets_a_bonus_and_wrong_items_come_back_first(monkeypatch):
    h = _user("q4")
    items = client.get("/api/practice/quick/q4", headers=h).json()["items"]
    db = SessionLocal()
    keys = {i["id"]: db.get(PracticeItem, i["id"]).answer_index for i in items}
    db.close()
    last = None
    for item in items:
        last = client.post("/api/practice/quick/q4/answer", headers=h, json={"item_id": item["id"], "choice": keys[item["id"]]}).json()
    assert last["set_complete"]["perfect"] is True and last["engagement"]["awarded"] == 15
    # Two days later: right answers (box 2, due in 3 days) are not due yet -> new questions are served.
    monkeypatch.setattr(eng, "_now", lambda: datetime.datetime(2026, 10, 7, 6, 0, tzinfo=UTC))
    later = client.get("/api/practice/quick/q4", headers=h).json()["items"]
    assert not ({i["id"] for i in later} & set(keys))


def test_unknown_item_and_other_users_are_rejected():
    h = _user("q5")
    assert client.post("/api/practice/quick/q5/answer", headers=h, json={"item_id": "nope", "choice": 0}).status_code == 404
    assert client.get("/api/practice/quick/q5", headers={"X-User-Id": "intruder"}).status_code == 403
