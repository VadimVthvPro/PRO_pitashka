"""Brand metadata endpoint.

Exposes the currently active brand as JSON so the frontend can read it in
runtime (without rebuilding the Next.js image on every brand switch).

Example:
    GET /api/brand
    {
        "name": "profit",
        "display_name": "PROfit",
        "short_name": "PROfit",
        "tagline": "AI-наставник по питанию и тренировкам"
    }
"""

from fastapi import APIRouter

from app import brand as _brand

router = APIRouter()


@router.get("")
async def get_brand() -> dict[str, str]:
    """Return the currently configured brand data.

    Reads ``settings.BRAND`` on every request (cheap — ``get_settings`` is
    memoised). Safe to cache on the client for ~60 seconds.
    """
    data = _brand.current()
    return {
        "name": data["name"],
        "display_name": data["display_name"],
        "short_name": data["short_name"],
        "tagline": data["tagline"],
    }
