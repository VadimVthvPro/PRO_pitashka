"""FastAPI-зависимости для проверки тира и квот.

Использование:

    from app.dependencies_billing import quota, require_tier

    @router.post("/chat")
    async def ai_chat(..., _q = Depends(quota("ai_chat_msg"))):
        ...

    @router.get("/export")
    async def export_csv(..., _t = Depends(require_tier("premium"))):
        ...

Оба зависят от `CurrentUserDep`/`DbDep`/`RedisDep`, т.е. требуют
авторизованного запроса.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.dependencies import CurrentUserDep, DbDep, RedisDep
from app.services import subscription_service
from app.services.quota_service import (
    QuotaExceeded,
    QuotaStatus,
    check as quota_check,
    consume as quota_consume,
)


_TIER_ORDER = {"free": 0, "premium": 1, "pro": 2}


def _paywall_detail(
    *,
    code: str,
    message: str,
    plan_key: str,
    tier: str,
    quota_key: str | None = None,
    limit: int | None = None,
    used: int | None = None,
    reset_at: str | None = None,
    required_tier: str | None = None,
) -> dict:
    """Единый формат detail для 402 Payment Required.

    Фронт ловит этот JSON и открывает paywall-модалку; backend-side только
    заполняет поля, не знает деталей UI.
    """
    detail: dict = {
        "code": code,
        "message": message,
        "plan_key": plan_key,
        "tier": tier,
        "upgrade": {
            "suggested_plan_key": "premium_month" if tier == "free" else "pro_month",
            "billing_url": "/billing",
        },
    }
    if quota_key:
        detail["quota_key"] = quota_key
    if limit is not None:
        detail["limit"] = limit
    if used is not None:
        detail["used"] = used
    if reset_at:
        detail["reset_at"] = reset_at
    if required_tier:
        detail["required_tier"] = required_tier
    return detail


def quota(key: str, *, consume: bool = True):
    """Фабрика зависимостей под конкретную квоту.

    При `consume=True` (по умолчанию) счётчик инкрементируется до выполнения
    роута. Если сам роут потом падает, мы квоту НЕ возвращаем — это осознанно:
    при ретраях фронт будет честно видеть расход. Если в будущем захочется
    возвращать при ошибке — можно добавить `consume=False` и вызывать
    `quota_service.consume()` вручную после успеха.
    """
    async def _dep(
        user_id: CurrentUserDep,
        pool: DbDep,
        redis: RedisDep,
    ) -> QuotaStatus:
        try:
            if consume:
                status_q = await quota_consume(pool, redis, user_id, key)
            else:
                status_q = await quota_check(pool, redis, user_id, key)
                if not status_q.allowed:
                    raise QuotaExceeded(status_q, _human_message(status_q))
        except QuotaExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=_paywall_detail(
                    code="quota_exceeded",
                    message=exc.message,
                    plan_key=exc.status.plan_key,
                    tier=exc.status.tier,
                    quota_key=exc.status.key,
                    limit=exc.status.limit,
                    used=exc.status.used,
                    reset_at=exc.status.reset_at.isoformat() if exc.status.reset_at else None,
                ),
            )
        return status_q

    return _dep


def require_tier(min_tier: str):
    """Требует тир не ниже `min_tier` ('premium' или 'pro')."""
    min_level = _TIER_ORDER.get(min_tier, 0)

    async def _dep(
        user_id: CurrentUserDep,
        pool: DbDep,
        redis: RedisDep,
    ) -> dict:
        sub = await subscription_service.resolve(pool, redis, user_id)
        level = _TIER_ORDER.get(sub["tier"], 0)
        if level < min_level:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=_paywall_detail(
                    code="require_tier",
                    message=f"Эта функция доступна на тарифе {min_tier}.",
                    plan_key=sub["plan_key"],
                    tier=sub["tier"],
                    required_tier=min_tier,
                ),
            )
        return sub

    return _dep


def _human_message(status_q: QuotaStatus) -> str:
    period = "на сегодня" if status_q.period == "d" else "в этом месяце"
    return f"Лимит {status_q.key} {period} исчерпан ({status_q.used}/{status_q.limit})."
