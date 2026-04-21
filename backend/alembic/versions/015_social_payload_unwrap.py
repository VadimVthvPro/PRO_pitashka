"""social_posts.payload — unwrap double-encoded jsonb.

Revision ID: 015_social_payload_unwrap
Revises: 014_food_photo_url
Create Date: 2026-04-21

В ранних версиях POST /api/social/posts payload сохранялся как
json.dumps(dict), а asyncpg-codec ещё раз вызывал json.dumps поверх
строки. В итоге в БД попадали double-encoded значения:
    '"{\"photo_url\": \"/uploads/...\"}"'
вместо нормального:
    '{"photo_url": "/uploads/..."}'

Чтение через `dict(row["payload"])` в routers/social.py::_post_row
падало с ValueError → GET /api/social/feed возвращал 500.

Фикс кода (коммит с этой миграцией) убрал лишний json.dumps в
write-path + добавил `_coerce_payload` в read-path. Эта миграция
распаковывает уже сохранённые записи на уровне БД: если jsonb-
значение — строка, достаём её содержимое и парсим обратно как jsonb.

Запрос идемпотентен: после распаковки jsonb_typeof(payload) = 'object'
и повторный прогон не затронет ни одной строки.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "015_social_payload_unwrap"
down_revision: Union[str, None] = "014_food_photo_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE social_posts
        SET payload = (payload #>> '{}')::jsonb
        WHERE jsonb_typeof(payload) = 'string'
        """
    )


def downgrade() -> None:
    # Обратный путь — снова завернуть dict в строку — разрушит клиентов.
    # Downgrade не поддерживается: миграция исправляет корректность данных,
    # откатывать нечего.
    pass
