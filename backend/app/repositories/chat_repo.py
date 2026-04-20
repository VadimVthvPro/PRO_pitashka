"""Persistence helpers for the AI chat history.

Why every method lives here:
  * The router stays free of SQL — easier to reason about auth & error mapping.
  * The admin AI-log viewer reuses the same table; co-locating queries makes it
    obvious when a schema change (e.g. adding ``feedback``/``latency_ms`` in
    revision ``010_chat_feedback``) affects both surfaces.
"""

from __future__ import annotations

import asyncpg


class ChatRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def save_user_message(self, user_id: int, text: str) -> int:
        """Persist the *user* turn and return its id.

        The router needs the id so a follow-up assistant row can be attributed
        to the same dialog turn (used by the admin log to pair them via
        ``LAG()``)."""
        return await self.pool.fetchval(
            """
            INSERT INTO chat_history (user_id, message_type, message_text)
            VALUES ($1, 'user', $2)
            RETURNING id
            """,
            user_id,
            text,
        )

    async def save_assistant_message(
        self,
        user_id: int,
        text: str,
        *,
        attach_kind: str | None = None,
        latency_ms: int | None = None,
        model: str | None = None,
    ) -> int:
        return await self.pool.fetchval(
            """
            INSERT INTO chat_history
                (user_id, message_type, message_text, attach_kind, latency_ms, model)
            VALUES ($1, 'assistant', $2, $3, $4, $5)
            RETURNING id
            """,
            user_id,
            text,
            attach_kind,
            latency_ms,
            model,
        )

    async def set_feedback(self, user_id: int, message_id: int, value: int) -> bool:
        """Update the assistant message's thumb. Returns True on success.

        We re-check ``user_id`` so a malicious client can't rate other users'
        messages, and ``message_type='assistant'`` so the user can't
        accidentally rate their own outgoing message."""
        result = await self.pool.execute(
            """
            UPDATE chat_history
            SET feedback = $1
            WHERE id = $2 AND user_id = $3 AND message_type = 'assistant'
            """,
            value,
            message_id,
            user_id,
        )
        try:
            return int(result.split()[-1]) > 0
        except (ValueError, IndexError):
            return False

    async def delete_last_assistant(self, user_id: int) -> tuple[int | None, str | None]:
        """For /regenerate: drop the most recent assistant reply and return
        the *previous* user message text so the router can re-run the model.

        Atomically deletes the assistant row and returns the user prompt that
        triggered it (the row immediately preceding it in time).
        """
        async with self.pool.acquire() as conn, conn.transaction():
            asst = await conn.fetchrow(
                """
                SELECT id, created_at FROM chat_history
                WHERE user_id = $1 AND message_type = 'assistant'
                ORDER BY created_at DESC LIMIT 1
                """,
                user_id,
            )
            if not asst:
                return None, None
            prev_user = await conn.fetchrow(
                """
                SELECT message_text FROM chat_history
                WHERE user_id = $1 AND message_type = 'user'
                  AND created_at < $2
                ORDER BY created_at DESC LIMIT 1
                """,
                user_id,
                asst["created_at"],
            )
            await conn.execute("DELETE FROM chat_history WHERE id = $1", asst["id"])
            return asst["id"], (prev_user["message_text"] if prev_user else None)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_context(self, user_id: int, limit: int = 20) -> list[dict]:
        """Most recent N messages in chronological order (oldest first)."""
        rows = await self.pool.fetch(
            "SELECT message_type, message_text, created_at FROM chat_history "
            "WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
            user_id, limit,
        )
        return [dict(r) for r in reversed(rows)]

    async def get_history(self, user_id: int, limit: int = 100) -> list[dict]:
        """Full visible chat history for the UI (chronological, oldest first)."""
        rows = await self.pool.fetch(
            """
            SELECT id, message_type, message_text, created_at,
                   feedback, attach_kind
            FROM chat_history
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id, limit,
        )
        return [dict(r) for r in reversed(rows)]

    async def clear_history(self, user_id: int) -> int:
        result = await self.pool.execute(
            "DELETE FROM chat_history WHERE user_id = $1", user_id,
        )
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0

    async def get_user_info_for_ai(self, user_id: int) -> dict:
        user = await self.pool.fetchrow(
            "SELECT user_sex, date_of_birth FROM user_main WHERE user_id = $1", user_id
        )
        health = await self.pool.fetchrow(
            "SELECT imt, weight, height FROM user_health WHERE user_id = $1 ORDER BY date DESC LIMIT 1", user_id
        )
        aims = await self.pool.fetchrow(
            "SELECT user_aim, daily_cal FROM user_aims WHERE user_id = $1", user_id
        )
        return {
            "sex": user["user_sex"] if user else None,
            "date_of_birth": user["date_of_birth"].isoformat() if user and user["date_of_birth"] else None,
            "imt": float(health["imt"]) if health else None,
            "weight": float(health["weight"]) if health else None,
            "height": float(health["height"]) if health else None,
            "aim": aims["user_aim"] if aims else None,
            "daily_cal": float(aims["daily_cal"]) if aims else None,
        }
