from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Each field is read from the environment variable with the same name
    # (case-insensitive): DATABASE_URL, DATABASE_URL_DIRECT, SECRET_KEY, ENV, ...
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./test.db"
    database_url_direct: Optional[str] = None

    # Security
    secret_key: str = "test-secret-key-for-development-only"

    # Environment
    env: str = "development"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Token settings
    learner_token_length: int = 32  # bytes, so 64 hex chars


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def _normalize_url(url: str) -> str:
    """Make a database URL usable by the installed driver (psycopg2)."""
    for prefix in ("postgresql://", "postgres://", "postgresql+psycopg://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg2://" + url[len(prefix):]
            break
    # Neon needs SSL; add sslmode=require unless the URL already says otherwise
    # (skipped for SQLite).
    if "sqlite:" not in url and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url


def get_database_url() -> str:
    return _normalize_url(get_settings().database_url)


def get_database_url_direct() -> str:
    settings = get_settings()
    return _normalize_url(settings.database_url_direct or settings.database_url)


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