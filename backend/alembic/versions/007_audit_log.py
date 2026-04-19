"""Universal audit log of every meaningful API operation.

Revision ID: 007_audit_log
Revises: 006_social
Create Date: 2026-04-15
"""
from typing import Sequence, Union
from alembic import op

revision: str = "007_audit_log"
down_revision: Union[str, None] = "006_social"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id          BIGSERIAL PRIMARY KEY,
            user_id     BIGINT NULL,
            method      VARCHAR(8)  NOT NULL,
            path        TEXT        NOT NULL,
            category    VARCHAR(32) NOT NULL,
            status_code INTEGER     NOT NULL,
            duration_ms INTEGER     NOT NULL,
            ip          INET        NULL,
            user_agent  TEXT        NULL,
            detail      JSONB       NOT NULL DEFAULT '{}'::jsonb,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_created  ON audit_log (created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_user     ON audit_log (user_id, created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_log (category, created_at DESC);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log;")
