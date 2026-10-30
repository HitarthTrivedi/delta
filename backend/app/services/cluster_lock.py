"""'Only one server does this': a lock shared by every API replica.

On Postgres it is an advisory lock held on its own connection, so it isn't
tied to any request's transaction, and it is freed automatically if the
process dies (the connection closes). On SQLite (local development and tests)
there is only ever one process, so the lock is always granted.
"""
from __future__ import annotations

import contextlib
import hashlib

from sqlalchemy import text


def _key(name: str) -> int:
    """A stable signed 64-bit key for the lock name (same on every server)."""
    return int.from_bytes(hashlib.sha256(f"delta:{name}".encode()).digest()[:8], "big", signed=True)


@contextlib.contextmanager
def cluster_lock(name: str, wait: bool = False):
    """Yield True if this process holds the lock named `name`. With wait=True,
    block until it is free; otherwise give up at once (yield False)."""
    from app.database import engine
    if engine.dialect.name != "postgresql":
        yield True
        return
    conn = engine.connect()
    try:
        key = _key(name)
        if wait:
            conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": key})
            got = True
        else:
            got = bool(conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar())
        conn.commit()
        try:
            yield got
        finally:
            if got:
                conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
                conn.commit()
    finally:
        conn.close()
