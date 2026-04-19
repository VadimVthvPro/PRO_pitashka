"""Tests for ``ai_service._classify_error`` and the Gemini retry predicate."""

from __future__ import annotations

import asyncio

import pytest

from app.services.ai_service import (
    AIConfigError,
    AIQuotaError,
    AITimeoutError,
    AIUpstreamError,
    _ai_retry_predicate,
    _classify_error,
)


class _FakeStatusError(Exception):
    def __init__(self, status_code: int, message: str = "boom"):
        super().__init__(message)
        self.status_code = status_code


def test_classify_quota_error_to_AIQuotaError():
    e = _classify_error(_FakeStatusError(429, "rate limit exceeded"))
    assert isinstance(e, AIQuotaError)


def test_classify_resource_exhausted_to_AIQuotaError():
    e = _classify_error(Exception("RESOURCE_EXHAUSTED quota for project"))
    assert isinstance(e, AIQuotaError)


def test_classify_invalid_key_to_AIConfigError():
    e = _classify_error(Exception("API key not valid (401 Unauthorized)"))
    assert isinstance(e, AIConfigError)


def test_classify_timeout_to_AITimeoutError():
    e = _classify_error(asyncio.TimeoutError())
    assert isinstance(e, AITimeoutError)
    assert e.retryable is True


def test_classify_503_to_retryable_upstream():
    e = _classify_error(_FakeStatusError(503, "Service Unavailable"))
    assert isinstance(e, AIUpstreamError)
    assert e.retryable is True


def test_classify_unknown_to_non_retryable_upstream():
    e = _classify_error(Exception("some weird parser failure"))
    assert isinstance(e, AIUpstreamError)
    assert e.retryable is False


@pytest.mark.parametrize(
    "exc, should_retry",
    [
        (AIConfigError("bad key"), False),
        (AIQuotaError("daily quota gone"), False),
        (AITimeoutError(), True),
        (AIUpstreamError("503", retryable=True), True),
        (AIUpstreamError("weird", retryable=False), False),
        (_FakeStatusError(503, "down"), True),
        (_FakeStatusError(401, "auth"), False),
    ],
)
def test_predicate_respects_typed_errors(exc, should_retry):
    assert _ai_retry_predicate(exc) is should_retry
