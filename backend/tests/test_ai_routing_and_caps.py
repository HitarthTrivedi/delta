"""Production backlog #3 and #5: every AI call is routed by task from config,
metered into a daily ledger (no personal data), alerts the admins at budget
thresholds and degrades to the lite model at 100%, and per-plan monthly caps
limit each learner's AI features (refunded when the call fails).

    .venv/Scripts/python -m pytest tests/test_ai_routing_and_caps.py -q
"""
import json
import os
import pathlib
import re
import sys
import tempfile
import types

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "ai_routing_caps_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AiBudgetAlert, AiFeatureUse, AiUsageDaily, User  # noqa: E402
from app.services import ai_budget, ai_service, ai_usage, usage_caps  # noqa: E402
import app.routers.sandbox_theory as st  # noqa: E402
import app.services.compliance as comp  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
APP_DIR = pathlib.Path(__file__).resolve().parents[1] / "app"
QUESTIONS = [{"question": f"Q{i}?", "options": ["a", "b", "c", "d"], "skill": "SQL", "answer_index": 0,
              "explanation": "x"} for i in range(5)]


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    from app.limiter import limiter
    limiter.reset()  # every test request shares one client address
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", True)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "boss@delta.test")
    monkeypatch.setattr(settings, "AI_MONTHLY_BUDGET_USD", "")
    monkeypatch.setattr(settings, "AI_ROUTES_JSON", "")
    monkeypatch.setattr(settings, "AI_CAPS_JSON", "")
    ai_budget._state.update({"checked_at": float("-inf"), "degraded": False})
    yield
    ai_budget._state.update({"checked_at": float("-inf"), "degraded": False})


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json()


def _student(uid):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=uid, profile_data=json.dumps({"audience": "student"})))
        db.commit()
        comp.record_consent(db, uid, comp.TERMS, True)
    db.close()
    return {"X-User-Id": uid, "X-User-Email": f"{uid}@gmail.com"}


def _clear_ledger():
    db = SessionLocal()
    db.query(AiUsageDaily).delete()
    db.query(AiBudgetAlert).delete()
    db.commit()
    db.close()


class FakeGemini:
    """Stands in for google-genai: records the model and reports token usage."""
    def __init__(self):
        self.models = self
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        return types.SimpleNamespace(text="ok from gemini", usage_metadata=types.SimpleNamespace(
            prompt_token_count=1000, candidates_token_count=500))


@pytest.fixture
def gemini(monkeypatch):
    fake = FakeGemini()
    monkeypatch.setattr(ai_service, "_clients", [fake])
    monkeypatch.setattr(ai_service, "_client_cycle", __import__("itertools").cycle([fake]))
    monkeypatch.setattr(ai_service, "_clients_initialised", True)
    return fake


def test_every_task_in_code_has_a_route():
    used = set()
    for path in APP_DIR.rglob("*.py"):
        used |= set(re.findall(r'task="([a-z_]+)"', path.read_text(encoding="utf-8")))
    assert used and used <= set(ai_usage.routes()), used - set(ai_usage.routes())


def test_routes_resolve_from_config(monkeypatch):
    assert ai_service.resolve_model("theory_test") == settings.GEMINI_MODEL
    assert ai_service.resolve_model("interview_turn") == settings.GEMINI_LITE_MODEL
    assert ai_service.resolve_model("chat_intent") == settings.GROQ_FAST_MODEL
    assert ai_service.resolve_model("chat_reply") in settings.GROQ_QUALITY_MODELS.split(",")
    assert ai_service.resolve_model("theory_test", model="some-model") == "some-model"
    monkeypatch.setattr(settings, "AI_ROUTES_JSON", '{"theory_test": "lite", "job_extract": "gemini-x"}')
    assert ai_service.resolve_model("theory_test") == settings.GEMINI_LITE_MODEL
    assert ai_service.resolve_model("job_extract") == "gemini-x"
    monkeypatch.setattr(settings, "AI_ROUTES_JSON", "not json")
    assert ai_service.resolve_model("theory_test") == settings.GEMINI_MODEL  # bad override: defaults


def test_calls_are_metered_and_groq_falls_back_to_the_task_route(monkeypatch, gemini):
    _clear_ledger()
    assert ai_service.generate_response("hello", task="theory_test") == "ok from gemini"
    assert ai_service.generate_response("hello", task="theory_test") == "ok from gemini"
    assert gemini.calls == [settings.GEMINI_MODEL] * 2

    def broken_groq(*_a, **_k):
        raise RuntimeError("rate limited")
    monkeypatch.setattr(ai_service, "_get_groq", lambda: object())
    monkeypatch.setattr(ai_service, "_groq_generate", broken_groq)
    assert ai_service.generate_response("hi", task="chat_reply") == "ok from gemini"
    assert gemini.calls[-1] == settings.GEMINI_LITE_MODEL  # the task's fallback, not the full model

    db = SessionLocal()
    rows = {(r.task, r.model): r for r in db.query(AiUsageDaily)}
    full = rows[("theory_test", settings.GEMINI_MODEL)]
    assert (full.calls, full.input_tokens, full.output_tokens) == (2, 2000, 1000)
    price = ai_usage.prices()[settings.GEMINI_MODEL]
    assert full.est_cost_usd == pytest.approx(2 * (1000 * price[0] + 500 * price[1]) / 1_000_000)
    assert rows[("chat_reply", settings.GEMINI_LITE_MODEL)].calls == 1
    db.close()


def test_a_ledger_failure_never_breaks_the_call(monkeypatch, gemini):
    import app.database as database

    def broken_session():
        raise RuntimeError("database down")
    monkeypatch.setattr(database, "SessionLocal", broken_session)
    assert ai_service.generate_response("hello", task="theory_test") == "ok from gemini"


def test_budget_alerts_once_then_degrades(monkeypatch):
    _clear_ledger()
    sent = []
    monkeypatch.setattr("app.services.email_service._dispatch", lambda to, name, subject, html: sent.append(subject) or True)
    monkeypatch.setattr(settings, "AI_MONTHLY_BUDGET_USD", "1.00")
    db = SessionLocal()
    ai_usage.record("theory_test", "gemini-2.5-flash", 0, 220_000)  # 0.55 USD
    assert ai_budget.check(db)["pct"] == pytest.approx(55.0)
    ai_budget.check(db)  # no repeat
    assert sent == ["Delta AI spend at 50% of this month's budget"]
    assert ai_budget.degraded() is False
    ai_usage.record("theory_test", "gemini-2.5-flash", 0, 200_000)  # +0.50 USD -> 105%
    state = ai_budget.check(db)
    assert state["degraded"] is True and sent[1:] == ["Delta AI spend at 80% of this month's budget",
                                                      "Delta AI spend at 100% of this month's budget"]
    ai_budget._state["checked_at"] = float("-inf")
    assert ai_budget.degraded() is True
    assert ai_service.resolve_model("theory_test") == settings.GEMINI_LITE_MODEL  # everything drops to lite
    assert ai_service.resolve_model("chat_intent") == settings.GROQ_FAST_MODEL  # Groq is already cheap
    h = _student("ai-degraded")
    assert client.post("/api/opportunities/ai-degraded/generate", headers=h).status_code == 503
    summary = ok(client.get("/api/engagement/admin/ai-usage", headers={"X-User-Id": "boss", "X-User-Email": "boss@delta.test"}))
    assert summary["alerts_sent"] == [50, 80, 100] and summary["degraded"] is True and summary["breakdown"]
    assert client.get("/api/engagement/admin/ai-usage", headers=h).status_code == 403
    db.close()
    _clear_ledger()


def test_no_budget_means_no_alerts(monkeypatch):
    _clear_ledger()
    sent = []
    monkeypatch.setattr("app.services.email_service._dispatch", lambda *a: sent.append(a) or True)
    ai_usage.record("weekly_brief", "gemini-2.5-flash", 10_000_000, 10_000_000)
    db = SessionLocal()
    assert ai_budget.check(db)["degraded"] is False and sent == []
    db.close()
    assert ai_service.resolve_model("weekly_brief") == settings.GEMINI_MODEL
    _clear_ledger()


def test_caps_by_plan_with_refund_on_failure(monkeypatch):
    monkeypatch.setattr(settings, "AI_CAPS_JSON", '{"solo": {"theory_test": 2}, "college": {"theory_test": 3}}')
    calls = []

    def fake_generate(user_id, topic, n, difficulty, category, area, personalize=True):
        calls.append(topic)
        return topic or "Aptitude", [dict(q) for q in QUESTIONS[:n]]
    monkeypatch.setattr(st, "generate_test", fake_generate)
    h = _student("ai-cap")
    body = {"topic": "SQL", "num_questions": 5}
    ok(client.post("/api/sandbox/theory/ai-cap/start", headers=h, json=body))

    def failing(*_a, **_k):
        raise ValueError("model down")
    monkeypatch.setattr(st, "generate_test", failing)
    assert client.post("/api/sandbox/theory/ai-cap/start", headers=h, json=body).status_code == 503  # refunded
    monkeypatch.setattr(st, "generate_test", fake_generate)
    ok(client.post("/api/sandbox/theory/ai-cap/start", headers=h, json=body))
    over = client.post("/api/sandbox/theory/ai-cap/start", headers=h, json=body)
    assert over.status_code == 429 and "practice tests" in over.json()["detail"] and "More on 1 " in over.json()["detail"]
    assert len(calls) == 2

    use = ok(client.get("/api/engagement/usage/ai-cap", headers=h))
    row = next(f for f in use["features"] if f["feature"] == "theory_test")
    assert (use["plan"], row["used"], row["cap"]) == ("solo", 2, 2)
    assert client.get("/api/engagement/usage/ai-cap", headers=_student("ai-other")).status_code == 403

    db = SessionLocal()
    assert usage_caps.plan_for(db, "ai-cap") == "solo"
    assert "ai_feature_uses" in comp.export_user_data(db, "ai-cap")
    comp.erase_student(db, "ai-cap")
    assert db.query(AiFeatureUse).filter_by(user_id="ai-cap").count() == 0
    db.close()


def test_college_plan_and_month_rollover(monkeypatch):
    import datetime
    admin = {"X-User-Id": "ai-boss", "X-User-Email": "boss@delta.test"}
    c = ok(client.post("/api/college/admin/colleges", headers=admin, json={
        "name": "Caps College", "seat_limit": 5, "first_tpo_email": "tpo@caps.edu"}))
    tpo = {"X-User-Id": "ai-tpo", "X-User-Email": "tpo@caps.edu"}
    ok(client.post("/api/college/me/accept", headers=tpo, json={"policy_version": comp.POLICY_VERSION}))
    b = ok(client.post(f"/api/college/{c['id']}/batches", headers=tpo, json={"name": "CSE"}))
    h = _student("ai-college")
    ok(client.post("/api/college/student/ai-college/join", headers=h, json={"code": b["join_code"]}))
    monkeypatch.setattr(settings, "AI_CAPS_JSON", '{"college": {"job_match": 1}}')
    db = SessionLocal()
    assert usage_caps.plan_for(db, "ai-college") == "college"
    assert usage_caps.claim(db, "ai-college", "job_match") == (True, 1)
    assert usage_caps.claim(db, "ai-college", "job_match") == (False, 1)
    monkeypatch.setattr(usage_caps, "_now", lambda: datetime.datetime(2099, 1, 15))
    assert usage_caps.claim(db, "ai-college", "job_match") == (True, 1)  # new month, fresh count
    assert usage_caps.claim(db, "ai-college", "chat")[0] is True  # chat keeps the default cap
    db.close()


def test_budget_is_checked_right_away_even_just_after_boot(monkeypatch):
    monkeypatch.setattr(ai_budget, "time", types.SimpleNamespace(monotonic=lambda: 30.0))  # host booted 30 s ago, like a fresh CI runner
    monkeypatch.setattr(settings, "AI_MONTHLY_BUDGET_USD", "1.00")
    calls = []
    monkeypatch.setattr(ai_budget, "refresh", lambda: calls.append(1) or {})
    ai_budget.degraded()
    assert calls == [1]
