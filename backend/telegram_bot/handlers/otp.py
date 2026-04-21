"""Telegram bot handler: `/start` + inline «новый ключ».

Главный принцип новой схемы (после alembic 017): **OTP привязан к
`user_main.user_id = message.from_user.id`**, а не к `@username`. Это
значит:

* Пользователю не нужно иметь публичный `@username` в Telegram.
* На сайте достаточно одного инпута для 6-значного alphanumeric кода.
* Бот — единственный, кто генерирует OTP-коды. Сайту не нужен
  эндпоинт `/api/auth/request-otp`.

Обработчики здесь:

    /start (c command-filter'ом) → создать user_main (UPSERT), выдать
                                   свежий код, прикрепить inline-кнопку
                                   «🔁 Прислать новый ключ».

    callback_query "otp:new"     → сгенерить ещё один код (например,
                                   если пользователь прокликал первый
                                   или ключ истёк), заменить inline-
                                   кнопку новым сообщением.
"""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app import brand as _brand
from app.database import get_pool
from app.services import auth_service

logger = logging.getLogger(__name__)
otp_router = Router()


def _otp_keyboard() -> InlineKeyboardMarkup:
    """Единая inline-клавиатура «🔁 Прислать новый ключ».

    Используется и при /start, и после callback'а resend — чтобы
    пользователь мог запросить ещё один код не выходя из чата.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Прислать новый ключ", callback_data="otp:new")]
        ]
    )


async def _upsert_user(tg_user) -> None:
    """Гарантировать, что user_main существует для данного Telegram user_id.

    Username записывается в опциональное поле `telegram_username` —
    только для UI (отобразить «Telegram: @you» в Настройках). OTP flow
    им больше не пользуется.

    Сохраняем имя в `display_name` и `user_name` (оба поля заполняются
    одинаково при первом /start, но потом могут разъехаться: напр.
    настройки / Google / Yandex-профиль заменит `display_name`).
    """
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
        "Возвращайся на сайт и вставь этот ключ в форму входа:\n\n"
        f"<code>{code}</code>\n\n"
        "Ключ действует 15 минут. Если случайно закрыл сообщение или "
        "ключ не подошёл — жми кнопку ниже, вышлю новый."
    )


@otp_router.message(CommandStart())
async def cmd_start(message: Message):
    """Создаём user + выдаём ключ. Без требования @username."""
    try:
        await _upsert_user(message.from_user)
    except Exception as e:
        # Даже если БД на мгновение недоступна, пользователю пишем понятное
        # сообщение вместо «bot crashed».
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
        reply_markup=_otp_keyboard(),
    )


@otp_router.callback_query(lambda c: c.data == "otp:new")
async def cb_resend_otp(callback: CallbackQuery):
    """Выдать новый ключ по нажатию inline-кнопки.

    Старый код инвалидируется (request_otp_for_user сам помечает все
    активные коды этого user_id как used=TRUE перед INSERT). Сообщение
    отправляем новое, а предыдущее оставляем нетронутым — удобно, если
    пользователь вернётся к нему позже и увидит в истории чата
    прогресс: два ключа подряд ≠ два активных ключа.
    """
    tg_user = callback.from_user
    try:
        await _upsert_user(tg_user)  # на всякий случай — если кто-то нажал
        # кнопку до /start (теоретически невозможно, но дёшево подстраховаться).
    except Exception:
        # Не прерываем flow: user_id у нас уже есть, создать OTP можем и без
        # успешного upsert'а (хотя FK-ограничения на user_main в otp_codes нет).
        pass

    pool = await get_pool()
    code = await auth_service.request_otp_for_user(pool, tg_user.id)
    if not code:
        await callback.answer("Не удалось сгенерировать ключ", show_alert=True)
        return

    await callback.message.answer(
        _otp_message(code),
        parse_mode="HTML",
        reply_markup=_otp_keyboard(),
    )
    # Закрываем «часики» на inline-кнопке — обязательный ответ на callback,
    # иначе Telegram-клиент будет показывать спиннер до таймаута.
    await callback.answer("Новый ключ отправлен")
