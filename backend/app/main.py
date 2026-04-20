import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db, close_db
from app.redis import init_redis, close_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("propitashka")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting PROpitashka backend [%s]", settings.ENVIRONMENT)

    await init_db()
    await init_redis()

    # Pre-warm runtime settings cache — AI model / timeouts come from DB,
    # and we want the first request to use the live values, not defaults.
    try:
        from app.services import runtime_settings as _rs
        for key in _rs.KNOWN_SETTINGS:
            await _rs.get_setting(key)
        logger.info("Runtime settings cache warmed (%d keys)", len(_rs.KNOWN_SETTINGS))
    except Exception as e:
        logger.warning("Runtime settings warm-up skipped: %s", e)

    # Start Telegram bot for OTP delivery
    from telegram_bot.bot import start_bot, stop_bot
    await start_bot()

    yield

    await stop_bot()
    await close_redis()
    await close_db()
    logger.info("PROpitashka backend stopped")


app = FastAPI(
    title="PROpitashka API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if get_settings().ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if get_settings().ENVIRONMENT != "production" else None,
)

settings_instance = get_settings()
cors_origins = ["http://localhost:3000"]
if settings_instance.FRONTEND_URL and settings_instance.FRONTEND_URL not in cors_origins:
    cors_origins.append(settings_instance.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.middleware.audit import AuditLogMiddleware
app.add_middleware(AuditLogMiddleware)

# Routers
from app.routers import (
    auth, users, food, workouts, water, summary, ai, settings, admin,
    streaks, weight, digest, google_auth, social,
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(google_auth.router, prefix="/api/auth/google", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(food.router, prefix="/api/food", tags=["food"])
app.include_router(workouts.router, prefix="/api/workouts", tags=["workouts"])
app.include_router(water.router, prefix="/api/water", tags=["water"])
app.include_router(summary.router, prefix="/api/summary", tags=["summary"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(streaks.router, prefix="/api/streaks", tags=["streaks"])
app.include_router(weight.router, prefix="/api/weight", tags=["weight"])
app.include_router(digest.router, prefix="/api/digest", tags=["digest"])
app.include_router(social.router, prefix="/api/social", tags=["social"])

# User-uploaded media (currently social post photos). Mounted under
# /uploads/ so it never collides with API routes; the directory is
# persisted via a docker volume in production (see docker-compose.yml).
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "/data/uploads"))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/_internal/ai-health")
async def ai_health():
    """Diagnostic endpoint — verifies the Gemini key actually works.

    Hidden behind /_internal/ on purpose: don't link from the UI, but it is
    safe enough to leave open (only returns the key prefix/tail, never the key).
    """
    from app.services import ai_service
    return await ai_service.health_check()
