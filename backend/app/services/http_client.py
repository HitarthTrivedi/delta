"""Shared HTTP session for outbound calls to public/live data sources.

All market-pulse / opportunity / search providers previously used bare
``requests.get/post``, which opens a fresh TCP+TLS connection every time and
never retries. A single shared ``Session`` with a connection pool reuses
connections (meaningful now that these calls fan out in parallel) and adds a
light retry so a transient blip doesn't silently return empty data.

Usage::

    from app.services.http_client import get_session
    resp = get_session().get(url, params=..., timeout=10)
"""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Return a process-wide pooled session with light retries."""
    global _session
    if _session is None:
        session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "POST"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _session = session
    return _session
