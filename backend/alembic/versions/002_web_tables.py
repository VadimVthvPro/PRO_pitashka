"""Add web_sessions and otp_codes tables for web auth

Revision ID: 002_web_tables
Revises: 001_fix_schema
Create Date: 2026-04-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_web_tables"
down_revision: Union[str, None] = "001_fix_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS otp_codes (
            id BIGSERIAL PRIMARY KEY,
            telegram_username VARCHAR(255) NOT NULL,
            user_id BIGINT,
            code VARCHAR(6) NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_otp_codes_username ON otp_codes (telegram_username, used);
        CREATE INDEX IF NOT EXISTS idx_otp_codes_expires ON otp_codes (expires_at);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS web_sessions (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            token_hash VARCHAR(128) NOT NULL UNIQUE,
            refresh_token_hash VARCHAR(128) NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            user_agent TEXT,
            ip_address VARCHAR(45)
        );
        CREATE INDEX IF NOT EXISTS idx_web_sessions_user ON web_sessions (user_id);
        CREATE INDEX IF NOT EXISTS idx_web_sessions_token ON web_sessions (token_hash);
        CREATE INDEX IF NOT EXISTS idx_web_sessions_refresh ON web_sessions (refresh_token_hash);
        CREATE INDEX IF NOT EXISTS idx_web_sessions_expires ON web_sessions (expires_at);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id BIGINT PRIMARY KEY REFERENCES user_main(user_id) ON DELETE CASCADE,
            theme VARCHAR(10) DEFAULT 'auto',
            notifications_enabled BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_settings;")
    op.execute("DROP TABLE IF EXISTS web_sessions;")
    op.execute("DROP TABLE IF EXISTS otp_codes;")
