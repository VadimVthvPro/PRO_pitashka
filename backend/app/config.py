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

    # --- Brand (dual-brand parity) ---
    # Один и тот же код обслуживает два бренда: "propitashka" (исторический,
    # для конкурса) и "profit" (публичный). Переключение на сервере через env +
    # рестарт backend'а (~5 сек) для runtime-логики (AI-промпты, бот, paywall).
    # Подробности — см. BRAND_ARCHITECTURE.md и .cursor/rules/dual-brand-parity.mdc.
    BRAND: str = "propitashka"

    # Admin
    ADMIN_SECRET_KEY: str = "change-me-in-production"
    ADMIN_PASSWORD: str = ""

    # ===== OAuth providers =====
    # Любой из трёх опционален — если client_id не задан, соответствующая
    # кнопка в UI просто скрывается (backend отвечает enabled=false на
    # endpoint'ах /config). Это позволяет deploy'ить код до регистрации
    # приложений у провайдеров.
    #
    # Google Sign-In (Google Identity Services — JWT id_token flow, не нужен secret)
    GOOGLE_CLIENT_ID: str = ""
    # Yandex ID (OAuth 2.0 Authorization Code flow — нужны id + secret)
    # Регистрация: https://oauth.yandex.ru/client/new
    YANDEX_CLIENT_ID: str = ""
    YANDEX_CLIENT_SECRET: str = ""
    # VK ID (OAuth 2.1 / Authorization Code + PKCE)
    # Регистрация: https://id.vk.com (раздел «Приложения»)
    VK_CLIENT_ID: str = ""
    VK_CLIENT_SECRET: str = ""

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = Field(default=False)
    FRONTEND_URL: str = "http://localhost:3000"
    # Публичный base-URL, на который провайдеры OAuth возвращают юзера
    # после авторизации. Используется для формирования redirect_uri.
    # В dev это обычно http://localhost:3201; на проде —
    # https://propitashka.ru или https://profit.<domain>.
    # Если пусто — fallback на FRONTEND_URL.
    OAUTH_REDIRECT_BASE: str = ""

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
