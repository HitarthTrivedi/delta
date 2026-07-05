"""
limiter.py — Shared slowapi rate limiter instance.

Defined here (not in main.py) to avoid circular imports when routers
import the limiter directly.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_key(request):
    """Real client IP. Behind Railway's proxy the direct peer is the proxy, so the
    true client is the first entry of X-Forwarded-For; fall back to the peer addr."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


# default_limits apply to every route (a global safety net against abuse / quota
# burn on the AI endpoints); routes may add tighter per-endpoint limits.
limiter = Limiter(key_func=_client_key, default_limits=["100/minute"])
