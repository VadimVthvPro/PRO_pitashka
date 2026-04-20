"""Admin control plane: runtime settings, user tier/ban, post moderation.

Revision ID: 011_admin_control_plane
Revises: 010_chat_feedback
Create Date: 2026-04-15

Three independent extensions, all idempotent:

1. ``app_settings`` — one-row-per-key JSONB store for values the admin must be
   able to rotate at runtime without a redeploy (AI model, retry budgets,
   feature flags, free-tier quotas). ``ai_service`` reads from here with an
   env fallback, so deployments with the table empty continue to work.

2. ``user_main`` gains ``tier``, ``banned_at``, ``ban_reason``, ``ai_disabled``,
   ``social_disabled`` so the admin can scope access without juggling rows in
   an auxiliary table. The three feature flags are NOT NULL + default FALSE so
   existing users keep current behaviour on day one.

3. ``social_posts`` gains ``hidden_at``, ``hidden_reason``, ``pinned_at`` for
   soft-moderation (hide without deleting, pin-to-top). A partial index on
   ``hidden_at IS NULL`` keeps feed queries fast.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "011_admin_control_plane"
down_revision: Union[str, None] = "010_chat_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- app_settings key/value store -------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key         VARCHAR(80) PRIMARY KEY,
            value       JSONB        NOT NULL,
            description VARCHAR(280),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_by  BIGINT
        );
        """
    )

    # ---- user_main permissions -------------------------------------------
    op.execute(
        """
        ALTER TABLE user_main
            ADD COLUMN IF NOT EXISTS tier             VARCHAR(16) NOT NULL DEFAULT 'free',
            ADD COLUMN IF NOT EXISTS banned_at        TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS ban_reason       VARCHAR(280),
            ADD COLUMN IF NOT EXISTS ai_disabled      BOOLEAN     NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS social_disabled  BOOLEAN     NOT NULL DEFAULT FALSE;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'user_main_tier_check'
            ) THEN
                ALTER TABLE user_main
                    ADD CONSTRAINT user_main_tier_check
                    CHECK (tier IN ('free','pro','elite','admin'));
            END IF;
        END $$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_main_tier ON user_main(tier);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_main_banned ON user_main(banned_at) WHERE banned_at IS NOT NULL;")

    # ---- social_posts moderation ------------------------------------------
    op.execute(
        """
        ALTER TABLE social_posts
            ADD COLUMN IF NOT EXISTS hidden_at      TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS hidden_reason  VARCHAR(280),
            ADD COLUMN IF NOT EXISTS pinned_at      TIMESTAMPTZ;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_social_posts_visible "
        "ON social_posts (created_at DESC) WHERE hidden_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_social_posts_pinned "
        "ON social_posts (pinned_at DESC) WHERE pinned_at IS NOT NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_social_posts_pinned;")
    op.execute("DROP INDEX IF EXISTS idx_social_posts_visible;")
    op.execute(
        """
        ALTER TABLE social_posts
            DROP COLUMN IF EXISTS pinned_at,
            DROP COLUMN IF EXISTS hidden_reason,
            DROP COLUMN IF EXISTS hidden_at;
        """
    )
    op.execute("DROP INDEX IF EXISTS idx_user_main_banned;")
    op.execute("DROP INDEX IF EXISTS idx_user_main_tier;")
    op.execute(
        """
        ALTER TABLE user_main
            DROP CONSTRAINT IF EXISTS user_main_tier_check,
            DROP COLUMN IF EXISTS social_disabled,
            DROP COLUMN IF EXISTS ai_disabled,
            DROP COLUMN IF EXISTS ban_reason,
            DROP COLUMN IF EXISTS banned_at,
            DROP COLUMN IF EXISTS tier;
        """
    )
    op.execute("DROP TABLE IF EXISTS app_settings;")
