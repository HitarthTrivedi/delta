"""AI interview: model routing, field rules and per-session settings.

    .venv/Scripts/python -m pytest tests/test_interview.py -q

Throwaway SQLite DB (or TEST_DATABASE_URL), header auth, AI calls stubbed.
"""
import json
import os
import sys
import tempfile

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "interview_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
import app.services.interview_ai as iai  # noqa: E402
import app.routers.sandbox_interview as sir  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)


@pytest.fixture(autouse=True)
def dev_header_auth(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)


def _student(uid, role):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=uid, target_role=role,
                    profile_data=json.dumps({"target_role": role, "name": uid})))
        db.commit()
    db.close()
    return {"X-User-Id": uid}


def _ok(r):
    assert r.status_code == 200, (r.status_code, r.text)
    return r.json()


def test_turns_use_the_lite_model(monkeypatch):
    H = _student("iv_lite", "Data Analyst")
    models = []
    monkeypatch.setattr(iai, "generate_response", lambda p, **k: models.append(k.get("task")) or "Tell me about a dataset you cleaned.")
    st = _ok(client.post("/api/sandbox/interview/iv_lite/start", headers=H, json={"role_type": "technical", "num_questions": 3}))
    _ok(client.post(f"/api/sandbox/interview/iv_lite/sessions/{st['session_id']}/respond", headers=H, json={"answer": "I used pandas."}))
    from app.services.ai_service import resolve_model
    assert models and all(m == "interview_turn" for m in models)
    assert resolve_model("interview_turn") == settings.GEMINI_LITE_MODEL


def test_system_design_is_not_offered_to_non_tech_fields(monkeypatch):
    H = _student("iv_nurse", "Staff Nurse")
    monkeypatch.setattr(iai, "generate_response", lambda p, **k: "How would you triage two patients arriving together?")
    st = _ok(client.post("/api/sandbox/interview/iv_nurse/start", headers=H, json={"role_type": "system_design"}))
    assert st["settings"]["field"] == "healthcare"
    assert st["role_type"] == "technical"
    assert _ok(client.get(f"/api/sandbox/interview/iv_nurse/sessions/{st['session_id']}", headers=H))["title"] == "Role Knowledge Interview"


def test_system_design_stays_for_software(monkeypatch):
    H = _student("iv_swe", "Backend Software Engineer")
    monkeypatch.setattr(iai, "generate_response", lambda p, **k: "Design a URL shortener.")
    st = _ok(client.post("/api/sandbox/interview/iv_swe/start", headers=H, json={"role_type": "system_design"}))
    assert st["role_type"] == "system_design"


def test_settings_are_fixed_for_the_whole_session(monkeypatch):
    H = _student("iv_fixed", "Chartered Accountant")
    monkeypatch.setattr(iai, "generate_response", lambda p, **k: "Walk me through a bank reconciliation.")
    st = _ok(client.post("/api/sandbox/interview/iv_fixed/start", headers=H, json={"role_type": "technical", "num_questions": 3}))

    def no_reload(*a, **k):
        raise AssertionError("respond must reuse the stored settings, not rebuild them from the profile")
    monkeypatch.setattr(sir, "normalize_settings", no_reload)
    r = _ok(client.post(f"/api/sandbox/interview/iv_fixed/sessions/{st['session_id']}/respond", headers=H, json={"answer": "Match the ledger."}))
    assert r["total_questions"] == 3


class _FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_tts_needs_a_key(monkeypatch):
    H = _student("iv_tts0", "Staff Nurse")
    monkeypatch.setattr(settings, "GOOGLE_TTS_API_KEY", "")
    assert _ok(client.get("/api/sandbox/interview/iv_tts0/avatar", headers=H))["tts"] is False
    r = client.post("/api/sandbox/interview/iv_tts0/tts", headers=H, json={"text": "Hello there."})
    assert r.status_code == 503


def test_tts_builds_safe_ssml_and_word_times(monkeypatch):
    H = _student("iv_tts1", "Staff Nurse")
    monkeypatch.setattr(settings, "GOOGLE_TTS_API_KEY", "k")
    monkeypatch.setattr(settings, "INTERVIEW_TTS_VOICES", "en-IN-Neural2-A,en-IN-Neural2-D")
    sent = {}

    def fake_post(url, json=None, timeout=None, headers=None):
        sent.update(body=json, headers=headers, url=url)
        # Google skipped mark "2": its time must fall back to the previous word's.
        return _FakeResponse({"audioContent": "QUJD", "timepoints": [
            {"markName": "0", "timeSeconds": 0.0}, {"markName": "1", "timeSeconds": 0.42},
            {"markName": "3", "timeSeconds": 1.1}]})
    monkeypatch.setattr(sir.requests, "post", fake_post)

    out = _ok(client.post("/api/sandbox/interview/iv_tts1/tts", headers=H,
                          json={"text": "Tell <me> about R&D work", "voice": "en-US-Evil-Voice"}))
    ssml = sent["body"]["input"]["ssml"]
    assert "<me>" not in ssml and "&lt;me&gt;" in ssml and "R&amp;D" in ssml
    assert sent["body"]["voice"] == {"languageCode": "en-IN", "name": "en-IN-Neural2-A"}  # not allowed -> default
    assert sent["headers"] == {"X-Goog-Api-Key": "k"} and "key=" not in sent["url"]
    assert out["words"] == ["Tell", "<me>", "about", "R&D", "work"]
    assert out["wtimes"] == [0, 420, 420, 1100, 1100]
    assert out["audio"] == "QUJD"


def test_tts_reports_google_failure(monkeypatch):
    H = _student("iv_tts2", "Staff Nurse")
    monkeypatch.setattr(settings, "GOOGLE_TTS_API_KEY", "k")
    bad = _FakeResponse({})
    bad.status_code = 403
    monkeypatch.setattr(sir.requests, "post", lambda *a, **k: bad)
    assert client.post("/api/sandbox/interview/iv_tts2/tts", headers=H, json={"text": "Hi"}).status_code == 502
