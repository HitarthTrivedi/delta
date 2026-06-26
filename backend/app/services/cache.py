"""Shared cache with graceful in-process fallback.

Caches deterministic / idempotent work only (web search, market data,
embeddings, low-temp intent classification) — never personalized generative
output. Backed by Redis when reachable; otherwise a per-process TTL cache.

The layer NEVER raises to callers: any cache error behaves like a miss, so the
app runs identically whether or not Redis is available (important — Redis has
no native Windows build; locally this transparently uses the in-process cache).
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
from typing import Any, Callable

from cachetools import TTLCache

from app.config import settings

logger = logging.getLogger("delta.cache")

# ── Redis connection (probed once, lazily) ──────────────────────────────────
_redis = None
_redis_checked = False
_redis_ok = False

# ── In-process fallback: one bounded TTL cache per namespace ────────────────
_fallback_caches: dict[str, TTLCache] = {}


def _get_redis():
    """Return a live Redis client, or None if unavailable. Probed once."""
    global _redis, _redis_checked, _redis_ok
    if _redis_checked:
        return _redis if _redis_ok else None
    _redis_checked = True
    if not settings.CACHE_ENABLED:
        logger.info("cache: disabled via CACHE_ENABLED — using in-process fallback")
        return None
    try:
        import redis as redis_lib

        client = redis_lib.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            decode_responses=True,
        )
        client.ping()
        _redis = client
        _redis_ok = True
        logger.info("cache: connected to Redis at %s", settings.REDIS_URL)
    except Exception as exc:  # noqa: BLE001
        _redis_ok = False
        logger.warning("cache: Redis unavailable (%s) — using in-process TTL fallback", exc)
    return _redis if _redis_ok else None


def _full_key(namespace: str, key: str) -> str:
    digest = hashlib.sha1(str(key).encode("utf-8")).hexdigest()  # noqa: S324
    return f"delta:{namespace}:{digest}"


def _fallback_cache(namespace: str, ttl: float) -> TTLCache:
    cache = _fallback_caches.get(namespace)
    if cache is None:
        cache = TTLCache(maxsize=2048, ttl=ttl)
        _fallback_caches[namespace] = cache
    return cache


def cache_get(namespace: str, key: str) -> Any | None:
    """Return the cached value, or None on miss/error."""
    full = _full_key(namespace, key)
    client = _get_redis()
    if client is not None:
        try:
            raw = client.get(full)
            return json.loads(raw) if raw is not None else None
        except Exception as exc:  # noqa: BLE001 — fail open to fallback
            logger.warning("cache get failed (%s) — trying in-process", exc)
    cache = _fallback_caches.get(namespace)
    return cache.get(full) if cache is not None else None


def cache_set(namespace: str, key: str, value: Any, ttl: float) -> None:
    """Store a value under (namespace, key) with a TTL in seconds. Never raises."""
    full = _full_key(namespace, key)
    client = _get_redis()
    if client is not None:
        try:
            client.setex(full, int(ttl), json.dumps(value))
            return
        except Exception as exc:  # noqa: BLE001 — fall through to in-process
            logger.warning("cache set failed (%s) — using in-process", exc)
    _fallback_cache(namespace, ttl)[full] = value


def _default_key(args: tuple, kwargs: dict) -> str:
    return repr(args) + "|" + repr(sorted(kwargs.items()))


def cached(namespace: str, ttl: float, key_fn: Callable[..., str] | None = None):
    """Cache a function's return value. Only caches truthy, non-None results.

    ``key_fn`` builds the cache key from the call args; defaults to repr(args).
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                key = key_fn(*args, **kwargs) if key_fn else _default_key(args, kwargs)
            except Exception:  # noqa: BLE001 — bad key fn must not break the call
                return fn(*args, **kwargs)
            hit = cache_get(namespace, key)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            if result:  # don't cache empty/falsy results (treated as transient miss)
                cache_set(namespace, key, result, ttl)
            return result
        return wrapper
    return decorator
