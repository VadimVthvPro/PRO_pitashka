"""Обёртка над Bot API для Telegram Stars.

Нужна, чтобы routers/billing.py не знал об aiogram напрямую — достаточно
вызвать `create_stars_invoice_link()` и получить готовый `t.me/$/invoice/...`
URL. Токен провайдера для Stars НЕ используется (валюта `XTR`).
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from aiogram.types import LabeledPrice

logger = logging.getLogger(__name__)


def generate_invoice_payload(user_id: int, plan_key: str) -> str:
    """`pay:{user_id}:{plan_key}:{random}` — уникально, читаемо в логах."""
    nonce = secrets.token_urlsafe(12)
    return f"pay:{user_id}:{plan_key}:{nonce}"


async def create_stars_invoice_link(
    *,
    title: str,
    description: str,
    plan_key: str,
    stars_amount: int,
    payload: str,
) -> str:
    """Создаёт Stars-invoice link через activeBot().

    Не дергает `sendInvoice` напрямую — возвращает URL, который можно открыть
    из браузера/приложения и Telegram сам покажет окно оплаты. Это
    позволяет работать с фронтом, не привязываясь к конкретному chat_id.
    """
    from telegram_bot.bot import bot  # late import — модуль-синглтон инициализируется в startup
    if bot is None:
        raise RuntimeError("Telegram bot is not initialized")
    link = await bot.create_invoice_link(
        title=title[:32],
        description=description[:255],
        payload=payload,
        provider_token="",          # Stars → пустой токен провайдера
        currency="XTR",
        prices=[LabeledPrice(label=title[:32], amount=int(stars_amount))],
    )
    return link


async def refund_star_payment(
    *, user_id: int, telegram_payment_charge_id: str
) -> bool:
    """Админская команда: возвращает звёзды конкретному платежу."""
    from telegram_bot.bot import bot
    if bot is None:
        return False
    try:
        await bot.refund_star_payment(
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
        )
        return True
    except Exception as exc:
        logger.exception("refund_star_payment failed: %s", exc)
        return False


async def get_bot_username() -> str | None:
    """Используется, чтобы фронт мог построить fallback-ссылку `t.me/<bot>?start=…`."""
    from telegram_bot.bot import bot
    if bot is None:
        return None
    try:
        me = await bot.get_me()
        return me.username
    except Exception:
        return None
