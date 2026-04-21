"""Общая обработка и сохранение пользовательских фото.

Хранилище — docker volume `/data/uploads`, монтируемый FastAPI как
`/uploads/*` (см. `main.py`). Это переживает рестарт контейнера и совместимо
с CDN (можно позже поставить nginx перед `/uploads/`). MinIO/S3 не заводим,
пока объёмы малы — замена клиента изолируется ровно в этой функции.

Вход: сырые байты + content-type + подпапка (`food`, `social`, ...).
Выход: `(public_url, jpeg_bytes, (w, h))`. `public_url` относительный
(`/uploads/<kind>/<user>/<name>.jpg`) — фронт сам разрешит его через Next
rewrite.
"""

from __future__ import annotations

import io
import logging
import os
import secrets
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException


logger = logging.getLogger(__name__)

MAX_PHOTO_BYTES = 6 * 1024 * 1024  # 6 MB — останавливает 12-MP .HEIC
ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic", "image/heif"}
DEFAULT_MAX_SIDE = 1600  # px по длинной стороне — достаточно для карточки и чата


def _uploads_root() -> Path:
    """Читает UPLOADS_DIR в runtime — main.py выставляет фактическое значение."""
    return Path(os.environ.get("UPLOADS_DIR", "/data/uploads"))


def save_user_photo(
    *,
    kind: str,
    user_id: int,
    raw: bytes,
    content_type: str | None,
    max_side: int = DEFAULT_MAX_SIDE,
) -> Tuple[str, bytes, Tuple[int, int]]:
    """Валидирует, нормализует (EXIF + resize + strip) и кладёт jpeg на диск.

    `kind` — подпапка: `food`, `social`, `avatars`. Создаётся лениво,
    файлы лежат рядом по пользователю, имя случайное — нельзя угадать URL
    чужого фото.

    Raises
    ------
    HTTPException(415) — неподдерживаемый content-type.
    HTTPException(413) — файл слишком большой.
    HTTPException(400) — слишком маленький/битый/не открывается как image.
    """
    ctype = (content_type or "").lower()
    # HEIC чаще всего приходит как octet-stream из Telegram — доверяем PIL.
    if ctype and ctype not in ALLOWED_PHOTO_TYPES and not ctype.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail="Поддерживаются только JPEG, PNG, WebP, HEIC",
        )
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс. 6 МБ)")
    if len(raw) < 64:
        raise HTTPException(status_code=400, detail="Файл пустой или повреждён")

    try:
        # Heavy import внутри функции — не нагружаем import-time.
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        if max(img.size) > max_side:
            ratio = max_side / max(img.size)
            img = img.resize(
                (int(img.size[0] * ratio), int(img.size[1] * ratio)),
                Image.LANCZOS,
            )
        out_buf = io.BytesIO()
        img.convert("RGB").save(out_buf, format="JPEG", quality=85, optimize=True)
        out_bytes = out_buf.getvalue()
        size = img.size
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("media.save_user_photo: decode failed user=%s kind=%s: %s", user_id, kind, exc)
        raise HTTPException(status_code=400, detail=f"Не удалось обработать изображение: {exc}")

    safe_kind = kind.strip("/").replace("..", "").replace("/", "_") or "misc"
    user_dir = _uploads_root() / safe_kind / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    name = f"{secrets.token_urlsafe(12)}.jpg"
    path = user_dir / name
    try:
        path.write_bytes(out_bytes)
    except OSError as exc:
        logger.error("media.save_user_photo: write failed %s: %s", path, exc)
        raise HTTPException(status_code=500, detail="Не удалось сохранить файл")

    public_url = f"/uploads/{safe_kind}/{user_id}/{name}"
    return public_url, out_bytes, size


__all__ = ["save_user_photo", "MAX_PHOTO_BYTES", "ALLOWED_PHOTO_TYPES"]
