"""Tests for ``app.utils.retry`` — Gemini-friendly async retry decorator."""

from __future__ import annotations

import asyncio
import time

import pytest

from app.utils.retry import async_retry, is_retryable_exception


pytestmark = pytest.mark.asyncio


class _FakeStatusError(Exception):
    """Helper exception mimicking SDKs that expose a ``status_code`` attribute."""

    def __init__(self, status_code: int, message: str = "boom"):
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# is_retryable_exception
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "exc",
    [
        _FakeStatusError(503, "503 Service Unavailable"),
        _FakeStatusError(504, "deadline exceeded"),
        _FakeStatusError(500, "internal server error"),
        _FakeStatusError(429, "rate limit"),
        TimeoutError("timed out"),
        ConnectionError("connection reset"),
        Exception("Gemini overloaded — please retry"),
    ],
)
async def test_retryable_exceptions_are_recognised(exc):
    assert is_retryable_exception(exc) is True


@pytest.mark.parametrize(
    "exc",
    [
        _FakeStatusError(401, "unauthorized"),
        _FakeStatusError(403, "permission denied"),
        _FakeStatusError(400, "invalid argument"),
        _FakeStatusError(404, "not found"),
        Exception("API key not valid. Please pass a valid API key."),
        Exception("safety_blocked: response blocked"),
    ],
)
async def test_non_retryable_exceptions_are_recognised(exc):
    assert is_retryable_exception(exc) is False


async def test_cancelled_error_is_not_retried():
    assert is_retryable_exception(asyncio.CancelledError()) is False


# ---------------------------------------------------------------------------
# async_retry behaviour
# ---------------------------------------------------------------------------

async def test_returns_value_when_function_succeeds_first_try():
    calls = 0

    @async_retry(attempts=3, base_delay=0.01)
    async def ok():
        nonlocal calls
        calls += 1
        return "yes"

    assert await ok() == "yes"
    assert calls == 1


async def test_retries_on_transient_then_succeeds():
    calls = 0

    @async_retry(attempts=4, base_delay=0.01, max_delay=0.05, jitter=0)
    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise _FakeStatusError(503, "service unavailable")
        return "ok"

    assert await flaky() == "ok"
    assert calls == 3


async def test_does_not_retry_non_retryable_error():
    calls = 0

    @async_retry(attempts=5, base_delay=0.01)
    async def bad_key():
        nonlocal calls
        calls += 1
        raise _FakeStatusError(401, "unauthorized")

    with pytest.raises(_FakeStatusError):
        await bad_key()
    assert calls == 1, "non-retryable errors must short-circuit"


async def test_gives_up_after_max_attempts():
    calls = 0

    @async_retry(attempts=3, base_delay=0.01, max_delay=0.02, jitter=0)
    async def always_503():
        nonlocal calls
        calls += 1
        raise _FakeStatusError(503, "still down")

    with pytest.raises(_FakeStatusError):
        await always_503()
    assert calls == 3


async def test_total_budget_aborts_long_retry_chain():
    calls = 0

    @async_retry(
        attempts=10,
        base_delay=0.05,
        max_delay=0.05,
        jitter=0,
        total_budget=0.12,
    )
    async def always_503():
        nonlocal calls
        calls += 1
        raise _FakeStatusError(503, "down")

    started = time.monotonic()
    with pytest.raises(_FakeStatusError):
        await always_503()
    elapsed = time.monotonic() - started

    assert calls < 10, "budget should cut the chain short"
    assert elapsed < 0.5, f"too slow: {elapsed:.2f}s"


async def test_custom_retry_predicate_overrides_default():
    calls = 0
    seen = []

    def only_value_errors(exc):
        seen.append(type(exc).__name__)
        return isinstance(exc, ValueError)

    @async_retry(
        attempts=3,
        base_delay=0.01,
        jitter=0,
        retry_on=only_value_errors,
    )
    async def picky():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("retry please")
        raise _FakeStatusError(503, "should NOT be retried under this predicate")

    with pytest.raises(_FakeStatusError):
        await picky()
    assert calls == 2
    assert "ValueError" in seen


async def test_on_retry_callback_is_invoked():
    events: list[tuple[int, str, float]] = []

    def collect(attempt, exc, delay):
        events.append((attempt, type(exc).__name__, delay))

    @async_retry(
        attempts=3,
        base_delay=0.01,
        max_delay=0.02,
        jitter=0,
        on_retry=collect,
    )
    async def flaky():
        raise _FakeStatusError(503, "down")

    with pytest.raises(_FakeStatusError):
        await flaky()
    assert len(events) == 2  # called for the first two failures, not the final
    assert all(name == "_FakeStatusError" for _, name, _ in events)


async def test_legacy_aliases_delay_backoff_still_work():
    calls = 0

    @async_retry(attempts=3, delay=0.01, backoff=2.0, jitter=0, max_delay=0.05)
    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise _FakeStatusError(503, "transient")
        return "done"

    assert await flaky() == "done"
    assert calls == 2
