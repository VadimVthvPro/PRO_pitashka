"""Общий хелпер установки auth-cookies (access + refresh).

Выделен в отдельный модуль, чтобы каждый auth-провайдер (Telegram OTP,
Google GIS, Yandex OAuth, VK ID) не дублировал одинаковую логику
set_cookie/delete_cookie и чтобы изменения в cookie-политике (secure,
samesite, path) применялись в одном месте.

Правила:

* `samesite="lax"` — достаточно для OAuth-редиректов обратно на наш
  домен (Google/Yandex/VK все делают top-level navigation), но
  блокирует third-party POST'ы → защита от CSRF.
* `secure=True` включается только в production (иначе local dev на
  http://localhost перестал бы логиниться).
* `path="/"` — куки видны на всех путях. Это важно: до миграции на `/`
  refresh-кука жила на `/api/auth/refresh`, из-за чего Next.js-middleware
  не видел её и мы ложно редиректили на /login при каждой навигации.
* `AUTH_COOKIE_PREFIX` (обычно `fm_` для freemium) отделяет cookie-пул
  freemium и основного сайта: они живут на одном хосте на разных портах,
  а HTTP-куки (RFC 6265) порт не учитывают.
"""

from fastapi import Response

from app.config import Settings


def set_auth_cookies(response: Response, settings: Settings, access: str, refresh: str) -> None:
    """Выставить access + refresh cookies на ответ."""
    secure = settings.ENVIRONMENT == "production"
    prefix = settings.AUTH_COOKIE_PREFIX
    response.set_cookie(
        key=prefix + "access_token",
        value=access,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key=prefix + "refresh_token",
        value=refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    """Удалить обе auth-cookies. Используется на logout и при invalid refresh."""
    prefix = settings.AUTH_COOKIE_PREFIX
    response.delete_cookie(prefix + "access_token", path="/")
    response.delete_cookie(prefix + "refresh_token", path="/")
    # Legacy path: до миграции на `/` refresh жил на `/api/auth/refresh`.
    # Если клиент ещё не пересетнул куку — уберём её и там, иначе старая
    # «призрачная» кука будет мешать фронту после logout.
    response.delete_cookie(prefix + "refresh_token", path="/api/auth/refresh")
