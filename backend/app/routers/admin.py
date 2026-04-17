from fastapi import APIRouter, HTTPException, Query
from app.dependencies import DbDep, CurrentUserDep
from app.repositories.admin_repo import AdminRepository

router = APIRouter()

ALLOWED_TABLES = {
    "user_main", "user_lang", "user_health", "user_aims",
    "food", "water", "user_training", "training_types",
    "training_coefficients", "chat_history", "admin_users",
    "web_sessions", "otp_codes", "user_settings",
}


async def _check_admin(user_id: int, db) -> None:
    row = await db.fetchrow(
        "SELECT id FROM admin_users au "
        "JOIN user_main um ON LOWER(au.username) = um.telegram_username "
        "WHERE um.user_id = $1",
        user_id,
    )
    if not row:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/tables")
async def list_tables(user_id: CurrentUserDep, db: DbDep):
    await _check_admin(user_id, db)
    repo = AdminRepository(db)
    tables = await repo.list_tables()
    return {"tables": [t for t in tables if t in ALLOWED_TABLES]}


@router.get("/tables/{table_name}")
async def get_table_data(
    table_name: str, user_id: CurrentUserDep, db: DbDep,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
):
    await _check_admin(user_id, db)
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    repo = AdminRepository(db)
    columns = await repo.get_table_columns(table_name)
    offset = (page - 1) * per_page
    rows = await repo.get_rows(table_name, per_page, offset)
    total = await repo.count_rows(table_name)
    return {
        "columns": columns,
        "rows": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.delete("/tables/{table_name}/{pk_column}/{pk_value}")
async def delete_row(table_name: str, pk_column: str, pk_value: str, user_id: CurrentUserDep, db: DbDep):
    await _check_admin(user_id, db)
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    repo = AdminRepository(db)

    columns = await repo.get_table_columns(table_name)
    valid_columns = {c["column_name"] for c in columns}
    if pk_column not in valid_columns:
        raise HTTPException(status_code=400, detail=f"Invalid column: {pk_column}")

    try:
        typed_value: int | str = int(pk_value)
    except ValueError:
        typed_value = pk_value

    deleted = await repo.delete_row(table_name, pk_column, typed_value)
    if not deleted:
        raise HTTPException(status_code=404, detail="Row not found")
    return {"message": "Deleted"}
