import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.database import get_pool
from app import brand as _brand

logger = logging.getLogger(__name__)
otp_router = Router()


async def _save_telegram_username(user_id: int, username: str | None, full_name: str | None = None) -> None:
    """Upsert the user so the web OTP flow can look up the chat_id by username."""
    try:
        pool = await get_pool()
        await pool.execute(
            """
            INSERT INTO user_main (user_id, user_name, telegram_username)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE
                SET telegram_username = COALESCE(EXCLUDED.telegram_username, user_main.telegram_username),
                    user_name = COALESCE(EXCLUDED.user_name, user_main.user_name)
            """,
            user_id,
            full_name,
            username.lower() if username else None,
        )
    except Exception as e:
        logger.warning("Failed to upsert user %s: %s", user_id, e)


async def _pop_pending_otp(telegram_username: str) -> str | None:
    """If the website is waiting for this user, return the freshest unused code.

    The OTP is left valid (not marked used) so the user can copy it from the
    chat and paste it on the website. We just want to surface it proactively
    instead of forcing the user to retry from the website.
    """
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            """
            SELECT code FROM otp_codes
            WHERE telegram_username = $1
              AND used = FALSE
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """,
            telegram_username.lower(),
        )
        return row["code"] if row else None
    except Exception as e:
        logger.warning("Failed to fetch pending OTP for %s: %s", telegram_username, e)
        return None


@otp_router.message(CommandStart())
async def cmd_start(message: Message):
    full_name = (message.from_user.full_name or message.from_user.first_name or "").strip() or None
    await _save_telegram_username(
        message.from_user.id,
        message.from_user.username,
        full_name,
    )

    brand_name = _brand.display_name()

    if not message.from_user.username:
        await message.answer(
            f"👋 Привет! Я бот {brand_name}.\n\n"
            "⚠️ У тебя не задан Telegram @username — без него сайт не сможет найти твой чат.\n"
            "Открой Telegram → Settings → Username и придумай его, потом отправь /start ещё раз."
        )
        return

    pending = await _pop_pending_otp(message.from_user.username)
    if pending:
        await message.answer(
            f"👋 Привет! Я бот {brand_name}.\n\n"
            f"Сайт ждёт от тебя код — вот он:\n\n"
            f"<code>{pending}</code>\n\n"
            f"Скопируй и вставь на сайте. Действует 5 минут.",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"👋 Привет! Я бот {brand_name}.\n\n"
        "Через меня приходят коды для входа на сайт и уведомления.\n"
        f"Твой @{message.from_user.username} сохранён — теперь возвращайся на сайт "
        f"и нажми «Прислать код»."
    )
