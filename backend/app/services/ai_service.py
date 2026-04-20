"""AI service: thin wrapper around google-generativeai with safe error handling.

The Gemini Python SDK uses simple API keys (not OAuth tokens). A valid Gemini
API key looks like ``AIzaSy...`` (39 chars). Anything else (in particular
``AQ.<...>`` strings, which are short-lived OAuth access tokens) will be rejected
by the API with 401/403 — and the user will see "AI quota exceeded" or similar
opaque errors.

Architecture
------------

* Each task (food photo, KBJU calc, meal plan, workout plan, recipe, weekly
  digest, chat) has its OWN ``GenerativeModel`` instance with its own
  ``system_instruction``. Models are cached by ``(model_name, key, role)`` so
  we never re-create them on hot paths.
* All prompts live in :mod:`app.services.prompts` so they can be audited,
  versioned and unit-tested in one place.
* Every call goes through :func:`_call_model` which adds a per-call timeout
  and translates SDK errors into typed application errors. A separate
  ``async_retry`` decorator handles transient 503/504/timeout failures with
  jittered exponential backoff.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
from typing import Any

import google.generativeai as genai

from app.config import get_settings
from app.services import prompts
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


# Static fallbacks — overridden at runtime by `runtime_settings`. The
# decorator-based retry still uses these as hard bounds; per-call timeout is
# re-read on every call so admin edits take effect without restart.
_PER_CALL_TIMEOUT = 60.0


async def _current_per_call_timeout() -> float:
    from app.services import runtime_settings as _rs
    try:
        v = await _rs.get_setting("gemini_per_call_timeout")
        return float(v) if v is not None else _PER_CALL_TIMEOUT
    except Exception:
        return _PER_CALL_TIMEOUT


def _ai_retry_predicate(exc: BaseException) -> bool:
    if isinstance(exc, (AIConfigError, AIQuotaError)):
        return False
    if isinstance(exc, AITimeoutError):
        return True
    if isinstance(exc, AIUpstreamError):
        return exc.retryable
    return is_retryable_exception(exc)


_GEMINI_RETRY = dict(
    attempts=5,
    base_delay=1.0,
    max_delay=20.0,
    factor=2.0,
    jitter=0.25,
    total_budget=150.0,
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
        logger.warning(
            "GEMINI_API_KEY does not start with the expected 'AIza' prefix "
            "(got %r...). Continuing, but expect 401/403 if this is wrong.",
            key[:6],
        )


# Cache: keyed by (model_name, key, role) so we keep one model per persona
# without re-initialising on every request.
_models: dict[tuple[str, str, str], genai.GenerativeModel] = {}
_configured_key: str | None = None


def _ensure_configured(key: str) -> None:
    global _configured_key
    if _configured_key != key:
        _validate_key(key)
        genai.configure(api_key=key)
        _configured_key = key
        logger.info("Gemini configured (key tail: ...%s)", key[-4:])


def _current_model_name() -> str:
    """Live model name: runtime override if present, else env, else default.

    Synchronous on purpose — the `_model_for` path is called from sync code
    too. We piggy-back on the process cache already populated by async reads
    (TTL=30s) and fall back to env if the cache hasn't warmed up yet.
    """
    from app.services import runtime_settings as _rs
    cached = _rs._cache.get("gemini_model")  # noqa: SLF001
    if cached:
        v = cached[1]
        if v:
            return str(v)
    return get_settings().GEMINI_MODEL or "gemini-2.5-flash"


def _model_for(role: str, system_instruction: str) -> genai.GenerativeModel:
    """Return a memoised model bound to the given system instruction."""
    settings = get_settings()
    key = settings.GEMINI_API_KEY
    model_name = _current_model_name()
    _ensure_configured(key)
    cache_key = (model_name, key, role)
    if cache_key not in _models:
        _models[cache_key] = genai.GenerativeModel(
            model_name, system_instruction=system_instruction
        )
        logger.info("Gemini model created (model=%s, role=%s)", model_name, role)
    return _models[cache_key]


def _generation_config(*, json_only: bool, max_tokens: int = 4096) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "temperature": 0.4 if json_only else 0.7,
        "top_p": 0.95,
        "max_output_tokens": max_tokens,
    }
    if json_only:
        cfg["response_mime_type"] = "application/json"
    return cfg


def _classify_error(exc: BaseException) -> Exception:
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
    timeout = await _current_per_call_timeout()
    try:
        return await asyncio.wait_for(coro_factory(), timeout=timeout)
    except (AIConfigError, AIQuotaError, AIUpstreamError):
        raise
    except asyncio.TimeoutError as exc:
        raise AITimeoutError() from exc
    except Exception as exc:
        raise _classify_error(exc) from exc


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        text = text[first_nl + 1 :] if first_nl != -1 else text
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _safe_json_loads(text: str) -> Any:
    """Best-effort JSON parse — strips markdown fences and trims trailing junk."""
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Find first '{' / '[' and last '}' / ']' and try again
        for opener, closer in (("[", "]"), ("{", "}")):
            i = cleaned.find(opener)
            j = cleaned.rfind(closer)
            if i != -1 and j != -1 and j > i:
                try:
                    return json.loads(cleaned[i : j + 1])
                except json.JSONDecodeError:
                    continue
        raise


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def health_check() -> dict[str, Any]:
    settings = get_settings()
    key = settings.GEMINI_API_KEY
    info: dict[str, Any] = {
        "key_present": bool(key),
        "key_prefix": (key[:6] + "...") if key else None,
        "key_tail": ("..." + key[-4:]) if key else None,
        "key_looks_valid": bool(key) and any(key.startswith(p) for p in _VALID_KEY_PREFIXES),
        "model": _current_model_name(),
        "env_model": settings.GEMINI_MODEL,
    }
    try:
        _validate_key(key)
    except AIConfigError as e:
        info["status"] = "misconfigured"
        info["error"] = str(e)
        return info

    try:
        model = _model_for("health", "You are a probe. Reply with exactly: OK")
        response = await asyncio.wait_for(
            model.generate_content_async("ping"), timeout=12,
        )
        info["status"] = "ok"
        info["sample"] = (response.text or "").strip()[:32]
    except asyncio.TimeoutError:
        info["status"] = "timeout"
    except Exception as e:
        wrapped = _classify_error(e)
        info["status"] = "error"
        info["error_type"] = type(wrapped).__name__
        info["error"] = str(wrapped)
    return info


# ---------------------------------------------------------------------------
# Structured tasks (JSON outputs)
# ---------------------------------------------------------------------------


@async_retry(**_GEMINI_RETRY)
async def recognize_food_photo(image_bytes: bytes, lang: str = "ru") -> list[dict]:
    model = _model_for(f"food_photo:{lang}", prompts.system_food_photo(lang))
    import PIL.Image  # local import keeps cold-start light

    image = PIL.Image.open(io.BytesIO(image_bytes))
    response = await _call_model(
        lambda: model.generate_content_async(
            [prompts.PROMPT_FOOD_PHOTO, image],
            generation_config=_generation_config(json_only=True, max_tokens=2048),
        )
    )
    data = _safe_json_loads(response.text)
    if not isinstance(data, list):
        raise AIUpstreamError("food photo response is not a JSON array", retryable=False)
    return data


@async_retry(**_GEMINI_RETRY)
async def analyze_food_text(
    foods: list[str], grams: list[float], lang: str = "ru"
) -> list[dict]:
    model = _model_for(f"food_text:{lang}", prompts.system_food_text(lang))
    items_repr = "\n".join(f"- {f.strip()} — {g}g" for f, g in zip(foods, grams))
    response = await _call_model(
        lambda: model.generate_content_async(
            prompts.prompt_food_text(items_repr),
            generation_config=_generation_config(json_only=True, max_tokens=2048),
        )
    )
    data = _safe_json_loads(response.text)
    if not isinstance(data, list):
        raise AIUpstreamError("food text response is not a JSON array", retryable=False)
    return data


@async_retry(**_GEMINI_RETRY)
async def weekly_digest(stats: dict, lang: str = "ru") -> dict:
    model = _model_for(f"digest:{lang}", prompts.system_weekly_digest(lang))
    response = await _call_model(
        lambda: model.generate_content_async(
            prompts.prompt_weekly_digest(stats),
            generation_config=_generation_config(json_only=True, max_tokens=1024),
        )
    )
    data = _safe_json_loads(response.text) or {}
    return {
        "summary": str(data.get("summary", "")).strip(),
        "wins": [str(x).strip() for x in (data.get("wins") or [])][:5],
        "focus": [str(x).strip() for x in (data.get("focus") or [])][:5],
        "tip": str(data.get("tip", "")).strip(),
    }


# ---------------------------------------------------------------------------
# Generative tasks (Markdown outputs)
# ---------------------------------------------------------------------------


@async_retry(**_GEMINI_RETRY)
async def generate_meal_plan(user_info: dict, lang: str = "ru") -> str:
    model = _model_for(f"meal_plan:{lang}", prompts.system_meal_plan(lang))
    response = await _call_model(
        lambda: model.generate_content_async(
            prompts.prompt_meal_plan(user_info),
            generation_config=_generation_config(json_only=False, max_tokens=8192),
        )
    )
    return (response.text or "").strip()


@async_retry(**_GEMINI_RETRY)
async def generate_workout_plan(user_info: dict, lang: str = "ru") -> str:
    model = _model_for(f"workout_plan:{lang}", prompts.system_workout_plan(lang))
    response = await _call_model(
        lambda: model.generate_content_async(
            prompts.prompt_workout_plan(user_info),
            generation_config=_generation_config(json_only=False, max_tokens=6144),
        )
    )
    return (response.text or "").strip()


@async_retry(**_GEMINI_RETRY)
async def generate_recipe(meal_type: str, user_info: dict, lang: str = "ru") -> str:
    model = _model_for(f"recipe:{lang}", prompts.system_recipe(lang))
    response = await _call_model(
        lambda: model.generate_content_async(
            prompts.prompt_recipe(meal_type, user_info),
            generation_config=_generation_config(json_only=False, max_tokens=2048),
        )
    )
    return (response.text or "").strip()


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@async_retry(**_GEMINI_RETRY)
async def chat(
    message: str,
    history: list[dict],
    user_info: dict,
    lang: str = "ru",
    *,
    today: dict | None = None,
    week: dict | None = None,
    meal_plan: str | None = None,
    workout_plan: str | None = None,
) -> str:
    """Generate a chat reply with full personal context.

    `history` is a list of `{message_type, message_text}` dicts in chronological
    order. `today`, `week`, `meal_plan`, `workout_plan` are optional context
    blocks pulled from the routers (so the AI service stays DB-agnostic).
    """
    model = _model_for(f"chat:{lang}", prompts.system_chat(lang))
    context_block = prompts.render_chat_context(
        user_info=user_info,
        today=today,
        week=week,
        meal_plan=meal_plan,
        workout_plan=workout_plan,
    )
    history_block = prompts.render_chat_history(history)
    full_prompt = prompts.prompt_chat(
        context_block=context_block,
        history_block=history_block,
        message=message,
    )
    response = await _call_model(
        lambda: model.generate_content_async(
            full_prompt,
            generation_config=_generation_config(json_only=False, max_tokens=2048),
        )
    )
    return (response.text or "").strip()
