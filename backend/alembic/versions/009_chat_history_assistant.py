"""Allow ``message_type='assistant'`` in chat_history.

Revision ID: 009_chat_history_assistant
Revises: 008_seed_training_types
Create Date: 2026-04-19

The original schema constrained ``chat_history.message_type`` to
``('user', 'bot')`` — but the AI router writes ``'assistant'`` for replies
coming from Gemini, which silently turned every successful chat into a 500
error after the model had already produced a response.

Loosen the constraint to allow ``user``/``assistant``/``bot`` (the latter is
kept for backwards compatibility with rows written by the legacy Telegram
bot pipeline).
"""

from typing import Sequence, Union

from alembic import op


revision: str = "009_chat_history_assistant"
down_revision: Union[str, None] = "008_seed_training_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chat_history
            DROP CONSTRAINT IF EXISTS chat_history_message_type_check;
        ALTER TABLE chat_history
            ADD CONSTRAINT chat_history_message_type_check
            CHECK (message_type IN ('user', 'assistant', 'bot'));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE chat_history SET message_type = 'bot' WHERE message_type = 'assistant';
        ALTER TABLE chat_history
            DROP CONSTRAINT IF EXISTS chat_history_message_type_check;
        ALTER TABLE chat_history
            ADD CONSTRAINT chat_history_message_type_check
            CHECK (message_type IN ('user', 'bot'));
        """
    )
