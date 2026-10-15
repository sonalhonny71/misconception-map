from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_url_direct: Optional[str] = Field(default=None, env="DATABASE_URL_DIRECT")

    # Security
    secret_key: str = Field(..., env="SECRET_KEY")

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


settings = Settings()

# Convert database URL to SQLAlchemy format
def get_database_url() -> str:
    url = settings.database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    # Ensure sslmode=require is present
    if "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url


def get_database_url_direct() -> str:
    url = settings.database_url_direct or settings.database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url


DATABASE_URL = get_database_url()
DATABASE_URL_DIRECT = get_database_url_direct()