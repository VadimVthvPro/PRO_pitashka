"""Add feedback + lightweight metadata to chat_history.

Revision ID: 010_chat_feedback
Revises: 009_chat_history_assistant
Create Date: 2026-04-19

* `feedback` — three-way thumbs (up / down / null) on assistant replies, used
  by the redesigned AI chat to capture quality signal and surface it in the
  admin AI-log viewer.
* `attach_kind` — which plan (if any) was attached to the user message that
  produced this reply. Lets us answer "do meal-plan-attached chats land
  better?" without log-spelunking.
* `latency_ms` — round-trip from request entry to Gemini response, so the
  admin dashboard can show "median answer time" without parsing audit_log.
* `model` — which Gemini variant produced the reply (we will switch models
  again, and you want to know *which one* the user thumbed-down).

All columns are nullable: every existing row keeps working unchanged.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "010_chat_feedback"
down_revision: Union[str, None] = "009_chat_history_assistant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chat_history
            ADD COLUMN IF NOT EXISTS feedback     SMALLINT,
            ADD COLUMN IF NOT EXISTS attach_kind  VARCHAR(32),
            ADD COLUMN IF NOT EXISTS latency_ms   INTEGER,
            ADD COLUMN IF NOT EXISTS model        VARCHAR(64);

        ALTER TABLE chat_history
            DROP CONSTRAINT IF EXISTS chat_history_feedback_check;
        ALTER TABLE chat_history
            ADD CONSTRAINT chat_history_feedback_check
            CHECK (feedback IS NULL OR feedback IN (-1, 0, 1));

        CREATE INDEX IF NOT EXISTS idx_chat_history_feedback
            ON chat_history (feedback)
            WHERE feedback IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_chat_history_created_desc
            ON chat_history (created_at DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_chat_history_created_desc;
        DROP INDEX IF EXISTS idx_chat_history_feedback;
        ALTER TABLE chat_history DROP CONSTRAINT IF EXISTS chat_history_feedback_check;
        ALTER TABLE chat_history
            DROP COLUMN IF EXISTS model,
            DROP COLUMN IF EXISTS latency_ms,
            DROP COLUMN IF EXISTS attach_kind,
            DROP COLUMN IF EXISTS feedback;
        """
    )
