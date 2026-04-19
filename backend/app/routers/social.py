"""Social network: feed, likes, follows, leaderboard."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from app.dependencies import CurrentUserDep, DbDep

router = APIRouter()

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


async def _post_row(db, user_id: int, row) -> dict[str, Any]:
    """Convert asyncpg Record to API dict, including liked_by_me flag."""
    liked = await db.fetchval(
        "SELECT 1 FROM social_likes WHERE user_id = $1 AND post_id = $2",
        user_id, row["id"],
    )
    author = await db.fetchrow(
        """
        SELECT user_id, COALESCE(display_name, name, telegram_username, 'user') AS name,
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
        "payload": dict(row["payload"] or {}),
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
    where = []
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
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    args.extend([limit, offset])
    rows = await db.fetch(
        f"""
        SELECT id, user_id, kind, title, body, tags, payload, likes_count, created_at
        FROM social_posts
        {where_sql}
        ORDER BY created_at DESC
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

    row = await db.fetchrow(
        """
        INSERT INTO social_posts (user_id, kind, title, body, tags, payload)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING id, user_id, kind, title, body, tags, payload, likes_count, created_at
        """,
        user_id, kind, title, text, tags, _to_jsonb(payload),
    )
    await db.execute(
        "UPDATE user_main SET social_score = social_score + 2 WHERE user_id = $1",
        user_id,
    )
    return await _post_row(db, user_id, row)


def _to_jsonb(d: dict) -> str:
    import json
    return json.dumps(d, ensure_ascii=False)


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
                   COALESCE(display_name, name, telegram_username, 'user') AS name,
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
                   COALESCE(u.display_name, u.name, u.telegram_username, 'user') AS name,
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
        SELECT user_id, COALESCE(display_name, name, telegram_username, 'user') AS name,
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
