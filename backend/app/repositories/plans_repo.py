"""DB-доступ к таблице `user_plans` — истории AI-планов питания/тренировок.

Хранит персистентную историю генераций. В каждый момент у юзера может быть
максимум один активный план каждого типа (`is_active = TRUE`), это требование
обеспечивается частичным уникальным индексом — `set_active` атомарно
сбрасывает флаг у предыдущих и ставит новый.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

import asyncpg


PlanKind = Literal["meal", "workout"]


class PlansRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def insert_active(
        self,
        *,
        user_id: int,
        kind: PlanKind,
        content: str,
        lang: str,
        model: str | None,
    ) -> dict[str, Any]:
        """Сохраняет новый план и помечает его активным.

        Атомарно: сначала снимаем флаг с прошлого активного, потом INSERT'им
        новый — это не даёт частичному уникальному индексу `ux_user_plans_active`
        сработать.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE user_plans
                       SET is_active = FALSE
                     WHERE user_id = $1 AND kind = $2 AND is_active = TRUE
                    """,
                    user_id, kind,
                )
                row = await conn.fetchrow(
                    """
                    INSERT INTO user_plans (user_id, kind, content, lang, model, is_active)
                    VALUES ($1, $2, $3, $4, $5, TRUE)
                    RETURNING id, user_id, kind, content, lang, model, is_active, created_at
                    """,
                    user_id, kind, content, lang, model,
                )
        return dict(row)

    async def get_active(
        self, user_id: int, kind: PlanKind
    ) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT id, user_id, kind, content, lang, model, is_active, created_at
              FROM user_plans
             WHERE user_id = $1 AND kind = $2 AND is_active = TRUE
             LIMIT 1
            """,
            user_id, kind,
        )
        return dict(row) if row else None

    async def list_history(
        self, user_id: int, kind: PlanKind, *, limit: int = 20
    ) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT id, kind, lang, model, is_active, created_at,
                   LEFT(content, 320) AS preview,
                   OCTET_LENGTH(content) AS size_bytes
              FROM user_plans
             WHERE user_id = $1 AND kind = $2
             ORDER BY created_at DESC
             LIMIT $3
            """,
            user_id, kind, limit,
        )
        return [dict(r) for r in rows]

    async def get_by_id(self, user_id: int, plan_id: int) -> dict[str, Any] | None:
        row = await self.pool.fetchrow(
            """
            SELECT id, user_id, kind, content, lang, model, is_active, created_at
              FROM user_plans
             WHERE id = $1 AND user_id = $2
            """,
            plan_id, user_id,
        )
        return dict(row) if row else None

    async def set_active(
        self, user_id: int, plan_id: int
    ) -> dict[str, Any] | None:
        """Делает указанный план активным (для его kind), снимая флаг со старого."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                target = await conn.fetchrow(
                    "SELECT id, kind FROM user_plans WHERE id = $1 AND user_id = $2",
                    plan_id, user_id,
                )
                if not target:
                    return None
                await conn.execute(
                    """
                    UPDATE user_plans
                       SET is_active = FALSE
                     WHERE user_id = $1 AND kind = $2 AND is_active = TRUE
                    """,
                    user_id, target["kind"],
                )
                row = await conn.fetchrow(
                    """
                    UPDATE user_plans
                       SET is_active = TRUE
                     WHERE id = $1
                     RETURNING id, user_id, kind, content, lang, model, is_active, created_at
                    """,
                    plan_id,
                )
        return dict(row) if row else None

    async def delete(self, user_id: int, plan_id: int) -> bool:
        result = await self.pool.execute(
            "DELETE FROM user_plans WHERE id = $1 AND user_id = $2",
            plan_id, user_id,
        )
        # asyncpg возвращает строку формата 'DELETE N'.
        return result.endswith(" 1")

    async def count(self, user_id: int, kind: PlanKind) -> int:
        return int(await self.pool.fetchval(
            "SELECT COUNT(*) FROM user_plans WHERE user_id = $1 AND kind = $2",
            user_id, kind,
        ) or 0)


__all__ = ["PlansRepository", "PlanKind"]
