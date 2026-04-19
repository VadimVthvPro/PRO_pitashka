"""Social network: posts, likes, follows, public profile bits.

Revision ID: 006_social
Revises: 005_google_oauth
Create Date: 2026-04-15
"""
from typing import Sequence, Union
from alembic import op

revision: str = "006_social"
down_revision: Union[str, None] = "005_google_oauth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Public profile fields on existing user_main row.
    op.execute(
        """
        ALTER TABLE user_main
            ADD COLUMN IF NOT EXISTS display_name  VARCHAR(64),
            ADD COLUMN IF NOT EXISTS bio           VARCHAR(280),
            ADD COLUMN IF NOT EXISTS gender        VARCHAR(16),
            ADD COLUMN IF NOT EXISTS public_profile BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS social_score  INTEGER NOT NULL DEFAULT 0;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS social_posts (
            id              BIGSERIAL PRIMARY KEY,
            user_id         BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            kind            VARCHAR(16) NOT NULL,
            title           VARCHAR(140),
            body            TEXT NOT NULL,
            tags            TEXT[]       NOT NULL DEFAULT '{}',
            payload         JSONB        NOT NULL DEFAULT '{}'::jsonb,
            likes_count     INTEGER      NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            CHECK (kind IN ('form', 'meal', 'workout'))
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_created ON social_posts (created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_kind    ON social_posts (kind, created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_user    ON social_posts (user_id, created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_social_posts_tags    ON social_posts USING GIN (tags);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS social_likes (
            user_id BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            post_id BIGINT NOT NULL REFERENCES social_posts(id)   ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, post_id)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS social_follows (
            follower_id BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            followee_id BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (follower_id, followee_id),
            CHECK (follower_id <> followee_id)
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS social_follows;")
    op.execute("DROP TABLE IF EXISTS social_likes;")
    op.execute("DROP TABLE IF EXISTS social_posts;")
    op.execute(
        """
        ALTER TABLE user_main
            DROP COLUMN IF EXISTS social_score,
            DROP COLUMN IF EXISTS public_profile,
            DROP COLUMN IF EXISTS gender,
            DROP COLUMN IF EXISTS bio,
            DROP COLUMN IF EXISTS display_name;
        """
    )
