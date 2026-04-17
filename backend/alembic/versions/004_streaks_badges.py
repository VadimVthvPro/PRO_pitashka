"""Add streaks and achievement badges

Revision ID: 004_streaks_badges
Revises: 003_add_telegram_username
Create Date: 2026-04-15
"""
from typing import Sequence, Union
from alembic import op

revision: str = "004_streaks_badges"
down_revision: Union[str, None] = "003_add_telegram_username"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_streaks (
            user_id BIGINT PRIMARY KEY REFERENCES user_main(user_id) ON DELETE CASCADE,
            current_streak INT NOT NULL DEFAULT 0,
            longest_streak INT NOT NULL DEFAULT 0,
            last_active_date DATE,
            freezes_available INT NOT NULL DEFAULT 1,
            last_freeze_reset DATE,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_user_streaks_last_active
            ON user_streaks (last_active_date);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS badges (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) UNIQUE NOT NULL,
            title VARCHAR(128) NOT NULL,
            description TEXT NOT NULL,
            icon VARCHAR(128) NOT NULL,
            tier VARCHAR(16) NOT NULL,
            category VARCHAR(32) NOT NULL,
            sort_order INT NOT NULL DEFAULT 0
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_badges (
            user_id BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
            badge_id INT NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
            earned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, badge_id)
        );
        CREATE INDEX IF NOT EXISTS idx_user_badges_earned
            ON user_badges (user_id, earned_at DESC);
    """)

    op.execute("""
        INSERT INTO badges (code, title, description, icon, tier, category, sort_order) VALUES
            ('streak_3',     'Три дня подряд',   'Три активных дня кряду',                          'solar:flame-bold-duotone',       'bronze', 'streak', 10),
            ('streak_7',     'Неделя стали',     'Семь дней без пропусков',                          'solar:flame-bold-duotone',       'silver', 'streak', 20),
            ('streak_30',    'Месяц характера',  'Тридцать дней подряд. Это уже привычка',            'solar:flame-bold-duotone',       'gold',   'streak', 30),
            ('streak_100',   '100 дней',          'Сто дней активности',                              'solar:crown-star-bold-duotone',  'legend', 'streak', 40),
            ('water_first',  'Первый глоток',    'Первый стакан воды вообще',                        'solar:cup-bold-duotone',         'bronze', 'water',  110),
            ('water_goal',   'Ровно 8',          'Выпил дневную норму',                              'solar:cup-bold-duotone',         'silver', 'water',  120),
            ('water_7',      'Гидромаст',         'Норма воды 7 дней подряд',                         'solar:cup-star-bold-duotone',    'gold',   'water',  130),
            ('food_first',   'Первая тарелка',   'Первое добавление еды',                            'solar:plate-bold-duotone',       'bronze', 'food',   210),
            ('food_balance', 'Балансист',         'БЖУ в пределах ±10% от цели за день',              'solar:plate-bold-duotone',       'silver', 'food',   220),
            ('workout_first','Разогрев',          'Первая тренировка в дневнике',                     'solar:dumbbell-large-bold-duotone','bronze','workout',310),
            ('workout_5wk',  'Марафонец',         'Пять тренировок за календарную неделю',            'solar:running-bold-duotone',     'gold',   'workout',320),
            ('ai_10',        'Любопытный',        'Задал AI десять вопросов',                         'solar:magic-stick-3-bold-duotone','silver','ai',     410)
        ON CONFLICT (code) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_badges;")
    op.execute("DROP TABLE IF EXISTS badges;")
    op.execute("DROP TABLE IF EXISTS user_streaks;")
