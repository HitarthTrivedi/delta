"""
limiter.py — Shared slowapi rate limiter instance.

Defined here (not in main.py) to avoid circular imports when routers
import the limiter directly.
"""
import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def _client_key(request):
    """Who to count a request against.

    Signed-in callers are keyed by the user id in their token. Every expensive
    (AI) route requires a valid token, so a caller can't reset their limit by
    changing headers: a forged token's id is rejected by auth anyway. The token
    is only read here, not verified; verification happens in the route's auth
    dependency. Anonymous callers fall back to the client IP (first
    X-Forwarded-For entry behind Railway's proxy, else the peer address).
    """
    auth = request.headers.get("authorization") or ""
    if auth.startswith("Bearer "):
        try:
            sub = jwt.decode(auth[7:], options={"verify_signature": False}).get("sub")
            if sub:
                return f"user:{sub}"
        except jwt.PyJWTError:
            pass
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


# default_limits apply to every route (a global safety net against abuse / quota
# burn on the AI endpoints); routes may add tighter per-endpoint limits.
# With RATE_LIMIT_STORAGE_URI set (Redis), every API replica shares the same
# counters. If that store is unreachable, limits fall back to this process's
# memory instead of failing requests: rate limiting must never take the API down.
limiter = Limiter(
    key_func=_client_key,
    default_limits=["100/minute"],
    storage_uri=settings.RATE_LIMIT_STORAGE_URI or None,
    key_prefix="delta-rl",
    in_memory_fallback_enabled=True,
    swallow_errors=True,
)
