"""Tiny concurrency helper for fanning out independent blocking calls.

The codebase is synchronous (``requests`` + sync SDKs). Rather than rewrite to
async, we run independent network calls concurrently on a thread pool. Each
underlying call already carries its own request timeout, so a generous global
timeout here is just a safety net — failures/timeouts fall back to ``default``
per task and never propagate, matching the existing "return [] on error" style.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as _FuturesTimeout
from typing import Any, Callable

logger = logging.getLogger("delta.parallel")


def run_parallel(
    tasks: dict[str, Callable[[], Any]],
    timeout: float = 20.0,
    default: Any = None,
) -> dict[str, Any]:
    """Run ``{key: zero-arg callable}`` concurrently and return ``{key: result}``.

    A task that raises or does not finish within ``timeout`` yields ``default``
    for its key. Result ordering is irrelevant — callers key by name.
    """
    results: dict[str, Any] = {key: default for key in tasks}
    if not tasks:
        return results

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_key = {executor.submit(fn): key for key, fn in tasks.items()}
        try:
            for future in as_completed(future_to_key, timeout=timeout):
                key = future_to_key[future]
                try:
                    results[key] = future.result()
                except Exception as exc:  # noqa: BLE001 — mirror existing fail-soft behavior
                    logger.warning("parallel task '%s' failed: %s", key, exc)
        except _FuturesTimeout:
            unfinished = [future_to_key[f] for f in future_to_key if not f.done()]
            logger.warning("parallel tasks timed out (kept defaults): %s", unfinished)

    return results
