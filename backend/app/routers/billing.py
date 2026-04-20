"""HTTP API биллинга: /api/billing/*.

Эндпоинты:
    GET  /api/billing/me              — тир, лимиты, usage, auto_renew
    GET  /api/billing/plans           — публичный справочник тарифов
    GET  /api/billing/history         — история Stars-платежей юзера
    POST /api/billing/stars/invoice   — создать Stars-invoice link, вернуть URL
    POST /api/billing/cancel          — выключить auto_renew
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.dependencies import CurrentUserDep, DbDep, RedisDep
from app.models.billing import (
    HistoryOut,
    InvoiceCreate,
    InvoiceOut,
    MeOut,
    PaymentOut,
    PlanOut,
    UsageItem,
)
from app.repositories.billing_repo import BillingRepository
from app.services import quota_service, subscription_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me", response_model=MeOut)
async def billing_me(user_id: CurrentUserDep, pool: DbDep, redis: RedisDep):
    sub = await subscription_service.resolve(pool, redis, user_id)
    usage_status = await quota_service.get_all_status(pool, redis, user_id)
    items = [
        UsageItem(
            key=s.key,
            limit=s.limit,
            period=s.period,
            used=s.used,
            allowed=s.allowed,
            reset_at=s.reset_at,
        )
        for s in usage_status
    ]
    auto_renew = False
    active = await BillingRepository(pool).get_active_subscription(user_id)
    if active:
        auto_renew = bool(active.get("auto_renew"))
    return MeOut(
        tier=sub["tier"],
        plan_key=sub["plan_key"],
        plan_name=sub.get("name") or sub["plan_key"],
        status=sub.get("status") or "active",
        source=sub.get("source"),
        end_at=sub.get("end_at"),
        features=sub.get("features") or [],
        usage=items,
        auto_renew=auto_renew,
    )


@router.get("/plans", response_model=list[PlanOut])
async def billing_plans(pool: DbDep):
    plans = await BillingRepository(pool).list_plans(include_free=True)
    return [PlanOut(**p) for p in plans]


@router.get("/history", response_model=HistoryOut)
async def billing_history(user_id: CurrentUserDep, pool: DbDep):
    rows = await BillingRepository(pool).list_user_payments(user_id, limit=50)
    return HistoryOut(payments=[PaymentOut(**r) for r in rows])


@router.post("/stars/invoice", response_model=InvoiceOut)
async def create_stars_invoice(
    body: InvoiceCreate, user_id: CurrentUserDep, pool: DbDep,
):
    """Создаёт Stars-invoice для указанного плана.

    Фронт получает URL (`https://t.me/$/invoice/…`) — достаточно открыть
    его в WebApp или обычной ссылкой — Telegram сам покажет окно оплаты.
    На pre_checkout/successful_payment платёж обработает `payments.py`.
    """
    from telegram_bot import stars as stars_mod

    plan = await BillingRepository(pool).get_plan(body.plan_key)
    if not plan or plan.get("tier") == "free":
        raise HTTPException(status_code=404, detail="Тариф не найден")
    if not plan.get("price_stars"):
        raise HTTPException(status_code=400, detail="Этот план не продаётся за звёзды")

    payload = stars_mod.generate_invoice_payload(user_id, plan["plan_key"])
    # Сперва пишем запись в БД — так pre_checkout гарантированно найдёт payload.
    await BillingRepository(pool).create_star_payment(
        user_id=user_id,
        plan_key=plan["plan_key"],
        invoice_payload=payload,
        stars_amount=int(plan["price_stars"]),
    )

    title = f"{plan['name']} — PROpitashka"
    description = _plan_description(plan)

    try:
        link = await stars_mod.create_stars_invoice_link(
            title=title,
            description=description,
            plan_key=plan["plan_key"],
            stars_amount=int(plan["price_stars"]),
            payload=payload,
        )
    except Exception as exc:
        logger.exception("create_stars_invoice_link failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "invoice_failed",
                "message": "Не удалось создать инвойс. Попробуй позже.",
            },
        )

    bot_username = await stars_mod.get_bot_username()
    return InvoiceOut(
        plan_key=plan["plan_key"],
        plan_name=plan["name"],
        stars_amount=int(plan["price_stars"]),
        invoice_url=link,
        invoice_payload=payload,
        bot_username=bot_username,
    )


@router.post("/cancel")
async def billing_cancel(user_id: CurrentUserDep, pool: DbDep, redis: RedisDep):
    """Отменяет auto_renew активной подписки. Тир сохранится до `end_at`."""
    await subscription_service.cancel_auto_renew(pool, redis, user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------

def _plan_description(plan: dict) -> str:
    feats = plan.get("features") or []
    parts: list[str] = []
    if plan.get("duration_days"):
        parts.append(f"{plan['duration_days']} дней")
    if feats:
        parts.append(" · ".join(str(f) for f in feats[:3]))
    if not parts:
        return plan["name"]
    return " · ".join(parts)
