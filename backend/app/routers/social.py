"""Social network: feed, likes, follows, leaderboard, photo uploads."""

from __future__ import annotations

import io
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile

logger = logging.getLogger(__name__)

from app.dependencies import CurrentUserDep, DbDep

router = APIRouter()

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "/data/uploads"))
SOCIAL_PHOTO_DIR = UPLOADS_DIR / "social"
MAX_PHOTO_BYTES = 6 * 1024 * 1024  # 6 MB
ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}

VALID_KINDS = {"form", "meal", "workout"}
MAX_TAGS = 6
MAX_BODY = 4000
MAX_TITLE = 140


def _normalize_tags(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for t in raw:
        t = (t or "").strip().lower().lstrip("#")
        if not t:
            continue
        if len(t) > 24:
            t = t[:24]
        if t not in out:
            out.append(t)
        if len(out) >= MAX_TAGS:
            break
    return out


def _coerce_payload(raw: Any) -> dict[str, Any]:
    """Payload в БД исторически мог быть double-encoded JSON (сохранён как
    ``"{\"photo_url\":...}"`` вместо ``{"photo_url":...}``). Причина — баг
    в ранних версиях ``POST /posts``, где ``json.dumps`` вызывался поверх
    уже настроенного asyncpg jsonb codec. Миграция
    ``alembic/versions/015_social_payload_unwrap.py`` распаковывает их
    на уровне БД, но этот хелпер остаётся последней линией обороны на
    случай ручных инсертов, старых реплик или повторного проявления бага.

    Логика:
      * ``None``/``{}`` → ``{}``.
      * ``dict`` (ожидаемый случай после codec) → возвращается как есть.
      * ``str`` (double-encoded) → пытаемся ``json.loads`` до тех пор,
        пока не получим dict, максимум 3 итерации (параноиковый loop).
      * Всё остальное → пустой dict, с warning в логи.
    """
    if raw is None or raw == "":
        return {}
    value = raw
    for _ in range(3):
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                value = json.loads(value)
                continue
            except (TypeError, ValueError):
                break
        break
    logger.warning("social_posts.payload has unexpected shape: %r", raw)
    return {}


async def _post_row(db, user_id: int, row) -> dict[str, Any]:
    """Convert asyncpg Record to API dict, including liked_by_me flag."""
    liked = await db.fetchval(
        "SELECT 1 FROM social_likes WHERE user_id = $1 AND post_id = $2",
        user_id, row["id"],
    )
    author = await db.fetchrow(
        """
        SELECT user_id, COALESCE(display_name, user_name, telegram_username, 'user') AS name,
               telegram_username, gender, social_score
        FROM user_main WHERE user_id = $1
        """,
        row["user_id"],
    )
    return {
        "id": row["id"],
        "kind": row["kind"],
        "title": row["title"],
        "body": row["body"],
        "tags": list(row["tags"] or []),
        "payload": _coerce_payload(row["payload"]),
        "likes_count": row["likes_count"],
        "liked_by_me": bool(liked),
        "created_at": row["created_at"].isoformat(),
        "author": {
            "user_id": author["user_id"],
            "name": author["name"],
            "telegram_username": author["telegram_username"],
            "gender": author["gender"],
            "score": author["social_score"],
        } if author else None,
    }


@router.get("/feed")
async def feed(
    user_id: CurrentUserDep,
    db: DbDep,
    kind: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    author: Optional[int] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    # Admin-hidden posts never appear in the public feed. Pinned posts bubble
    # up to the top regardless of their created_at timestamp.
    where = ["hidden_at IS NULL"]
    args: list[Any] = []
    if kind:
        if kind not in VALID_KINDS:
            raise HTTPException(status_code=400, detail="invalid kind")
        args.append(kind)
        where.append(f"kind = ${len(args)}")
    if tag:
        args.append(tag.lower().lstrip("#"))
        where.append(f"${len(args)} = ANY(tags)")
    if author:
        args.append(author)
        where.append(f"user_id = ${len(args)}")
    where_sql = "WHERE " + " AND ".join(where)
    args.extend([limit, offset])
    rows = await db.fetch(
        f"""
        SELECT id, user_id, kind, title, body, tags, payload, likes_count, created_at
        FROM social_posts
        {where_sql}
        ORDER BY (pinned_at IS NOT NULL) DESC,
                 COALESCE(pinned_at, created_at) DESC
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    return {"items": [await _post_row(db, user_id, r) for r in rows]}


@router.post("/posts")
async def create_post(
    user_id: CurrentUserDep,
    db: DbDep,
    body: dict = Body(...),
):
    kind = (body.get("kind") or "").strip().lower()
    if kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail="kind must be form|meal|workout")

    text = (body.get("body") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="body is required")
    if len(text) > MAX_BODY:
        raise HTTPException(status_code=400, detail=f"body too long (>{MAX_BODY})")

    title = (body.get("title") or "").strip()[:MAX_TITLE] or None
    tags = _normalize_tags(body.get("tags"))
    payload = body.get("payload") or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")

    # Hard guardrails: banned or social-disabled users can't post; and the
    # admin can flip a global kill-switch for social posting via runtime
    # settings (useful during incident response).
    perms = await db.fetchrow(
        "SELECT banned_at, social_disabled FROM user_main WHERE user_id = $1",
        user_id,
    )
    if perms and perms["banned_at"] is not None:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован администрацией")
    if perms and perms["social_disabled"]:
        raise HTTPException(status_code=403, detail="Публикации отключены для этого аккаунта")
    from app.services.runtime_settings import get_setting as _get_setting
    if not bool(await _get_setting("social_posting_enabled")):
        raise HTTPException(status_code=503, detail="Публикация временно недоступна")

    # jsonb codec из app/database.py сам сериализует dict через json.dumps —
    # передавать сюда json-строку нельзя, иначе она encode-нётся ВТОРОЙ раз
    # и в БД попадёт '"{\"photo_url\":...}"' (см. migration 015).
    row = await db.fetchrow(
        """
        INSERT INTO social_posts (user_id, kind, title, body, tags, payload)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING id, user_id, kind, title, body, tags, payload, likes_count, created_at
        """,
        user_id, kind, title, text, tags, payload,
    )
    await db.execute(
        "UPDATE user_main SET social_score = social_score + 2 WHERE user_id = $1",
        user_id,
    )
    return await _post_row(db, user_id, row)


@router.post("/posts/photo")
async def upload_post_photo(
    user_id: CurrentUserDep,
    file: UploadFile = File(...),
):
    """Upload a photo for a social post and return its public URL.

    The frontend calls this BEFORE creating the post, then puts the returned
    URL into ``payload.photo_url`` of the create-post request. This keeps the
    post-creation endpoint pure-JSON (so we don't need multipart there) and
    lets the user retry uploads independently of the post text.
    """
    ctype = (file.content_type or "").lower()
    if ctype not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Поддерживаются только JPEG, PNG и WebP",
        )

    raw = await file.read()
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс. 6 МБ)")
    if len(raw) < 64:
        raise HTTPException(status_code=400, detail="Файл пустой или повреждён")

    try:
        from PIL import Image, ImageOps  # local import: heavy
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        # Strip EXIF, normalise to RGB, downscale long side to 1600 px so we
        # don't ship 12-MP phone shots to every viewer.
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        max_side = 1600
        if max(img.size) > max_side:
            ratio = max_side / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        out_buf = io.BytesIO()
        img.convert("RGB").save(out_buf, format="JPEG", quality=85, optimize=True)
        out_bytes = out_buf.getvalue()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Не удалось обработать изображение: {exc}")

    user_dir = SOCIAL_PHOTO_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_urlsafe(12)}.jpg"
    path = user_dir / name
    path.write_bytes(out_bytes)

    public_url = f"/uploads/social/{user_id}/{name}"
    return {"url": public_url, "size": len(out_bytes), "width": img.size[0], "height": img.size[1]}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: int, user_id: CurrentUserDep, db: DbDep):
    row = await db.fetchrow("SELECT user_id FROM social_posts WHERE id = $1", post_id)
    if not row:
        raise HTTPException(status_code=404, detail="post not found")
    if row["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="not your post")
    await db.execute("DELETE FROM social_posts WHERE id = $1", post_id)
    return {"deleted": True}


@router.post("/posts/{post_id}/like")
async def toggle_like(post_id: int, user_id: CurrentUserDep, db: DbDep):
    exists = await db.fetchval(
        "SELECT 1 FROM social_likes WHERE user_id = $1 AND post_id = $2",
        user_id, post_id,
    )
    if exists:
        await db.execute(
            "DELETE FROM social_likes WHERE user_id = $1 AND post_id = $2",
            user_id, post_id,
        )
        await db.execute(
            "UPDATE social_posts SET likes_count = GREATEST(likes_count - 1, 0) WHERE id = $1",
            post_id,
        )
        liked = False
    else:
        # The post must exist; otherwise FK insert will raise — surface as 404.
        try:
            await db.execute(
                "INSERT INTO social_likes (user_id, post_id) VALUES ($1, $2)",
                user_id, post_id,
            )
        except Exception:
            raise HTTPException(status_code=404, detail="post not found")
        await db.execute(
            "UPDATE social_posts SET likes_count = likes_count + 1 WHERE id = $1",
            post_id,
        )
        author_id = await db.fetchval(
            "SELECT user_id FROM social_posts WHERE id = $1", post_id,
        )
        if author_id and author_id != user_id:
            await db.execute(
                "UPDATE user_main SET social_score = social_score + 1 WHERE user_id = $1",
                author_id,
            )
        liked = True
    count = await db.fetchval("SELECT likes_count FROM social_posts WHERE id = $1", post_id) or 0
    return {"liked": liked, "likes_count": int(count)}


@router.post("/follow/{target_id}")
async def toggle_follow(target_id: int, user_id: CurrentUserDep, db: DbDep):
    if target_id == user_id:
        raise HTTPException(status_code=400, detail="can't follow yourself")
    exists = await db.fetchval(
        "SELECT 1 FROM social_follows WHERE follower_id = $1 AND followee_id = $2",
        user_id, target_id,
    )
    if exists:
        await db.execute(
            "DELETE FROM social_follows WHERE follower_id = $1 AND followee_id = $2",
            user_id, target_id,
        )
        return {"following": False}
    await db.execute(
        "INSERT INTO social_follows (follower_id, followee_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        user_id, target_id,
    )
    return {"following": True}


@router.get("/leaderboard")
async def leaderboard(
    user_id: CurrentUserDep,
    db: DbDep,
    category: str = Query("overall"),
    limit: int = Query(10, ge=1, le=50),
):
    """Top-N rankings.

    Categories:
      overall  — by social_score (likes received + posts authored)
      strength — by total weight lifted in last 30d (workouts.kg * sets * reps)
      consistency — by current streak length
      weight   — by absolute weight delta over last 90d (positive = closest to goal)
    """
    if category == "overall":
        rows = await db.fetch(
            """
            SELECT user_id,
                   COALESCE(display_name, user_name, telegram_username, 'user') AS name,
                   social_score AS score
            FROM user_main
            WHERE public_profile = TRUE OR user_id = $1
            ORDER BY social_score DESC
            LIMIT $2
            """,
            user_id, limit,
        )
        return {"category": category, "items": [dict(r) for r in rows]}

    if category == "consistency":
        rows = await db.fetch(
            """
            SELECT u.user_id,
                   COALESCE(u.display_name, u.user_name, u.telegram_username, 'user') AS name,
                   COALESCE(s.current_streak, 0) AS score
            FROM user_main u
            LEFT JOIN user_streaks s ON s.user_id = u.user_id
            WHERE u.public_profile = TRUE OR u.user_id = $1
            ORDER BY score DESC
            LIMIT $2
            """,
            user_id, limit,
        )
        return {"category": category, "items": [dict(r) for r in rows]}

    raise HTTPException(status_code=400, detail=f"unknown category: {category}")


@router.get("/me")
async def my_social_profile(user_id: CurrentUserDep, db: DbDep):
    row = await db.fetchrow(
        """
        SELECT user_id, COALESCE(display_name, user_name, telegram_username, 'user') AS name,
               display_name, bio, gender, public_profile, social_score
        FROM user_main WHERE user_id = $1
        """,
        user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="user missing")
    posts = await db.fetchval(
        "SELECT COUNT(*) FROM social_posts WHERE user_id = $1", user_id,
    )
    followers = await db.fetchval(
        "SELECT COUNT(*) FROM social_follows WHERE followee_id = $1", user_id,
    )
    following = await db.fetchval(
        "SELECT COUNT(*) FROM social_follows WHERE follower_id = $1", user_id,
    )
    return {
        **dict(row),
        "posts_count": int(posts or 0),
        "followers": int(followers or 0),
        "following": int(following or 0),
    }


@router.patch("/me")
async def update_my_social_profile(
    user_id: CurrentUserDep, db: DbDep, body: dict = Body(...)
):
    fields, values = [], []
    if "display_name" in body:
        v = (body["display_name"] or "").strip()[:64] or None
        values.append(v)
        fields.append(f"display_name = ${len(values)}")
    if "bio" in body:
        v = (body["bio"] or "").strip()[:280] or None
        values.append(v)
        fields.append(f"bio = ${len(values)}")
    if "gender" in body:
        g = (body["gender"] or "").strip().lower() or None
        if g and g not in {"male", "female", "other"}:
            raise HTTPException(status_code=400, detail="invalid gender")
        values.append(g)
        fields.append(f"gender = ${len(values)}")
    if "public_profile" in body:
        values.append(bool(body["public_profile"]))
        fields.append(f"public_profile = ${len(values)}")

    if not fields:
        return await my_social_profile(user_id, db)

    values.append(user_id)
    await db.execute(
        f"UPDATE user_main SET {', '.join(fields)} WHERE user_id = ${len(values)}",
        *values,
    )
    return await my_social_profile(user_id, db)
