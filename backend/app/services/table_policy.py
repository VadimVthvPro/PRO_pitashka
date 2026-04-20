"""Whitelist of fields the admin "Tables" panel is allowed to edit.

We intentionally keep this policy in code (not in the DB) so nobody with
write access to `app_settings` can promote themselves, drop the audit log,
or rewrite chat history. Everything that flows through the generic
row-editor goes through this file first.

Everything NOT listed here is read-only by default — that includes
`audit_log`, `otp_codes`, `web_sessions`, `admin_users`, `chat_history`
(moderated via /ai/message/{id}), and anything the schema can add later.
"""

from __future__ import annotations

from typing import Any

# Columns that can never be edited via the generic tables panel, even on
# whitelisted tables. Some of them have dedicated admin endpoints (ban/tier),
# others are structural (created_at, PKs), others are security-critical.
GLOBAL_FORBIDDEN_COLS: set[str] = {
    "created_at",
    "updated_at",
    "password_hash",
    # user_main: managed via /users/{id}/ban and /users/{id} PATCH, not here
    "banned_at",
    "ban_reason",
    # chat moderation: /ai/message/{id}
    "deleted_at",
}

# Map: table → policy.
#   pk              - primary-key column (used to target a single row)
#   editable        - columns that may be updated via PATCH /tables/.../row
#   read_only       - True for append-only / sensitive tables; nothing is editable
#   label_key       - i18n key for UI hint (optional)
TABLE_POLICY: dict[str, dict[str, Any]] = {
    # --- users & profile ---------------------------------------------------
    "user_main": {
        "pk": "user_id",
        "editable": {
            "user_name", "display_name", "bio", "user_sex", "gender",
            "public_profile", "tier", "is_premium", "social_score",
            "ai_disabled", "social_disabled", "telegram_username",
        },
        "hint_key": "admin_table_hint_user_main",
    },
    "user_health": {
        "pk": "id",
        "editable": {"weight", "height", "age", "activity_coef", "date"},
    },
    "user_aims": {
        "pk": "id",
        "editable": {
            "aim", "coef_aim", "kcal_aim", "protein_aim", "fats_aim",
            "carbs_aim", "water_aim", "date",
        },
    },
    "user_lang": {
        "pk": "user_id",
        "editable": {"lang"},
    },
    "user_settings": {
        "pk": "user_id",
        "editable": {"notify_ai", "notify_social", "units", "theme", "timezone"},
    },
    # --- daily data --------------------------------------------------------
    "food": {
        "pk": "id",
        "editable": {
            "product", "count", "gramms_size", "cal",
            "protein", "fats", "carbs", "date", "time",
        },
    },
    "water": {
        "pk": "id",
        "editable": {"count", "date"},
    },
    "user_training": {
        "pk": "id",
        "editable": {"training_id", "training_cal", "duration_min", "date"},
    },
    "training_types": {
        "pk": "id",
        "editable": {"name_ru", "name_en", "name_de", "name_fr", "name_es"},
    },
    "training_coefficients": {
        "pk": "id",
        "editable": {"coef", "training_id"},
    },
    # --- social ------------------------------------------------------------
    # Hide/pin/delete live in /social/posts; here we allow only content edits.
    "social_posts": {
        "pk": "id",
        "editable": {"title", "body", "tags", "payload"},
        "hint_key": "admin_table_hint_social_posts",
    },
    # --- READ-ONLY TABLES --------------------------------------------------
    "audit_log":     {"pk": "id", "read_only": True},
    "otp_codes":     {"pk": "id", "read_only": True},
    "web_sessions":  {"pk": "id", "read_only": True},
    "admin_users":   {"pk": "id", "read_only": True},
    "chat_history":  {"pk": "id", "read_only": True},
    "social_likes":  {"pk": "id", "read_only": True},
    "social_follows": {"pk": "id", "read_only": True},
    "app_settings":  {"pk": "key", "read_only": True},  # managed via /settings
}


def policy_for(table: str) -> dict[str, Any] | None:
    return TABLE_POLICY.get(table)


def editable_columns(table: str) -> set[str]:
    """Columns the row editor may touch. Forbidden globals are always stripped."""
    p = TABLE_POLICY.get(table)
    if not p or p.get("read_only"):
        return set()
    cols = set(p.get("editable") or ())
    return cols - GLOBAL_FORBIDDEN_COLS


def is_read_only(table: str) -> bool:
    p = TABLE_POLICY.get(table)
    return bool(p and p.get("read_only"))


def pk_of(table: str) -> str | None:
    p = TABLE_POLICY.get(table)
    return p.get("pk") if p else None
