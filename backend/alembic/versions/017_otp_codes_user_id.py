"""OTP codes: switch lookup from telegram_username to user_id.

Revision ID: 017_otp_codes_user_id
Revises: 016_oauth_providers
Create Date: 2026-04-21

### Контекст

Исходная схема `otp_codes` (миграция 002) хранила `telegram_username` как
обязательный ключ, по которому сайт находил OTP: пользователь вводил
@username на форме входа, сайт просил бэкенд сгенерить код, бот слал его
в чат соответствующего username, пользователь вводил на сайте пару
(username + code) → логин.

Эта схема имела три хронических проблемы:

1. Пользователи **без** публичного `@username` в Telegram не могли войти.
2. Пара (username + code) требовала два инпута на сайте — лишний шаг UX.
3. Если пользователь менял username в Telegram, старый код становился
   «призраком» без возможности использовать.

Новая схема: бот при `/start` генерирует 6-символьный alphanumeric код
и сохраняет его с `user_id = message.from_user.id`. Сайт принимает
**только код** — lookup идёт по `(code, used=FALSE, expires_at > NOW())`,
без username. Код достаточно длинный (32^6 ≈ 10^9), чтобы глобальная
уникальность активных кодов обеспечивалась partial unique index'ом.

### Что делает миграция

1. Backfill `otp_codes.user_id` из `user_main.telegram_username` там, где
   он ещё не проставлен (для любых активных старых OTP).
2. Удаляет остатки orphan-кодов без user_id: это истёкшие коды или
   коды для юзеров, которых нет в БД — они нам точно не нужны.
3. `telegram_username` остаётся (NULLABLE), чтобы старый код
   `/api/auth/request-otp` не сломался во время деплоя; после того как
   бот/фронт полностью переедут на user_id-flow, колонку можно будет
   дропнуть отдельной миграцией.
4. Partial unique index на `code WHERE used = FALSE`: гарантирует, что
   ни в один момент времени два активных OTP не могут иметь одинаковый
   код. `request_otp()` на backend ловит UniqueViolationError и
   генерирует новый код (retry 3 раза).

### Почему UNIQUE только по used = FALSE, а не (used=FALSE AND expires_at > NOW())

NOW() не IMMUTABLE → нельзя использовать в WHERE partial index'а.
WHERE used=FALSE стабилен и достаточен: истёкшие неиспользованные коды
в практике не блокируют insert (их мало, коллизии отсутствуют). Если
коллизия всё же случится — retry в бэкенд-коде её поглотит.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "017_otp_codes_user_id"
down_revision: Union[str, None] = "016_oauth_providers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Backfill user_id из существующих username-based записей
    op.execute(
        """
        UPDATE otp_codes o
        SET user_id = um.user_id
        FROM user_main um
        WHERE o.user_id IS NULL
          AND o.telegram_username IS NOT NULL
          AND LOWER(um.telegram_username) = LOWER(o.telegram_username);
        """
    )

    # 2. Удаляем orphan-коды без user_id (это истёкшие и/или для
    # неизвестных пользователей — они всё равно бесполезны).
    op.execute("DELETE FROM otp_codes WHERE user_id IS NULL;")

    # 3. Разрешаем telegram_username быть NULL (новый bot flow заполняет
    # только user_id, username опционален).
    op.execute("ALTER TABLE otp_codes ALTER COLUMN telegram_username DROP NOT NULL;")

    # 4. Индексы под новый lookup-pattern: по коду (active) и по user_id
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_otp_codes_active_code
        ON otp_codes (code) WHERE used = FALSE;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_otp_codes_user_active
        ON otp_codes (user_id) WHERE used = FALSE;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_otp_codes_user_active;")
    op.execute("DROP INDEX IF EXISTS idx_otp_codes_active_code;")
    # Не делаем ALTER COLUMN ... SET NOT NULL на telegram_username:
    # после upgrade там уже могут появиться NULL-записи от нового bot-flow,
    # и strict downgrade упадёт. Оставляем nullable — downgrade минимален.
