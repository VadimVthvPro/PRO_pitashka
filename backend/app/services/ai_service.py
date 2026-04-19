"""AI service: thin wrapper around google-generativeai with safe error handling.

The Gemini Python SDK uses simple API keys (not OAuth tokens). A valid Gemini
API key looks like ``AIzaSy...`` (39 chars). Anything else (in particular
``AQ.<...>`` strings, which are short-lived OAuth access tokens) will be rejected
by the API with 401/403 — and the user will see "AI quota exceeded" or similar
opaque errors.

To make misconfiguration loud and obvious we:

* Validate the key shape in :func:`_get_model` and raise a typed error.
* Re-create the model whenever the underlying setting changes (so a key swap
  in ``.env`` is picked up after backend reload without needing a code change).
* Convert SDK errors into a small set of clear application-level errors so the
  routers can return clean HTTP responses.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
from typing import Any

import google.generativeai as genai

from app.config import get_settings
from app.utils.retry import async_retry, is_retryable_exception

logger = logging.getLogger(__name__)


class AIConfigError(RuntimeError):
    """Raised when the API key is missing or has an obviously wrong shape."""


class AIQuotaError(RuntimeError):
    """Raised when the upstream provider returns a quota / rate limit error."""


class AIUpstreamError(RuntimeError):
    """Raised on any other upstream failure we cannot recover from.

    The ``retryable`` attribute hints to callers whether this is a transient
    failure (503/504/timeout) that may resolve on its own or a permanent issue.
    """

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class AITimeoutError(AIUpstreamError):
    """The upstream call exceeded the per-attempt timeout budget."""

    def __init__(self, message: str = "Gemini call timed out"):
        super().__init__(message, retryable=True)


# Per-call timeout (seconds) — keeps a single hung Gemini request from
# blocking the whole retry budget. Backed by ``asyncio.wait_for``.
_PER_CALL_TIMEOUT = 25.0


def _ai_retry_predicate(exc: BaseException) -> bool:
    """Decide whether to retry a Gemini call.

    Hard rules:
      * ``AIConfigError`` is always permanent.
      * ``AIQuotaError`` is permanent — retrying just burns the daily quota.
      * ``AITimeoutError`` and any ``AIUpstreamError(retryable=True)`` are
        retried.
    Otherwise we fall back to the generic heuristic.
    """
    if isinstance(exc, (AIConfigError, AIQuotaError)):
        return False
    if isinstance(exc, AITimeoutError):
        return True
    if isinstance(exc, AIUpstreamError):
        return exc.retryable
    return is_retryable_exception(exc)


# Default retry policy for Gemini-backed coroutines:
#   5 attempts, exponential 1s -> 2s -> 4s -> 8s -> 16s with ±25% jitter,
#   capped at 20s between attempts and 60s total wall-clock.
_GEMINI_RETRY = dict(
    attempts=5,
    base_delay=1.0,
    max_delay=20.0,
    factor=2.0,
    jitter=0.25,
    total_budget=60.0,
    retry_on=_ai_retry_predicate,
)


_VALID_KEY_PREFIXES = ("AIza",)
_KNOWN_BAD_PREFIXES = {
    "AQ.": (
        "Provided value looks like a Google Cloud OAuth access token, not a "
        "Gemini API key. Create a key at https://aistudio.google.com/app/apikey "
        "(it should start with 'AIzaSy...')."
    ),
    "ya29.": (
        "Provided value is an OAuth2 token, not a Gemini API key. Create a key "
        "at https://aistudio.google.com/app/apikey."
    ),
    "sk-": (
        "Provided value looks like an OpenAI key, not a Gemini key. Create a "
        "Gemini key at https://aistudio.google.com/app/apikey."
    ),
}


_model: genai.GenerativeModel | None = None
_configured_key: str | None = None


def _validate_key(key: str) -> None:
    if not key or not key.strip():
        raise AIConfigError(
            "GEMINI_API_KEY is empty. Set it in .env "
            "(get one at https://aistudio.google.com/app/apikey)."
        )
    for bad, hint in _KNOWN_BAD_PREFIXES.items():
        if key.startswith(bad):
            raise AIConfigError(hint)
    if not any(key.startswith(p) for p in _VALID_KEY_PREFIXES):
        # Don't hard-fail — Google may add new prefixes — but warn loudly.
        logger.warning(
            "GEMINI_API_KEY does not start with the expected 'AIza' prefix "
            "(got %r...). Continuing, but expect 401/403 if this is wrong.",
            key[:6],
        )


_configured_model_name: str | None = None


def _get_model() -> genai.GenerativeModel:
    """Return a singleton model, re-initialising it if the key or model changed."""
    global _model, _configured_key, _configured_model_name
    settings = get_settings()
    key = settings.GEMINI_API_KEY
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
    if _model is None or _configured_key != key or _configured_model_name != model_name:
        _validate_key(key)
        genai.configure(api_key=key)
        _model = genai.GenerativeModel(model_name)
        _configured_key = key
        _configured_model_name = model_name
        logger.info(
            "Gemini model initialised (model=%s, key tail: ...%s)",
            model_name, key[-4:],
        )
    return _model


def _classify_error(exc: BaseException) -> Exception:
    """Map a raw SDK / transport exception onto our typed AI errors.

    The mapping is conservative: anything we recognise as ``quota`` becomes
    a permanent :class:`AIQuotaError`; anything that looks like an auth /
    config problem becomes :class:`AIConfigError`; everything else ends up
    as :class:`AIUpstreamError` with ``retryable`` derived from the generic
    heuristic.
    """
    msg = str(exc).lower()
    if "quota" in msg or "rate limit" in msg or "resource_exhausted" in msg or "429" in msg:
        return AIQuotaError(str(exc))
    if (
        "api key" in msg
        or "permission" in msg
        or "401" in msg
        or "403" in msg
        or "invalid api" in msg
        or "api_key_invalid" in msg
    ):
        return AIConfigError(
            f"Gemini rejected the request — likely an invalid or revoked key. "
            f"Original error: {exc}"
        )
    if isinstance(exc, asyncio.TimeoutError):
        return AITimeoutError()
    return AIUpstreamError(str(exc), retryable=is_retryable_exception(exc))


async def _call_model(coro_factory) -> Any:
    """Invoke a Gemini coroutine with a per-attempt timeout + classification.

    ``coro_factory`` is a zero-arg callable that returns the coroutine to
    await. We wrap it in ``asyncio.wait_for`` so a single hanging request
    cannot eat the entire retry budget, and translate every failure into one
    of our typed errors so the retry decorator can decide what to do.
    """
    try:
        return await asyncio.wait_for(coro_factory(), timeout=_PER_CALL_TIMEOUT)
    except (AIConfigError, AIQuotaError, AIUpstreamError):
        raise
    except asyncio.TimeoutError as exc:
        raise AITimeoutError() from exc
    except Exception as exc:
        raise _classify_error(exc) from exc


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # remove first fence line (``` or ```json) and trailing fence
        first_nl = text.find("\n")
        text = text[first_nl + 1 :] if first_nl != -1 else text
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


async def health_check() -> dict[str, Any]:
    """Light-weight call used by /api/_internal/ai-health to verify config."""
    settings = get_settings()
    key = settings.GEMINI_API_KEY
    info: dict[str, Any] = {
        "key_present": bool(key),
        "key_prefix": (key[:6] + "...") if key else None,
        "key_tail": ("..." + key[-4:]) if key else None,
        "key_looks_valid": bool(key) and any(key.startswith(p) for p in _VALID_KEY_PREFIXES),
        "model": settings.GEMINI_MODEL,
    }
    try:
        _validate_key(key)
    except AIConfigError as e:
        info["status"] = "misconfigured"
        info["error"] = str(e)
        return info

    try:
        model = _get_model()
        response = await asyncio.wait_for(
            model.generate_content_async("Reply with the single word: OK"),
            timeout=12,
        )
        info["status"] = "ok"
        info["sample"] = (response.text or "").strip()[:32]
    except asyncio.TimeoutError:
        info["status"] = "timeout"
    except Exception as e:  # pragma: no cover — diagnostic path
        wrapped = _classify_error(e)
        info["status"] = "error"
        info["error_type"] = type(wrapped).__name__
        info["error"] = str(wrapped)
    return info


@async_retry(**_GEMINI_RETRY)
async def recognize_food_photo(image_bytes: bytes) -> list[dict]:
    model = _get_model()
    prompt = (
        "Analyze this food photo. Return a JSON array of items: "
        '[{"name": "food name", "grams": estimated_grams, "cal": calories, '
        '"b": protein_g, "g": fat_g, "u": carbs_g}]. '
        "Only JSON, no other text."
    )
    import PIL.Image  # local import keeps cold-start light

    image = PIL.Image.open(io.BytesIO(image_bytes))
    response = await _call_model(lambda: model.generate_content_async([prompt, image]))
    return json.loads(_strip_code_fence(response.text))


@async_retry(**_GEMINI_RETRY)
async def analyze_food_text(foods: list[str], grams: list[float], lang: str = "ru") -> list[dict]:
    model = _get_model()
    items = ", ".join(f"{f} {g}g" for f, g in zip(foods, grams))
    prompt = (
        f"Calculate KBJU for these foods: {items}. "
        f'Return JSON array: [{{"name": "...", "grams": N, "cal": N, "b": N, "g": N, "u": N}}]. '
        f"Language: {lang}. Only JSON."
    )
    response = await _call_model(lambda: model.generate_content_async(prompt))
    return json.loads(_strip_code_fence(response.text))


@async_retry(**_GEMINI_RETRY)
async def generate_meal_plan(user_info: dict, lang: str = "ru") -> str:
    model = _get_model()
    prompt = (
        "Create a detailed weekly meal plan (7 days, 3 meals + snacks) for a person with these parameters:\n"
        f"Sex: {user_info.get('sex', 'unknown')}, Weight: {user_info.get('weight')}kg, "
        f"Height: {user_info.get('height')}cm, BMI: {user_info.get('imt')}, "
        f"Goal: {user_info.get('aim')}, Daily calories: {user_info.get('daily_cal')}kcal.\n"
        f"Include KBJU for each meal. Language: {lang}."
    )
    response = await _call_model(lambda: model.generate_content_async(prompt))
    return response.text


@async_retry(**_GEMINI_RETRY)
async def generate_workout_plan(user_info: dict, lang: str = "ru") -> str:
    model = _get_model()
    prompt = (
        "Create a weekly workout plan (7 days) for:\n"
        f"Sex: {user_info.get('sex', 'unknown')}, Weight: {user_info.get('weight')}kg, "
        f"BMI: {user_info.get('imt')}, Goal: {user_info.get('aim')}.\n"
        f"Include exercise names, sets, reps, rest times. Language: {lang}."
    )
    response = await _call_model(lambda: model.generate_content_async(prompt))
    return response.text


@async_retry(**_GEMINI_RETRY)
async def generate_recipe(meal_type: str, user_info: dict, lang: str = "ru") -> str:
    model = _get_model()
    prompt = (
        f"Generate a healthy {meal_type} recipe for a person with daily calorie target "
        f"{user_info.get('daily_cal')}kcal, goal: {user_info.get('aim')}.\n"
        f"Include ingredients, steps, and KBJU. Language: {lang}."
    )
    response = await _call_model(lambda: model.generate_content_async(prompt))
    return response.text


@async_retry(**_GEMINI_RETRY)
async def weekly_digest(stats: dict, lang: str = "ru") -> dict:
    """Return a structured weekly digest. Caller is responsible for fallback."""
    model = _get_model()
    prompt = (
        "You are a friendly nutrition & fitness coach. Look at the user's "
        "weekly stats (JSON below) and produce a personal digest. "
        "Reply ONLY in raw JSON (no markdown fences) with keys: "
        "summary (2-3 sentences, warm and concrete, mention numbers), "
        "wins (2-3 short bullets in second person), "
        "focus (2-3 short bullets — what to improve), "
        "tip (one actionable sentence). "
        f"Language: {lang}. Avoid generic advice — refer to the actual numbers.\n\n"
        f"Stats JSON:\n{json.dumps(stats, ensure_ascii=False)}"
    )
    response = await _call_model(lambda: model.generate_content_async(prompt))
    data = json.loads(_strip_code_fence(response.text))
    return {
        "summary": str(data.get("summary", "")).strip(),
        "wins": [str(x).strip() for x in (data.get("wins") or [])][:5],
        "focus": [str(x).strip() for x in (data.get("focus") or [])][:5],
        "tip": str(data.get("tip", "")).strip(),
    }


@async_retry(**_GEMINI_RETRY)
async def chat(message: str, context: list[dict], user_info: dict, lang: str = "ru") -> str:
    model = _get_model()
    system = (
        "You are PROpitashka AI assistant — a friendly nutrition and fitness expert. "
        f"User parameters: {json.dumps(user_info)}. "
        f"Respond in language: {lang}. Be helpful, specific, and encouraging."
    )
    history_text = "\n".join(
        f"{'User' if m['message_type'] == 'user' else 'Assistant'}: {m['message_text']}"
        for m in context[-10:]
    )
    full_prompt = f"{system}\n\nChat history:\n{history_text}\n\nUser: {message}\nAssistant:"
    response = await _call_model(lambda: model.generate_content_async(full_prompt))
    return response.text
