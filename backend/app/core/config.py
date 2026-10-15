from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = Field(default="sqlite:///./test.db", env="DATABASE_URL")
    database_url_direct: Optional[str] = Field(default=None, env="DATABASE_URL_DIRECT")

    # Security
    secret_key: str = Field(default="test-secret-key-for-development-only", env="SECRET_KEY")

    # Environment
    env: str = Field(default="development", env="ENV")
    allowed_origins: str = Field(default="http://localhost:5173,http://localhost:3000", env="ALLOWED_ORIGINS")

    # Rate limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")

    # Token settings
    learner_token_length: int = Field(default=32, env="LEARNER_TOKEN_LENGTH")  # bytes, so 64 hex chars

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_database_url() -> str:
    settings = get_settings()
    url = settings.database_url
    # Change both places that do the replace
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    # Ensure sslmode=require is present (skip for SQLite)
    if "sqlite:" not in url and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url


def get_database_url_direct() -> str:
    settings = get_settings()
    url = settings.database_url_direct or settings.database_url
    # Change both places that do the replace
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if "sqlite:" not in url and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url


# For backwards compatibility, provide lazy properties
class _LazySettings:
    def __getattr__(self, name):
        if name == "DATABASE_URL":
            return get_database_url()
        if name == "DATABASE_URL_DIRECT":
            return get_database_url_direct()
        return getattr(get_settings(), name)


settings = _LazySettings()

# Module-level lazy properties for backwards compatibility
class _LazyDatabaseURL:
    def __getattr__(self, name):
        if name == "DATABASE_URL":
            return get_database_url()
        if name == "DATABASE_URL_DIRECT":
            return get_database_url_direct()
        raise AttributeError(f"module 'app.core.config' has no attribute '{name}'")

    def __dir__(self):
        return ["DATABASE_URL", "DATABASE_URL_DIRECT", "get_database_url", "get_database_url_direct", "get_settings", "Settings"]


# Replace module's __getattr__ for lazy DATABASE_URL/DATABASE_URL_DIRECT
import sys
this_module = sys.modules[__name__]
this_module.__getattr__ = _LazyDatabaseURL().__getattr__
this_module.__dir__ = _LazyDatabaseURL().__dir__