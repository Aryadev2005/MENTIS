"""MENTIS application configuration via environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    APP_HOST: str = "0.0.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "info"

    # AI APIs
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEEPGRAM_API_KEY: str = ""
    LANGSMITH_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "mentis-dev"

    # Auth
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""

    # Payment
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Databases
    POSTGRES_URL: str = "postgresql+asyncpg://mentis_user:mentis_dev_password@localhost:5432/mentis"
    POSTGRES_PASSWORD: str = "mentis_dev_password"

    REDIS_URL: str = "redis://:mentis_redis_dev@localhost:6379/0"
    REDIS_PASSWORD: str = "mentis_redis_dev"

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    SQLITE_PATH: str = "./data/mentis_local.db"

    # Security
    ENCRYPTION_KEY: str = "00000000000000000000000000000000"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 43200

    # Features
    ENABLE_OFFLINE_MODE: bool = True
    ENABLE_GROUP_MODE: bool = True
    ENABLE_SELF_LEARNING: bool = True
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Pricing (paise)
    PRICE_STUDENT_MONTHLY: int = 29900
    PRICE_PRO_MONTHLY: int = 79900
    PRICE_OA_PASS: int = 19900

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
