"""Telegram bot handler: `/start` + inline «новый ключ» + magic link.

OTP привязан к `user_main.user_id = message.from_user.id` (не к @username).

При /start бот:
1. Upsert'ит user_main (авторегистрация).
2. Генерирует OTP-код.
3. Шлёт сообщение с двумя кнопками:
   - «Открыть NutriFit» — URL magic link (/api/auth/magic?code=...),
     автоматически логинит без ввода кода.
   - «Прислать новый ключ» — callback, генерирует свежий код.
4. Код видим в тексте сообщения для ручного входа с другого устройства.
"""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app import brand as _brand
from app.config import get_settings
from app.database import get_pool
from app.services import auth_service

logger = logging.getLogger(__name__)
otp_router = Router()


def _magic_url(code: str) -> str:
    """URL для автовхода: backend верифицирует код и ставит cookies."""
    base = (get_settings().FRONTEND_URL or "http://localhost:3000").rstrip("/")
    return f"{base}/api/auth/magic?code={code}"


def _otp_keyboard(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Открыть NutriFit", url=_magic_url(code))],
            [InlineKeyboardButton(text="🔁 Прислать новый ключ", callback_data="otp:new")],
        ]
    )


async def _upsert_user(tg_user) -> None:
    full_name = (tg_user.full_name or tg_user.first_name or "").strip() or None
    username = tg_user.username.lower() if tg_user.username else None

    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO user_main (user_id, user_name, display_name, telegram_username)
        VALUES ($1, $2, $2, $3)
        ON CONFLICT (user_id) DO UPDATE
            SET telegram_username = COALESCE(EXCLUDED.telegram_username, user_main.telegram_username),
                user_name         = COALESCE(user_main.user_name, EXCLUDED.user_name),
                display_name      = COALESCE(user_main.display_name, EXCLUDED.display_name)
        """,
        tg_user.id, full_name, username,
    )


def _otp_message(code: str) -> str:
    brand_name = _brand.display_name()
    return (
        f"👋 Привет! Я бот {brand_name}.\n\n"
        "Нажми кнопку ниже — вход на сайт произойдёт автоматически.\n\n"
        "Если входишь с другого устройства, вот ключ для ручного ввода:\n\n"
        f"<code>{code}</code>\n\n"
        "Ключ действует 15 минут."
    )


@otp_router.message(CommandStart())
async def cmd_start(message: Message):
    try:
        await _upsert_user(message.from_user)
    except Exception as e:
        logger.exception("Failed to upsert user %s in /start: %s", message.from_user.id, e)
        await message.answer(
            "Упс, что-то пошло не так на нашей стороне. Попробуй /start ещё раз через минуту."
        )
        return

    pool = await get_pool()
    code = await auth_service.request_otp_for_user(pool, message.from_user.id)
    if not code:
        logger.error("OTP generation failed for user %s", message.from_user.id)
        await message.answer("Не получилось сгенерировать ключ. Попробуй /start ещё раз.")
        return

    await message.answer(
        _otp_message(code),
        parse_mode="HTML",
        reply_markup=_otp_keyboard(code),
    )


@otp_router.callback_query(lambda c: c.data == "otp:new")
async def cb_resend_otp(callback: CallbackQuery):
    tg_user = callback.from_user
    try:
        await _upsert_user(tg_user)
    except Exception:
        pass

    pool = await get_pool()
    code = await auth_service.request_otp_for_user(pool, tg_user.id)
    if not code:
        await callback.answer("Не удалось сгенерировать ключ", show_alert=True)
        return

    await callback.message.answer(
        _otp_message(code),
        parse_mode="HTML",
        reply_markup=_otp_keyboard(code),
    )
    await callback.answer("Новый ключ отправлен")
