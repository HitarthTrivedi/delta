"""Opt-in study reminders: timing, backoff, consent, unsubscribe, web push.

    .venv/Scripts/python -m pytest tests/test_reminders.py -q
"""
import base64
import datetime
import json
import os
import sys
import tempfile
import types

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "reminders_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import http_ece  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ConsentRecord, User, UserEngagement  # noqa: E402
from app.models.engagement import PushSubscription  # noqa: E402
from app.services import compliance, engagement as eng, push_service, reminder_service as rs  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
UTC = datetime.timezone.utc
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(settings, "EMAIL_LINK_SECRET", "test-link-secret")


def _user(uid, consent=True, email=None):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name="Asha Rao", email=email or f"{uid}@mail.test.org"))
        db.commit()
        if consent:
            compliance.record_consent(db, uid, compliance.TERMS, True)
    db.close()
    return {"X-User-Id": uid}


def _eng(**kw):
    base = dict(user_id="x", timezone="Asia/Kolkata", reminders_opt_in=True, study_time="19:00",
                current_streak=0, ignored_nudges=0, last_nudged_on=None, break_until=None)
    base.update(kw)
    return types.SimpleNamespace(**base)


def at(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    return datetime.datetime(2026, 10, day, h, m, tzinfo=IST)


def test_nudge_rules():
    mon = 5  # 2026-10-05 is a Monday
    assert rs.nudge_kind(_eng(reminders_opt_in=False), at(mon, "20:00"), False) is None
    assert rs.nudge_kind(_eng(), at(mon, "20:00"), True) is None             # already studied today
    assert rs.nudge_kind(_eng(), at(mon, "18:59"), False) is None            # before their time
    assert rs.nudge_kind(_eng(), at(mon, "19:00"), False) == "gentle"
    assert rs.nudge_kind(_eng(current_streak=4), at(mon, "19:30"), False) == "streak"
    assert rs.nudge_kind(_eng(study_time=None), at(mon, "18:00"), False) is None  # default 19:00
    assert rs.nudge_kind(_eng(last_nudged_on=datetime.date(2026, 10, 5)), at(mon, "21:00"), False) is None
    assert rs.nudge_kind(_eng(break_until=datetime.date(2026, 10, 6)), at(mon, "20:00"), False) is None
    # Backoff
    yesterday = datetime.date(2026, 10, 4)
    assert rs.nudge_kind(_eng(ignored_nudges=3, last_nudged_on=yesterday), at(mon, "20:00"), False) is None
    assert rs.nudge_kind(_eng(ignored_nudges=3, last_nudged_on=datetime.date(2026, 10, 3)), at(mon, "20:00"), False) == "gentle"
    assert rs.nudge_kind(_eng(ignored_nudges=14), at(mon, "20:00"), False) == "fresh_start"
    assert rs.nudge_kind(_eng(ignored_nudges=14), at(6, "20:00"), False) is None       # Tuesday
    assert rs.nudge_kind(_eng(ignored_nudges=15), at(12, "20:00"), False) is None


def test_reminders_need_terms_consent_and_every_switch_is_recorded():
    h = _user("r1", consent=False)
    assert client.put("/api/engagement/r1/reminders", headers=h, json={"enabled": True}).status_code == 400
    db = SessionLocal()
    compliance.record_consent(db, "r1", compliance.TERMS, True)
    db.close()
    r = client.put("/api/engagement/r1/reminders", headers=h, json={"enabled": True, "channel": "both"})
    assert r.status_code == 200 and r.json()["reminders_opt_in"] is True and r.json()["reminder_channel"] == "both"
    assert client.get("/api/privacy/r1/consent", headers=h).json()["learning_reminders"] is True
    client.put("/api/engagement/r1/reminders", headers=h, json={"enabled": False})
    db = SessionLocal()
    actions = [c.action for c in db.query(ConsentRecord).filter_by(user_id="r1", purpose="learning_reminders")
               .order_by(ConsentRecord.created_at)]
    db.close()
    assert actions == ["granted", "withdrawn"]


def test_sweep_sends_once_a_day_only_when_not_studied(monkeypatch):
    h = _user("r2")
    client.put("/api/engagement/r2", headers=h, json={"study_time": "19:00"})
    client.put("/api/engagement/r2/reminders", headers=h, json={"enabled": True})
    sent = []
    monkeypatch.setattr(rs, "send_nudge_email", lambda **kw: sent.append(kw) or True)
    monkeypatch.setattr(eng, "_now", lambda: datetime.datetime(2026, 10, 5, 13, 0, tzinfo=UTC))  # 18:30 IST
    rs.run_daily_reminders()
    assert sent == []
    monkeypatch.setattr(eng, "_now", lambda: datetime.datetime(2026, 10, 5, 14, 0, tzinfo=UTC))  # 19:30 IST
    rs.run_daily_reminders()
    rs.run_daily_reminders()
    assert len(sent) == 1 and sent[0]["unsubscribe_url"].startswith(settings.FRONTEND_URL)
    assert "streak" not in sent[0]["unsubscribe_url"]
    db = SessionLocal()
    assert db.get(UserEngagement, "r2").ignored_nudges == 1
    db.close()
    # Studying resets the backoff; a learner who already studied today isn't nudged.
    monkeypatch.setattr(eng, "_now", lambda: datetime.datetime(2026, 10, 6, 6, 0, tzinfo=UTC))
    db = SessionLocal()
    eng.record_activity(db, "r2", "quick_review", "2026-10-06")
    assert db.get(UserEngagement, "r2").ignored_nudges == 0
    db.close()
    monkeypatch.setattr(eng, "_now", lambda: datetime.datetime(2026, 10, 6, 15, 0, tzinfo=UTC))
    rs.run_daily_reminders()
    assert len(sent) == 1


def test_unsubscribe_link_turns_reminders_off():
    h = _user("r3")
    client.put("/api/engagement/r3/reminders", headers=h, json={"enabled": True})
    assert client.post("/api/engagement/unsubscribe", json={"u": "r3", "t": "0" * 40}).status_code == 400
    token = eng.unsubscribe_token("r3")
    assert client.post("/api/engagement/unsubscribe", json={"u": "r3", "t": token}).status_code == 200
    assert client.get("/api/engagement/r3", headers=h).json()["reminders_opt_in"] is False


def _browser_subscription():
    key = ec.generate_private_key(ec.SECP256R1())
    pub = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = os.urandom(16)
    enc = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")  # noqa: E731
    return key, enc(pub), enc(auth), auth


def test_push_payload_decrypts_in_the_browser():
    key, p256dh, auth_b64, auth = _browser_subscription()
    body = push_service.encrypt_payload(b'{"title":"hi"}', p256dh, auth_b64)
    assert http_ece.decrypt(body, private_key=key, auth_secret=auth, version="aes128gcm") == b'{"title":"hi"}'


def test_push_send_signs_and_drops_expired_subscriptions(monkeypatch):
    _user("r4")
    keys = push_service.generate_vapid_keys()
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", keys["VAPID_PRIVATE_KEY"])
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", keys["VAPID_PUBLIC_KEY"])
    monkeypatch.setattr(settings, "VAPID_SUBJECT", "mailto:team@example.com")
    _, p256dh, auth_b64, _ = _browser_subscription()
    db = SessionLocal()
    eng.add_push_subscription(db, "r4", "https://push.example.com/send/abc", p256dh, auth_b64)
    calls = []

    class Resp:
        def __init__(self, code):
            self.status_code = code

    monkeypatch.setattr(push_service.requests, "post", lambda url, data=None, headers=None, timeout=None: calls.append(headers) or Resp(201))
    assert push_service.send_to_user(db, "r4", "t", "b", "https://app/today") == 1
    assert calls[0]["Content-Encoding"] == "aes128gcm" and calls[0]["Authorization"].startswith("vapid t=")
    monkeypatch.setattr(push_service.requests, "post", lambda *a, **k: Resp(410))
    assert push_service.send_to_user(db, "r4", "t", "b", "https://app/today") == 0
    assert db.query(PushSubscription).filter_by(user_id="r4").count() == 0
    db.close()
    assert client.get("/api/engagement/push/public-key").json()["key"] == keys["VAPID_PUBLIC_KEY"]
