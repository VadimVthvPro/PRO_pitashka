"""Dual-brand configuration for backend.

Централизованный источник правды о бренде. Все места, где раньше был
хардкод ``"PROpitashka"`` (AI-промпты, telegram-бот, paywall, локали,
логи), читают имя отсюда.

Переключение между брендами:
    1. в ``.env.freemium`` выставить ``BRAND=profit`` или ``BRAND=propitashka``
    2. ``docker compose -f docker-compose.freemium.yml restart backend_freemium``
    3. новый бренд активен через ~5 секунд

См. ``BRAND_ARCHITECTURE.md`` и правило
``.cursor/rules/dual-brand-parity.mdc``.
"""

from __future__ import annotations

from typing import TypedDict

from app.config import get_settings


class BrandData(TypedDict):
    name: str           # canonical id (used in env, urls, internal code)
    display_name: str   # as shown to user in UI / AI responses
    short_name: str     # compact form for tight UI (sidebar, telegram)
    tagline: str        # one-line pitch
    # Словоформа для обращения «Спроси X» / «Ask X» по языкам UI.
    # В русском у propitashka это винительный падеж "Пропитошку";
    # PROfit не склоняется — одинаково на всех языках.
    ask_form: dict[str, str]


BRANDS: dict[str, BrandData] = {
    "propitashka": {
        "name": "propitashka",
        "display_name": "PROpitashka",
        "short_name": "ПРОпиташка",
        "tagline": "Тёплый дневник питания и тренировок",
        "ask_form": {
            "ru": "Пропитошку",
            "en": "Propitoshka",
            "de": "Propitoshka",
            "fr": "Propitoshka",
            "es": "Propitoshka",
        },
    },
    "profit": {
        "name": "profit",
        "display_name": "PROfit",
        "short_name": "PROfit",
        "tagline": "AI-наставник по питанию и тренировкам",
        "ask_form": {
            "ru": "PROfit",
            "en": "PROfit",
            "de": "PROfit",
            "fr": "PROfit",
            "es": "PROfit",
        },
    },
}

_DEFAULT = "propitashka"


def current() -> BrandData:
    """Return the brand data for the currently active brand.

    Reads :attr:`Settings.BRAND` on every call (cheap — ``get_settings`` is
    memoised). Falls back to propitashka if the env value is unknown.
    """
    raw = (get_settings().BRAND or _DEFAULT).strip().lower()
    return BRANDS.get(raw, BRANDS[_DEFAULT])


def display_name() -> str:
    """Shortcut: the brand name as shown to the user."""
    return current()["display_name"]


def short_name() -> str:
    """Shortcut: the compact brand name for tight layouts."""
    return current()["short_name"]


def tagline() -> str:
    """Shortcut: one-line pitch."""
    return current()["tagline"]


def ask_form(lang: str) -> str:
    """Brand name in «Ask X» form for the given UI language.

    Falls back to :func:`display_name` if the language is unknown.
    """
    return current()["ask_form"].get((lang or "ru").lower(), display_name())
