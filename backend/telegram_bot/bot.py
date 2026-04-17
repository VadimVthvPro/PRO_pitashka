import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import get_settings

logger = logging.getLogger(__name__)

bot: Bot | None = None
dp: Dispatcher | None = None
_task: asyncio.Task | None = None


async def _save_username_middleware(handler, event, data):
    """Middleware that persists telegram_username on every interaction."""
    from aiogram import types as _types
    user = None
    if isinstance(event, _types.Message) and event.from_user:
        user = event.from_user
    elif isinstance(event, _types.CallbackQuery) and event.from_user:
        user = event.from_user

    if user and user.username:
        try:
            from app.database import get_pool
            pool = await get_pool()
            await pool.execute(
                "UPDATE user_main SET telegram_username = $2 WHERE user_id = $1",
                user.id, user.username.lower(),
            )
        except Exception:
            pass

    return await handler(event, data)


async def start_bot() -> None:
    global bot, dp, _task
    settings = get_settings()

    if not settings.TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_TOKEN not set, bot will not start")
        return

    bot = Bot(token=settings.TELEGRAM_TOKEN)
    dp = Dispatcher()
    dp.message.middleware(_save_username_middleware)
    dp.callback_query.middleware(_save_username_middleware)

    from telegram_bot.handlers.otp import otp_router
    from telegram_bot.handlers.notifications import notifications_router
    dp.include_router(otp_router)
    dp.include_router(notifications_router)

    _task = asyncio.create_task(_run_polling())
    logger.info("Telegram bot started (OTP + notifications mode)")


async def _run_polling() -> None:
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Bot polling error: %s", e)


async def stop_bot() -> None:
    global _task, bot, dp
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    if bot:
        await bot.session.close()
    logger.info("Telegram bot stopped")


async def send_otp_message(chat_id: int, code: str) -> bool:
    if not bot:
        logger.error("Bot not initialized, cannot send OTP")
        return False
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🔐 Ваш код для входа на PROpitashka: <b>{code}</b>\n\n"
                 f"Код действителен 5 минут. Не сообщайте его никому.",
            parse_mode="HTML",
        )
        return True
    except Exception as e:
        logger.error("Failed to send OTP to %s: %s", chat_id, e)
        return False


async def send_notification(chat_id: int, text: str) -> bool:
    if not bot:
        return False
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        return True
    except Exception as e:
        logger.error("Failed to send notification to %s: %s", chat_id, e)
        return False
