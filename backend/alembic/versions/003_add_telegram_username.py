"""Add telegram_username column to user_main for web OTP lookup

Revision ID: 003_add_telegram_username
Revises: 002_web_tables
Create Date: 2026-04-16
"""
from typing import Sequence, Union
from alembic import op

revision: str = "003_add_telegram_username"
down_revision: Union[str, None] = "002_web_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE user_main
        ADD COLUMN IF NOT EXISTS telegram_username VARCHAR(255);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_main_tg_username
        ON user_main (telegram_username);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_user_main_tg_username;")
    op.execute("ALTER TABLE user_main DROP COLUMN IF EXISTS telegram_username;")
