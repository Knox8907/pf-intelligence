"""Application configuration — reads from .env file."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/pf_intel"
    REDIS_URL: str = "redis://localhost:6379"
    ANTHROPIC_API_KEY: str = ""
    META_ACCESS_TOKEN: str = ""
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    SECRET_KEY: str = "change_this_secret_key_minimum_32_chars"
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    SCRAPE_INTERVAL_MINUTES: int = 30
    ADMIN_EMAIL: str = "admin@pf-intelligence.zm"
    ADMIN_PASSWORD: str = "changeme"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
