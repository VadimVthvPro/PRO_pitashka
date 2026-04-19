"""Add Google OAuth identity links to user_main.

Revision ID: 005_google_oauth
Revises: 004_streaks_badges
Create Date: 2026-04-15
"""
from typing import Sequence, Union
from alembic import op

revision: str = "005_google_oauth"
down_revision: Union[str, None] = "004_streaks_badges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE user_main
            ADD COLUMN IF NOT EXISTS google_sub      VARCHAR(64),
            ADD COLUMN IF NOT EXISTS google_email    VARCHAR(255),
            ADD COLUMN IF NOT EXISTS google_picture  TEXT,
            ADD COLUMN IF NOT EXISTS google_linked_at TIMESTAMPTZ;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_main_google_sub
        ON user_main (google_sub) WHERE google_sub IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_main_google_email
        ON user_main (LOWER(google_email)) WHERE google_email IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_user_main_google_email;")
    op.execute("DROP INDEX IF EXISTS idx_user_main_google_sub;")
    op.execute(
        """
        ALTER TABLE user_main
            DROP COLUMN IF EXISTS google_linked_at,
            DROP COLUMN IF EXISTS google_picture,
            DROP COLUMN IF EXISTS google_email,
            DROP COLUMN IF EXISTS google_sub;
        """
    )
