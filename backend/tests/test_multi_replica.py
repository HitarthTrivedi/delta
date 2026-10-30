"""Ready for more than one API replica: a lock only one server can hold
(Postgres advisory lock), the reminder sweep runs on one server at a time,
and rate limits can live in a shared store without ever failing requests.

    .venv/Scripts/python -m pytest tests/test_multi_replica.py -q
"""
import os
import sys
import tempfile
import threading
import time

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "multi_replica_test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_DB}"
os.environ["CACHE_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine  # noqa: E402
import app.main  # noqa: E402,F401 — registers every model
from app.limiter import limiter as app_limiter  # noqa: E402
from app.services import reminder_service  # noqa: E402
from app.services.cluster_lock import cluster_lock  # noqa: E402

Base.metadata.create_all(bind=engine)
POSTGRES = engine.dialect.name == "postgresql"
needs_postgres = pytest.mark.skipif(not POSTGRES, reason="advisory locks need Postgres")


@needs_postgres
def test_only_one_holder_and_release():
    with cluster_lock("test-a") as first:
        assert first is True
        with cluster_lock("test-a") as second:
            assert second is False  # another connection already holds it
        with cluster_lock("test-b") as other:
            assert other is True  # different names don't block each other
    with cluster_lock("test-a") as again:
        assert again is True  # released on exit


@needs_postgres
def test_wait_blocks_until_released():
    order = []
    holding, done = threading.Event(), threading.Event()

    def holder():
        with cluster_lock("test-wait"):
            holding.set()
            time.sleep(0.5)
            order.append("holder released")

    def waiter():
        holding.wait()
        with cluster_lock("test-wait", wait=True) as got:
            order.append(f"waiter got {got}")
        done.set()
    threads = [threading.Thread(target=holder), threading.Thread(target=waiter)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert done.is_set() and order == ["holder released", "waiter got True"]


def test_sqlite_has_one_process_so_the_lock_is_always_granted():
    if POSTGRES:
        pytest.skip("SQLite behaviour")
    with cluster_lock("anything") as a, cluster_lock("anything") as b:
        assert a is True and b is True


@needs_postgres
def test_reminder_sweep_runs_on_one_server_at_a_time(monkeypatch):
    monkeypatch.setattr(settings, "REMINDERS_ENABLED", True)
    with cluster_lock("reminder-sweep"):  # another replica is sweeping
        assert reminder_service.run_daily_reminders() == {"sent": 0, "skipped": 0, "failed": 0, "locked": True}
    result = reminder_service.run_daily_reminders()
    assert "locked" not in result


def _tiny_app(storage_uri):
    lim = Limiter(key_func=lambda request: "same-caller", storage_uri=storage_uri, key_prefix="delta-rl-test",
                  in_memory_fallback_enabled=True, swallow_errors=True)
    tiny = FastAPI()
    tiny.state.limiter = lim
    tiny.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @tiny.get("/ping")
    @lim.limit("2/minute")
    def ping(request: Request):
        return {"ok": True}
    return TestClient(tiny)


def test_shared_store_counts_and_a_dead_store_never_fails_requests():
    client = _tiny_app("memory://")
    assert [client.get("/ping").status_code for _ in range(3)] == [200, 200, 429]
    dead = _tiny_app("redis://127.0.0.1:1")  # nothing listens there
    assert dead.get("/ping").status_code == 200  # falls back to in-process limits, no 500


def test_app_limiter_is_configured_for_a_shared_store():
    assert app_limiter._key_prefix == "delta-rl"
    assert app_limiter._in_memory_fallback_enabled is True and app_limiter._swallow_errors is True
