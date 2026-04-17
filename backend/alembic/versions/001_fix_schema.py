"""Fix legacy schema issues: date_of_birth type, user_sex codes, user_aim codes, water.data rename

Revision ID: 001_fix_schema
Revises: None
Create Date: 2026-04-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_fix_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Fix date_of_birth: VARCHAR -> DATE ---
    op.execute("""
        ALTER TABLE user_main
        ADD COLUMN date_of_birth_new DATE;
    """)
    op.execute("""
        UPDATE user_main
        SET date_of_birth_new = TO_DATE(date_of_birth, 'DD-MM-YYYY')
        WHERE date_of_birth IS NOT NULL
          AND date_of_birth ~ '^\\d{2}-\\d{2}-\\d{4}$';
    """)
    op.execute("ALTER TABLE user_main DROP COLUMN date_of_birth;")
    op.execute("ALTER TABLE user_main RENAME COLUMN date_of_birth_new TO date_of_birth;")

    # --- Fix user_sex: localized text -> M/F code ---
    op.execute("""
        ALTER TABLE user_main
        ADD COLUMN user_sex_code VARCHAR(1);
    """)
    op.execute("""
        UPDATE user_main SET user_sex_code = CASE
            WHEN LOWER(user_sex) IN ('мужчина', 'man', 'homme', 'mann', 'hombre', 'male', 'm') THEN 'M'
            WHEN LOWER(user_sex) IN ('женщина', 'woman', 'femme', 'frau', 'mujer', 'female', 'f') THEN 'F'
            ELSE NULL
        END
        WHERE user_sex IS NOT NULL;
    """)
    op.execute("ALTER TABLE user_main DROP COLUMN user_sex;")
    op.execute("ALTER TABLE user_main RENAME COLUMN user_sex_code TO user_sex;")

    # --- Fix user_aim: localized text -> code ---
    op.execute("""
        ALTER TABLE user_aims
        ADD COLUMN user_aim_code VARCHAR(20);
    """)
    op.execute("""
        UPDATE user_aims SET user_aim_code = CASE
            WHEN LOWER(user_aim) LIKE '%сброс%' OR LOWER(user_aim) LIKE '%loss%'
                 OR LOWER(user_aim) LIKE '%perte%' OR LOWER(user_aim) LIKE '%abnehm%'
                 OR LOWER(user_aim) LIKE '%pérdida%'
            THEN 'weight_loss'
            WHEN LOWER(user_aim) LIKE '%удерж%' OR LOWER(user_aim) LIKE '%maintain%'
                 OR LOWER(user_aim) LIKE '%maintien%' OR LOWER(user_aim) LIKE '%halten%'
                 OR LOWER(user_aim) LIKE '%manten%'
            THEN 'maintain'
            WHEN LOWER(user_aim) LIKE '%набор%' OR LOWER(user_aim) LIKE '%gain%'
                 OR LOWER(user_aim) LIKE '%prise%' OR LOWER(user_aim) LIKE '%zunehm%'
                 OR LOWER(user_aim) LIKE '%ganar%'
            THEN 'weight_gain'
            ELSE 'maintain'
        END
        WHERE user_aim IS NOT NULL;
    """)
    op.execute("ALTER TABLE user_aims DROP COLUMN user_aim;")
    op.execute("ALTER TABLE user_aims RENAME COLUMN user_aim_code TO user_aim;")

    # --- Rename water.data -> water.date ---
    op.execute("ALTER TABLE water RENAME COLUMN data TO date;")


def downgrade() -> None:
    op.execute("ALTER TABLE water RENAME COLUMN date TO data;")

    op.execute("ALTER TABLE user_aims RENAME COLUMN user_aim TO user_aim_code;")
    op.execute("ALTER TABLE user_aims ADD COLUMN user_aim TEXT;")
    op.execute("UPDATE user_aims SET user_aim = user_aim_code;")
    op.execute("ALTER TABLE user_aims DROP COLUMN user_aim_code;")

    op.execute("ALTER TABLE user_main RENAME COLUMN user_sex TO user_sex_code;")
    op.execute("ALTER TABLE user_main ADD COLUMN user_sex TEXT;")
    op.execute("UPDATE user_main SET user_sex = user_sex_code;")
    op.execute("ALTER TABLE user_main DROP COLUMN user_sex_code;")

    op.execute("ALTER TABLE user_main ADD COLUMN date_of_birth_old VARCHAR(20);")
    op.execute("""
        UPDATE user_main
        SET date_of_birth_old = TO_CHAR(date_of_birth, 'DD-MM-YYYY')
        WHERE date_of_birth IS NOT NULL;
    """)
    op.execute("ALTER TABLE user_main DROP COLUMN date_of_birth;")
    op.execute("ALTER TABLE user_main RENAME COLUMN date_of_birth_old TO date_of_birth;")
