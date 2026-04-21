"""OAuth providers (Yandex, VK) + synthetic user_id sequence.

Revision ID: 016_oauth_providers
Revises: 015_social_payload_unwrap
Create Date: 2026-04-21

### Что добавляет миграция

1. Колонки `yandex_*` и `vk_*` в `user_main` — по аналогии с тем, что уже
   сделано для Google в миграции 005. Все NULLABLE, с partial unique
   индексами по `*_sub`, чтобы один внешний аккаунт нельзя было
   привязать к двум user_main-записям.

2. Sequence `user_main_synth_id_seq` для *синтетических* user_id. До этой
   миграции `user_main.user_id` = Telegram user id (примерно 10^9–10^10).
   После — пользователи, зарегистрировавшиеся без Telegram (через Google,
   Yandex, VK), получают id из sequence, стартующей с 10_000_000_000_000
   (10^13) — это на три порядка выше максимального возможного Telegram
   id в ближайшие десятилетия, поэтому коллизии исключены.

3. Никакого ALTER TYPE / DROP — миграция полностью аддитивна, откатить
   безопасно.

### Почему отдельные колонки вместо таблицы `user_identities`

Существующий Google-дизайн уже использует плоские колонки `google_sub`,
`google_email`, `google_linked_at`. Сохраняю тот же подход для единства,
это проще в SQL и понятнее в UI («привязать / отвязать» для каждого
провайдера без JOIN). Для пяти провайдеров это ещё приемлемо; если мы
когда-нибудь дойдём до десяти — стоит рефакторить в `user_identities`.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "016_oauth_providers"
down_revision: Union[str, None] = "015_social_payload_unwrap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Yandex ID ---
    op.execute(
        """
        ALTER TABLE user_main
            ADD COLUMN IF NOT EXISTS yandex_sub        VARCHAR(64),
            ADD COLUMN IF NOT EXISTS yandex_email      VARCHAR(255),
            ADD COLUMN IF NOT EXISTS yandex_login      VARCHAR(128),
            ADD COLUMN IF NOT EXISTS yandex_avatar_id  VARCHAR(128),
            ADD COLUMN IF NOT EXISTS yandex_linked_at  TIMESTAMPTZ;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_main_yandex_sub
        ON user_main (yandex_sub) WHERE yandex_sub IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_main_yandex_email
        ON user_main (LOWER(yandex_email)) WHERE yandex_email IS NOT NULL;
        """
    )

    # --- VK ID ---
    op.execute(
        """
        ALTER TABLE user_main
            ADD COLUMN IF NOT EXISTS vk_sub         VARCHAR(32),
            ADD COLUMN IF NOT EXISTS vk_email       VARCHAR(255),
            ADD COLUMN IF NOT EXISTS vk_first_name  VARCHAR(128),
            ADD COLUMN IF NOT EXISTS vk_last_name   VARCHAR(128),
            ADD COLUMN IF NOT EXISTS vk_photo_url   TEXT,
            ADD COLUMN IF NOT EXISTS vk_linked_at   TIMESTAMPTZ;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_main_vk_sub
        ON user_main (vk_sub) WHERE vk_sub IS NOT NULL;
        """
    )

    # --- Synthetic user_id sequence ---
    # Start с 10^13. Реальные Telegram user_id на 2026 год — около 8·10^9
    # и растут на ~5·10^8 в год (см. https://core.telegram.org/bots/api).
    # Зазор в 1000× гарантирует, что sequence ни при каких условиях не
    # столкнётся с реальными TG-id в нашей жизни.
    op.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS user_main_synth_id_seq
            AS BIGINT
            START WITH 10000000000000
            MINVALUE 10000000000000
            INCREMENT BY 1
            NO CYCLE;
        """
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS user_main_synth_id_seq;")

    op.execute("DROP INDEX IF EXISTS idx_user_main_vk_sub;")
    op.execute(
        """
        ALTER TABLE user_main
            DROP COLUMN IF EXISTS vk_linked_at,
            DROP COLUMN IF EXISTS vk_photo_url,
            DROP COLUMN IF EXISTS vk_last_name,
            DROP COLUMN IF EXISTS vk_first_name,
            DROP COLUMN IF EXISTS vk_email,
            DROP COLUMN IF EXISTS vk_sub;
        """
    )

    op.execute("DROP INDEX IF EXISTS idx_user_main_yandex_email;")
    op.execute("DROP INDEX IF EXISTS idx_user_main_yandex_sub;")
    op.execute(
        """
        ALTER TABLE user_main
            DROP COLUMN IF EXISTS yandex_linked_at,
            DROP COLUMN IF EXISTS yandex_avatar_id,
            DROP COLUMN IF EXISTS yandex_login,
            DROP COLUMN IF EXISTS yandex_email,
            DROP COLUMN IF EXISTS yandex_sub;
        """
    )
