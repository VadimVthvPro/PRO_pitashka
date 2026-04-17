import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.database import get_pool

logger = logging.getLogger(__name__)
otp_router = Router()


async def _save_telegram_username(user_id: int, username: str | None) -> None:
    """Persist the Telegram @username so the web OTP flow can look up the chat_id."""
    if not username:
        return
    try:
        pool = await get_pool()
        await pool.execute(
            "UPDATE user_main SET telegram_username = $2 WHERE user_id = $1",
            user_id, username.lower(),
        )
    except Exception as e:
        logger.warning("Failed to save telegram_username for %s: %s", user_id, e)


@otp_router.message(CommandStart())
async def cmd_start(message: Message):
    await _save_telegram_username(message.from_user.id, message.from_user.username)
    await message.answer(
        "👋 Привет! Я бот PROpitashka.\n\n"
        "Через меня приходят коды для входа на сайт и уведомления.\n"
        "Перейдите на сайт для регистрации и использования всех функций."
    )
