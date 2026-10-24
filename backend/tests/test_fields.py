"""Delta must work for every field, not just software. Run from backend/:

    .venv/Scripts/python -m pytest tests/test_fields.py -q

Uses a throwaway SQLite database and stubs every AI / network call, so it
never touches the real database or external services.
"""
import json
import os
import sys
import tempfile
from types import SimpleNamespace

_DB = os.path.join(tempfile.mkdtemp(), "fields_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"  # before any app import
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from app.database import Base, engine, SessionLocal  # noqa: E402
import app.models  # noqa: F401,E402
from app.models import User, SandboxSession  # noqa: E402
from app.services.domain_packs import resolve_field, DOMAIN_PACKS  # noqa: E402
import app.services.central_engine as ce  # noqa: E402
import app.services.brief_generator as bg  # noqa: E402
import app.services.market_pulse as mp  # noqa: E402
import app.services.opportunity_adapters as oa  # noqa: E402
import app.services.interview_ai as iai  # noqa: E402
from app.services.readiness import compute_readiness  # noqa: E402

Base.metadata.create_all(bind=engine)
TECH_WORDS = ("python", "docker", "kubernetes", "fastapi", "leetcode", "containeriz", "microservice")


# ── 1. Field resolution ──────────────────────────────────────────────────────

ROLES = {
    "Staff Nurse": "healthcare", "B.Sc Nursing graduate": "healthcare", "Pharmacist": "healthcare",
    "Chartered Accountant": "finance", "CA articleship": "finance", "Economics student": "finance",
    "Retail Store Manager": "business", "Technical Recruiter": "business", "MBA in HR": "business",
    "Civil Site Engineer": "core_engineering", "Maintenance Engineer": "core_engineering",
    "Mechanical Design Engineer": "core_engineering",
    "UPSC aspirant": "public_service", "Civil services": "public_service",
    "Hotel Management Trainee": "hospitality", "Cabin crew": "hospitality",
    "Legal Associate": "law", "School Teacher": "education", "Journalist": "media",
    "Digital Marketing Executive": "marketing", "Sales Executive": "marketing",
    "Backend Developer": "cs_ai", "Software Engineer": "cs_ai", "Solutions Architect": "cs_ai",
    "Data Analyst": "data", "UX Designer": "design", "Interior Designer": "design",
    "Product Manager": "product", "Startup founder": "entrepreneurship", "PhD in Chemistry": "research",
    "": "general", "Something unusual": "general",
}


@pytest.mark.parametrize("role,expected", ROLES.items())
def test_resolve_field_by_role(role, expected):
    assert resolve_field({"target_role": role})["id"] == expected


def test_explicit_field_wins_and_unknown_is_general():
    assert resolve_field({"field": "law", "target_role": "Software Engineer"})["id"] == "law"
    assert resolve_field({})["id"] == "general"
    assert resolve_field({"target_role": "Product Manager", "major": "Computer Science"})["id"] == "product"


def test_every_pack_has_required_keys():
    keys = {"id", "label", "is_tech", "keywords", "skill_taxonomy", "phases", "phase_guidance", "proof_types",
            "portfolio_hint", "interview_formats", "exam_tracks", "opportunity_queries", "weekly_habit",
            "certifications", "competitions", "starter_projects", "rubric", "target_roles"}
    for pid, pack in DOMAIN_PACKS.items():
        assert keys <= set(pack), (pid, keys - set(pack))
        assert len(pack["phases"]) == 3 and len(pack["phase_guidance"]) == 3, pid
        assert len(pack["skill_taxonomy"]) >= 6, pid


# ── 2. Weekly habit: LeetCode only for software ─────────────────────────────

def _user(role):
    return SimpleNamespace(id="u-" + role.replace(" ", "-"), target_role=role)


@pytest.fixture(autouse=True)
def _no_avoided_topics(monkeypatch):
    monkeypatch.setattr(ce, "_avoided_topics", lambda uid: [])


@pytest.mark.parametrize("role", ["Staff Nurse", "Civil Site Engineer", "Chartered Accountant", "Economics student"])
def test_non_software_users_get_field_habit_not_leetcode(role):
    actions = ce._recurring_habit_actions({"target_role": role}, [], _user(role), 0, None)
    assert actions and "leetcode" not in json.dumps(actions).lower()
    assert actions[0]["title"] == resolve_field({"target_role": role})["weekly_habit"]["title"]


def test_software_users_still_get_leetcode():
    actions = ce._recurring_habit_actions({"target_role": "Backend Developer"}, [], _user("Backend Developer"), 0, None)
    assert "leetcode" in json.dumps(actions).lower()


# ── 3. Roadmap: prompt and offline fallback follow the field ────────────────

def _roadmap(monkeypatch, role):
    captured = {}

    def fake(prompt, **k):
        captured["prompt"] = prompt
        raise RuntimeError("AI unavailable")  # force the static fallback too

    monkeypatch.setattr(bg, "generate_response", fake)
    monkeypatch.setattr(bg, "_fetch_trend_intel", lambda r: "")
    user = SimpleNamespace(id="u-road", target_role=role, hours_per_week=8, learning_style="practical")
    out = bg.generate_weekly_brief(user, [], None, onboarding_profile={"target_role": role})
    return captured["prompt"], out


def test_nurse_roadmap_prompt_and_fallback_are_healthcare(monkeypatch):
    prompt, out = _roadmap(monkeypatch, "Staff Nurse")
    assert "Healthcare & Medicine" in prompt and "containerization" not in prompt.lower()
    text = json.dumps(out).lower()
    assert not any(w in text for w in TECH_WORDS), [w for w in TECH_WORDS if w in text]
    assert "clinical" in text


def test_software_fallback_keeps_tech_roadmap(monkeypatch):
    _, out = _roadmap(monkeypatch, "Backend Developer")
    ids = {n["id"] for p in out["phases"] for n in p["nodes"]}
    assert "node-python" in ids


# ── 4. Market signals: no GitHub/StackOverflow for non-tech ──────────────────

def test_market_pulse_skips_github_for_non_tech(monkeypatch):
    calls = []
    monkeypatch.setattr(mp, "_fetch_github_signals", lambda *a: calls.append("github") or [])
    monkeypatch.setattr(mp, "_fetch_stackexchange_signals", lambda *a: calls.append("se") or [])
    monkeypatch.setattr(mp, "_fetch_job_signals", lambda *a: [])
    monkeypatch.setattr(mp, "_fetch_search_market_snapshot", lambda *a: {})
    monkeypatch.setattr(mp, "collect_opportunities", lambda *a, **k: [])
    snap = mp.get_market_snapshot("Staff Nurse")
    assert calls == [] and snap["domain_pack"]["id"] == "healthcare"
    assert not any(w in json.dumps(snap["project_patterns"]).lower() for w in TECH_WORDS)
    mp.get_market_snapshot("Backend Developer")
    assert "github" in calls


# ── 5. Opportunities: coding contests only for tech ─────────────────────────

def test_opportunity_adapters_filtered_by_field():
    def relevant(role):
        fid = resolve_field({"target_role": role})["id"]
        return {a.source for a in oa.get_opportunity_adapters() if a.fields is None or fid in a.fields}

    nurse = relevant("Staff Nurse")
    assert not {"LeetCode", "Codeforces", "Kaggle", "Hackathon"} & nurse
    assert "FieldSearch" in nurse
    assert {"LeetCode", "Codeforces"} <= relevant("Backend Developer")


def test_field_adapter_always_gives_browse_links():
    events = oa.FieldOpportunityAdapter().fetch([], "Chartered Accountant", 30)
    urls = [e["url"] for e in events]
    assert any("linkedin.com/jobs" in u for u in urls) and any("unstop.com/competitions" in u for u in urls)


# ── 6. Testing suite: interview + readiness adapt to the field ──────────────

def test_case_interview_uses_field_format(monkeypatch):
    monkeypatch.setattr(iai, "load_profile", lambda *a, **k: {"target_role": "Staff Nurse"})
    monkeypatch.setattr(iai, "profile_as_compact_context", lambda *a, **k: "")
    settings = iai.normalize_settings("case", None, "entry", 3, "u-nurse")
    assert settings["field"] == "healthcare"
    block = iai._role_prompt_block("u-nurse", settings)
    assert "clinical scenario" in block.lower() and "coding" not in block.lower()
    tech = iai.normalize_settings("technical", "Backend Developer", "entry", 3, "u-dev")
    assert "coding" in iai._role_prompt_block("u-dev", tech).lower()


def test_readiness_ignores_coding_for_non_tech():
    db = SessionLocal()
    db.add(User(id="nurse-r", name="N", profile_data=json.dumps({"target_role": "Staff Nurse"})))
    db.add(SandboxSession(id="t-r", user_id="nurse-r", type="theory", title="T", status="completed", score=80))
    db.add(SandboxSession(id="i-r", user_id="nurse-r", type="interview", title="I", status="completed", score=70))
    db.commit()
    rep = compute_readiness(db, "nurse-r")
    assert rep["applicable_types"] == ["theory", "interview"] and rep["coverage"] == 2 and rep["coverage_total"] == 2
    assert rep["readiness"] == round(0.55 * 80 + 0.45 * 70)
    assert not any("coding" in s["title"].lower() for s in rep["next_steps"])
    db.close()
