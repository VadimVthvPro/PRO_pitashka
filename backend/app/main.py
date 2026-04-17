import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Routers
from app.routers import auth, users, food, workouts, water, summary, ai, settings, admin

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(food.router, prefix="/api/food", tags=["food"])
app.include_router(workouts.router, prefix="/api/workouts", tags=["workouts"])
app.include_router(water.router, prefix="/api/water", tags=["water"])
app.include_router(summary.router, prefix="/api/summary", tags=["summary"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
