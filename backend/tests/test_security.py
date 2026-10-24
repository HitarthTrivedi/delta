"""Auth hardening checks: endpoints that used to be open, or trusted a forgeable
header, must now require a verified Supabase JWT in production mode.

    .venv/Scripts/python -m pytest tests/test_security.py -q

Throwaway SQLite DB; header auth is switched OFF per test to mimic production.
"""
import datetime
import os
import sys
import tempfile

import jwt
import pytest

_DB = os.path.join(tempfile.mkdtemp(), "security_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.dependencies.auth import GUEST_ID  # noqa: E402
from app.limiter import _client_key  # noqa: E402
from app.main import app  # noqa: E402
from app.models import SkillNode, User  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

SECRET = "test-jwt-secret-for-security-tests-only"
PROJECT = "https://example-project.supabase.co"


@pytest.fixture(autouse=True)
def production_auth(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_HEADER_AUTH", False)
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setattr(settings, "SUPABASE_URL", PROJECT)


def _token(sub, aud="authenticated", iss=PROJECT + "/auth/v1", email=None):
    claims = {"sub": sub, "aud": aud, "iss": iss,
              "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)}
    if email:
        claims["email"] = email
    return {"Authorization": "Bearer " + jwt.encode(claims, SECRET, algorithm="HS256")}


def _user_with_skill(uid):
    db = SessionLocal()
    if not db.get(User, uid):
        db.add(User(id=uid, name=uid))
    skill = SkillNode(id=f"skill-{uid}", user_id=uid, name="SQL")
    db.merge(skill)
    db.commit()
    db.close()
    return f"skill-{uid}"


FINALIZE = {"user_id": "victim", "raw_input": "x", "adaptive_questions": [], "answers": []}


def test_onboarding_finalize_requires_auth():
    assert client.post("/api/chat/onboarding/finalize", json=FINALIZE).status_code == 401


def test_onboarding_finalize_rejects_other_users_token():
    r = client.post("/api/chat/onboarding/finalize", json=FINALIZE, headers=_token("attacker"))
    assert r.status_code == 403


def test_onboarding_start_requires_auth():
    r = client.post("/api/chat/onboarding/start", json={"raw_input": "hi", "target_role": "x"})
    assert r.status_code == 401


def test_skill_update_ignores_forged_user_header():
    skill_id = _user_with_skill("owner1")
    r = client.put(f"/api/skills/{skill_id}", json={"proficiency": 5}, headers={"X-User-Id": "owner1"})
    assert r.status_code == 401


def test_skill_update_rejects_other_users_token():
    skill_id = _user_with_skill("owner2")
    r = client.put(f"/api/skills/{skill_id}", json={"proficiency": 5}, headers=_token("attacker"))
    assert r.status_code == 403


def test_skill_update_allows_owner_token():
    skill_id = _user_with_skill("owner3")
    r = client.put(f"/api/skills/{skill_id}", json={"proficiency": 5}, headers=_token("owner3"))
    assert r.status_code == 200, r.text
    assert r.json()["proficiency"] == 5


def test_jwt_with_wrong_audience_or_issuer_is_rejected():
    _user_with_skill("owner4")
    for bad in (_token("owner4", aud="anon-key-audience"), _token("owner4", iss="https://other.supabase.co/auth/v1")):
        assert client.put("/api/skills/skill-owner4", json={"proficiency": 2}, headers=bad).status_code == 401


def test_system_status_is_admin_only(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "admin@delta.test")
    assert client.get("/api/career-os/system-status").status_code == 401
    assert client.get("/api/career-os/system-status", headers=_token("u1", email="someone@x.test")).status_code == 403
    assert client.get("/api/career-os/system-status", headers=_token("u2", email="admin@delta.test")).status_code == 200


def test_guest_id_needs_auth_in_production():
    assert client.get(f"/api/career-os/user/{GUEST_ID}/context-docs").status_code == 401


def test_legacy_resume_upload_is_gone():
    r = client.post("/api/resume/upload", files={"file": ("cv.pdf", b"%PDF", "application/pdf")})
    assert r.status_code in (404, 405)


def test_rate_limit_key_follows_token_not_forwarded_header():
    class Req:
        def __init__(self, headers):
            self.headers = headers
            self.client = None

    token = _token("u9")["Authorization"]
    a = _client_key(Req({"authorization": token, "x-forwarded-for": "1.1.1.1"}))
    b = _client_key(Req({"authorization": token, "x-forwarded-for": "2.2.2.2"}))
    assert a == b == "user:u9"
