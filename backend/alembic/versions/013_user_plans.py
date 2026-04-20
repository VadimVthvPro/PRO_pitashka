"""user_plans — история сгенерированных AI-планов (питание / тренировки).

Revision ID: 013_user_plans
Revises: 012_freemium
Create Date: 2026-04-21

Раньше планы хранились ТОЛЬКО в Redis с TTL → исчезали при перезапуске и
терялись после квотных-ошибок (`.set()` не вызывался → старый кеш истекал
без замены). Юзер видел "план пропал".

Эта миграция добавляет персистентную историю: каждая успешная генерация
INSERT'ится в `user_plans`. Фронт показывает последние N как историю и
позволяет вернуть любой из них активным.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "013_user_plans"
down_revision: Union[str, None] = "012_freemium"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_plans (
            id          BIGSERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            kind        TEXT NOT NULL CHECK (kind IN ('meal', 'workout')),
            content     TEXT NOT NULL,
            lang        TEXT NOT NULL DEFAULT 'ru',
            model       TEXT,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    # Поиск истории по юзеру + типу. Самый частый query.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_plans_user_kind_created "
        "ON user_plans (user_id, kind, created_at DESC)"
    )
    # Уникальность активного плана по user+kind держим частичным индексом —
    # при INSERT новой "active" сначала сбрасываем флаг у старых.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_user_plans_active "
        "ON user_plans (user_id, kind) WHERE is_active = TRUE"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_plans")
