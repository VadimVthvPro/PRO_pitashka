from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DB_NAME: str = "propitashka"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_POOL_MIN: int = 2
    DB_POOL_MAX: int = 10

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    # Telegram
    TELEGRAM_TOKEN: str = ""

    # AI
    GEMINI_API_KEY: str = ""
    # Default model — override via env if Google deprecates it. As of 2026-04
    # gemini-2.5-flash is the current stable multimodal flash model.
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour (active session)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 90  # 90 days (remember me)

    # Cookie-scope prefix. HTTP cookies (RFC 6265) не учитывают порт, поэтому
    # прод и freemium на одном хосте делят cookie-пул и ломают авторизацию
    # друг друга. Для freemium ставим AUTH_COOKIE_PREFIX=fm_ — куки
    # становятся `fm_access_token`/`fm_refresh_token` и не пересекаются.
    AUTH_COOKIE_PREFIX: str = ""

    # Admin
    ADMIN_SECRET_KEY: str = "change-me-in-production"
    ADMIN_PASSWORD: str = ""

    # Google OAuth (optional — leave blank to disable Google sign-in)
    GOOGLE_CLIENT_ID: str = ""

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = Field(default=False)
    FRONTEND_URL: str = "http://localhost:3000"

    # Cache TTLs (seconds)
    CACHE_ENABLED: bool = True
    CACHE_TTL_FOOD_RECOGNITION: int = 604800
    CACHE_TTL_RECIPES: int = 86400
    CACHE_TTL_AI_RESPONSES: int = 3600

    # API
    API_TIMEOUT: int = 30
    API_RETRY_ATTEMPTS: int = 3
    API_RETRY_DELAY: float = 1.0

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
