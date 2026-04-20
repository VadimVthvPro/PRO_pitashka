"""Stars-платежи: команды бота + обработка pre_checkout / successful_payment.

Сценарий:
1. Фронт создаёт invoice через `/api/billing/stars/invoice` — это уже
   пишет payload в `star_payments(status='pending')` и возвращает t.me-URL.
2. Юзер оплачивает — Telegram шлёт `PreCheckoutQuery` боту.
3. Мы сверяем payload с БД и одобряем / отклоняем.
4. После успешной оплаты Telegram шлёт `Message.successful_payment` —
   мы помечаем платёж `paid` и вызываем `subscription_service.grant()`.

Для сценария «оплата прямо из бота» (команда `/premium`) добавлены
inline-кнопки со списком планов.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
)

from app.database import get_pool
from app.redis import get_redis
from app.repositories.billing_repo import BillingRepository
from app.services import subscription_service

logger = logging.getLogger(__name__)
payments_router = Router()


# ---------------------------------------------------------------------------
# /premium : показать список тарифов
# ---------------------------------------------------------------------------


@payments_router.message(Command("premium"))
async def cmd_premium(message: Message) -> None:
    pool = await get_pool()
    repo = BillingRepository(pool)
    plans = await repo.list_plans(include_free=False)
    if not plans:
        await message.answer("Тарифы временно недоступны.")
        return

    kb_rows: list[list[InlineKeyboardButton]] = []
    for p in plans:
        kb_rows.append([
            InlineKeyboardButton(
                text=f"{p['name']} — {p['price_stars']} ⭐",
                callback_data=f"buy:{p['plan_key']}",
            )
        ])
    kb_rows.append([
        InlineKeyboardButton(text="Открыть сайт", url="https://t.me/PROpitashka_bot"),
    ])

    text = (
        "✨ <b>Premium в PROpitashka</b>\n\n"
        "Расширенные лимиты на AI-чат, фото-анализ и планы питания.\n"
        "Оплата — звёздами Telegram, без привязки карты."
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
    )


@payments_router.callback_query(F.data.startswith("buy:"))
async def cb_buy_plan(query: CallbackQuery) -> None:
    from telegram_bot import stars as stars_mod

    if not query.data or not query.from_user:
        await query.answer()
        return
    plan_key = query.data.split(":", 1)[1]

    pool = await get_pool()
    repo = BillingRepository(pool)
    plan = await repo.get_plan(plan_key)
    if not plan or plan.get("tier") == "free":
        await query.answer("Тариф не найден", show_alert=True)
        return

    payload = stars_mod.generate_invoice_payload(query.from_user.id, plan["plan_key"])
    await repo.create_star_payment(
        user_id=query.from_user.id,
        plan_key=plan["plan_key"],
        invoice_payload=payload,
        stars_amount=int(plan["price_stars"]),
    )

    from aiogram.types import LabeledPrice
    try:
        await query.message.answer_invoice(
            title=f"{plan['name']} — PROpitashka"[:32],
            description=_desc(plan),
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=plan["name"][:32], amount=int(plan["price_stars"]))],
        )
        await query.answer()
    except Exception as exc:
        logger.exception("answer_invoice failed: %s", exc)
        await query.answer("Не удалось создать инвойс", show_alert=True)


# ---------------------------------------------------------------------------
# PreCheckoutQuery
# ---------------------------------------------------------------------------


@payments_router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    pool = await get_pool()
    repo = BillingRepository(pool)

    payment = await repo.get_star_payment_by_payload(query.invoice_payload)
    if not payment:
        logger.warning("pre_checkout: unknown payload=%s", query.invoice_payload)
        await query.answer(ok=False, error_message="Инвойс не найден, попробуй ещё раз.")
        return
    if payment["status"] != "pending":
        logger.warning("pre_checkout: payload=%s status=%s", query.invoice_payload, payment["status"])
        await query.answer(ok=False, error_message="Этот инвойс уже использован.")
        return
    if int(payment["stars_amount"]) != int(query.total_amount):
        logger.warning(
            "pre_checkout: amount mismatch payload=%s expected=%s got=%s",
            query.invoice_payload, payment["stars_amount"], query.total_amount,
        )
        await query.answer(ok=False, error_message="Сумма инвойса изменилась, обнови страницу.")
        return
    await query.answer(ok=True)


# ---------------------------------------------------------------------------
# SuccessfulPayment
# ---------------------------------------------------------------------------


@payments_router.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    sp = message.successful_payment
    if not sp or not message.from_user:
        return
    pool = await get_pool()
    redis = await get_redis()
    repo = BillingRepository(pool)

    payment = await repo.get_star_payment_by_payload(sp.invoice_payload)
    if not payment:
        logger.error("successful_payment: payload=%s not found in DB", sp.invoice_payload)
        await message.answer(
            "⚠️ Оплата прошла, но я не нашёл инвойс. Напиши в поддержку — звёзды вернём."
        )
        return
    if payment["status"] == "paid":
        # Дубль — игнорируем, Telegram иногда ретраит.
        logger.info("successful_payment: duplicate for payload=%s", sp.invoice_payload)
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            await repo.mark_payment_paid(
                conn,
                payment_id=payment["id"],
                telegram_payment_charge_id=sp.telegram_payment_charge_id,
                provider_payment_charge_id=sp.provider_payment_charge_id,
            )

    try:
        result = await subscription_service.grant(
            pool, redis,
            user_id=payment["user_id"],
            plan_key=payment["plan_key"],
            source="stars",
            payment_id=payment["id"],
        )
    except Exception as exc:
        logger.exception("grant after successful_payment failed: %s", exc)
        await message.answer(
            "⚠️ Оплата прошла, но активация не удалась. Напиши в поддержку — мы всё починим."
        )
        return

    end_at = result.get("end_at")
    end_str = end_at.strftime("%d.%m.%Y") if end_at else "—"
    await message.answer(
        f"✅ Оплата получена — спасибо! Активирован <b>{result.get('name')}</b> до {end_str}.\n\n"
        f"Возвращайся на сайт — лимиты уже расширены.",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------

def _desc(plan: dict) -> str:
    feats = plan.get("features") or []
    dur = plan.get("duration_days")
    parts: list[str] = []
    if dur:
        parts.append(f"{dur} дней")
    if feats:
        parts.append(" · ".join(str(f) for f in feats[:3]))
    return (" · ".join(parts) or plan["name"])[:255]
