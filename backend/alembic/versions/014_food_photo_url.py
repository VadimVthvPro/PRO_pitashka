"""food.photo_url — сохраняем превью распознанной тарелки.

Revision ID: 014_food_photo_url
Revises: 013_user_plans
Create Date: 2026-04-21

Раньше фото еды жило в памяти backend'а ровно до конца запроса: байты
попадали в Gemini и там же умирали. Теперь перед распознаванием сохраняем
jpeg в `UPLOADS_DIR/food/{user_id}/{uuid}.jpg` и пишем публичный URL в
`food.photo_url`. Так лента дня рендерит миниатюры без повторного запроса
в AI и без хранения base64 в БД.

Колонка nullable — для ручных записей и старых строк URL'а нет.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "014_food_photo_url"
down_revision: Union[str, None] = "013_user_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE food ADD COLUMN IF NOT EXISTS photo_url TEXT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE food DROP COLUMN IF EXISTS photo_url")
