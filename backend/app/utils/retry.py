"""Async retry helper with exponential backoff, jitter and selective retry.

Designed first and foremost for Gemini calls, which intermittently return
``503 UNAVAILABLE`` / ``504 DEADLINE_EXCEEDED`` / connection resets that are
recoverable on the next attempt. Permanent errors (invalid API key, malformed
request, quota exhausted) must NOT be retried — that only burns the user's
quota and slows down the response.

Usage::

    @async_retry(attempts=5, base_delay=1.0, max_delay=20.0, jitter=0.25)
    async def call_gemini(...): ...

The decorator accepts an optional ``retry_on`` predicate. By default it relies
on :func:`is_retryable_exception` which understands the Google Gen AI SDK
error shapes (``ServerError``, ``ResourceExhausted``, ``DeadlineExceeded``,
``ServiceUnavailable``) plus generic transport failures (timeouts, ``OSError``,
common ``aiohttp``/``httpx`` connection errors).
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from typing import Any, Awaitable, Callable, Iterable

logger = logging.getLogger(__name__)


# Status codes that almost always mean "try again later".
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504, 522, 524}

# Substrings (lower-cased) that hint at a transient upstream problem.
_RETRYABLE_HINTS = (
    "503",
    "502",
    "504",
    "500",
    "unavailable",
    "deadline",
    "timeout",
    "timed out",
    "temporarily",
    "retry",
    "overloaded",
    "connection reset",
    "connection aborted",
    "broken pipe",
    "eof occurred",
    "ssl",
    "remote end closed",
)

# Substrings that are *definitely* not retryable — config / programming errors.
_NON_RETRYABLE_HINTS = (
    "api key",
    "permission",
    "unauthorized",
    "401",
    "403",
    "invalid argument",
    "invalid_argument",
    "400",
    "not found",
    "404",
    "safety",
    "blocked",
)


def _status_code(exc: BaseException) -> int | None:
    """Best-effort extraction of an HTTP / gRPC code from various SDKs."""
    for attr in ("status_code", "code", "status"):
        v = getattr(exc, attr, None)
        if isinstance(v, int):
            return v
        if hasattr(v, "value") and isinstance(v.value, int):
            return v.value
    resp = getattr(exc, "response", None)
    if resp is not None:
        sc = getattr(resp, "status_code", None)
        if isinstance(sc, int):
            return sc
    return None


def is_retryable_exception(exc: BaseException) -> bool:
    """Heuristic — should we retry after this exception?

    The check looks at: the exception class name, status code (if exposed),
    and the message text. Errs on the side of caution: anything obviously
    permanent (auth, quota exhausted, validation) is *not* retried.
    """
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()

    if isinstance(exc, asyncio.TimeoutError):
        return True
    if isinstance(exc, ConnectionError):
        return True
    if isinstance(exc, asyncio.CancelledError):
        return False

    if any(h in msg for h in _NON_RETRYABLE_HINTS):
        if "quota" in msg or "rate limit" in msg or "resource_exhausted" in msg or "429" in msg:
            return True
        return False

    sc = _status_code(exc)
    if sc is not None and sc in _RETRYABLE_STATUS:
        return True
    if sc is not None and 400 <= sc < 500 and sc not in _RETRYABLE_STATUS:
        return False

    if any(h in msg for h in _RETRYABLE_HINTS):
        return True

    if any(s in name for s in (
        "serverunavailable",
        "serviceunavailable",
        "deadlineexceeded",
        "servererror",
        "internalservererror",
        "unavailable",
        "timeout",
    )):
        return True

    return False


def _compute_delay(
    attempt: int,
    base_delay: float,
    factor: float,
    max_delay: float,
    jitter: float,
) -> float:
    """Exponential backoff with optional symmetric jitter (fraction of delay).

    ``attempt`` is 1-based. Jitter of e.g. 0.25 means actual delay lands in
    ``[delay * 0.75, delay * 1.25]`` to avoid thundering-herd.
    """
    raw = base_delay * (factor ** (attempt - 1))
    capped = min(raw, max_delay)
    if jitter > 0:
        spread = capped * jitter
        capped = max(0.0, capped + random.uniform(-spread, spread))
    return capped


def async_retry(
    attempts: int = 5,
    *,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
    factor: float = 2.0,
    jitter: float = 0.25,
    total_budget: float | None = 45.0,
    retry_on: Callable[[BaseException], bool] | None = None,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
    delay: float | None = None,
    backoff: float | None = None,
):
    """Decorator that retries an async callable with exponential backoff.

    Arguments:
        attempts: maximum number of attempts (>= 1).
        base_delay: delay before the second attempt, in seconds.
        max_delay: hard cap on the delay between any two attempts.
        factor: exponential factor (delay = base_delay * factor**(n-1)).
        jitter: fraction of the delay added/subtracted as jitter (0..1).
        total_budget: if set, abort retrying once the total elapsed time
            exceeds this many seconds.
        retry_on: optional predicate (defaults to :func:`is_retryable_exception`).
        on_retry: optional callback ``(attempt, exception, sleep_seconds)``.
        delay / backoff: legacy aliases for backwards compatibility.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    if delay is not None:
        base_delay = delay
    if backoff is not None:
        factor = backoff
    predicate = retry_on or is_retryable_exception

    def decorator(func: Callable[..., Awaitable[Any]]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            started = time.monotonic()
            last_exc: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt == attempts:
                        logger.error(
                            "%s: giving up after %d attempt(s): %s",
                            func.__name__, attempt, exc,
                        )
                        raise
                    if not predicate(exc):
                        logger.info(
                            "%s: non-retryable error on attempt %d: %s",
                            func.__name__, attempt, exc,
                        )
                        raise
                    sleep_for = _compute_delay(attempt, base_delay, factor, max_delay, jitter)
                    if total_budget is not None:
                        elapsed = time.monotonic() - started
                        remaining = total_budget - elapsed
                        if remaining <= 0:
                            logger.warning(
                                "%s: retry budget exhausted after %d attempt(s) (%.1fs)",
                                func.__name__, attempt, elapsed,
                            )
                            raise
                        sleep_for = min(sleep_for, remaining)
                    logger.warning(
                        "%s: attempt %d/%d failed (%s: %s) — retrying in %.2fs",
                        func.__name__, attempt, attempts,
                        exc.__class__.__name__, exc, sleep_for,
                    )
                    if on_retry is not None:
                        try:
                            on_retry(attempt, exc, sleep_for)
                        except Exception:
                            logger.debug("on_retry callback raised", exc_info=True)
                    await asyncio.sleep(sleep_for)
            assert last_exc is not None
            raise last_exc
        return wrapper
    return decorator


__all__: Iterable[str] = (
    "async_retry",
    "is_retryable_exception",
)
