import asyncpg


class AdminRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def list_tables(self) -> list[str]:
        rows = await self.pool.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name"
        )
        return [r["table_name"] for r in rows]

    async def get_table_columns(self, table_name: str) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = $1 ORDER BY ordinal_position",
            table_name,
        )
        return [dict(r) for r in rows]

    async def get_rows(self, table_name: str, limit: int = 50, offset: int = 0) -> list[dict]:
        rows = await self.pool.fetch(
            f'SELECT * FROM "{table_name}" LIMIT $1 OFFSET $2',
            limit, offset,
        )
        return [dict(r) for r in rows]

    async def count_rows(self, table_name: str) -> int:
        row = await self.pool.fetchrow(f'SELECT COUNT(*) as cnt FROM "{table_name}"')
        return int(row["cnt"])

    async def delete_row(self, table_name: str, pk_column: str, pk_value) -> bool:
        result = await self.pool.execute(
            f'DELETE FROM "{table_name}" WHERE "{pk_column}" = $1', pk_value
        )
        return result != "DELETE 0"

    async def get_row(
        self, table_name: str, pk_column: str, pk_value
    ) -> dict | None:
        """Fetch a single row by primary key; returns None if missing.

        Used by the admin row-editor before PATCH to compute a diff and
        render the form with current values.
        """
        row = await self.pool.fetchrow(
            f'SELECT * FROM "{table_name}" WHERE "{pk_column}" = $1 LIMIT 1',
            pk_value,
        )
        return dict(row) if row else None

    async def update_row(
        self,
        table_name: str,
        pk_column: str,
        pk_value,
        set_map: dict[str, object],
    ) -> dict | None:
        """Apply a SET of column=value pairs on exactly one row.

        Column names in ``set_map`` MUST already be validated against the
        editor whitelist by the router — this layer trusts the caller for
        column identity and only handles parameterised value binding.
        Returns the updated row or None if nothing matched.
        """
        if not set_map:
            return await self.get_row(table_name, pk_column, pk_value)

        cols = list(set_map.keys())
        set_sql = ", ".join(f'"{c}" = ${i + 1}' for i, c in enumerate(cols))
        pk_param = f"${len(cols) + 1}"
        sql = (
            f'UPDATE "{table_name}" SET {set_sql} '
            f'WHERE "{pk_column}" = {pk_param} RETURNING *'
        )
        row = await self.pool.fetchrow(sql, *set_map.values(), pk_value)
        return dict(row) if row else None
