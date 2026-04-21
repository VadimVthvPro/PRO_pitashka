"""Подпись state-токенов для OAuth redirect flow.

Вместо того, чтобы хранить OAuth-state в Redis/БД, подписываем его
коротким JWT (TTL 10 минут) с секретом бэкенда. Плюсы:

* Stateless: нет таблицы, которую надо чистить и которая теряется при
  рестарте Redis.
* Безопасно: подделать токен без `JWT_SECRET_KEY` нельзя, а CSRF
  защищает issuer → audience связка (мы пишем в payload `purpose`
  и при callback'е сверяем).
* Поддерживает оба режима: `purpose=login_<provider>` создаёт новую
  сессию, `purpose=link_<provider>` привязывает к уже залогиненному
  `user_id` (тоже зашит в state).

Примечание: токен передаётся в query-параметре `state=...`, который
Yandex/VK просто возвращают обратно в callback. В эту точку НЕ кладём
ничего чувствительного — только ID намерения; сам access_token
получается на backend'е через client_secret и никогда не видит браузер.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import jwt
from jose.exceptions import JWTError

from app.config import get_settings


_STATE_TTL_MINUTES = 10
_STATE_TYPE = "oauth_state"

Provider = Literal["yandex", "vk"]
Purpose = Literal["login", "link"]


def sign_oauth_state(
    provider: Provider,
    purpose: Purpose,
    *,
    user_id: int | None = None,
    return_to: str | None = None,
) -> str:
    """Сформировать JWT, который мы положим в OAuth query-param `state`.

    - provider: yandex / vk (определяет, в какой callback ожидаем возврат)
    - purpose: login (создать сессию) / link (привязать к user_id)
    - user_id: обязателен если purpose='link'
    - return_to: опциональный относительный путь в приложении, куда
      редиректить после успешного входа (по умолчанию — /dashboard
      или /onboarding, решение принимает backend по needs_onboarding).
    """
    if purpose == "link" and user_id is None:
        raise ValueError("user_id required for link-purpose state")

    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "type": _STATE_TYPE,
        "provider": provider,
        "purpose": purpose,
        "nonce": secrets.token_urlsafe(12),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=_STATE_TTL_MINUTES)).timestamp()),
    }
    if user_id is not None:
        payload["uid"] = user_id
    if return_to:
        payload["rt"] = return_to
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_oauth_state(state: str, expected_provider: Provider) -> dict[str, Any]:
    """Проверить state из callback'а и вернуть разобранный payload.

    Бросает ValueError с понятным сообщением, если state недействителен,
    истёк, не того типа или пришёл в callback «не того» провайдера.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(state, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError(f"invalid state: {e}") from e

    if payload.get("type") != _STATE_TYPE:
        raise ValueError("wrong state type")
    if payload.get("provider") != expected_provider:
        raise ValueError(f"state issued for {payload.get('provider')}, expected {expected_provider}")
    return payload
