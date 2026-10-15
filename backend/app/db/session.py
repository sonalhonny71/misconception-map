from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import DATABASE_URL, DATABASE_URL_DIRECT, settings


class Base(DeclarativeBase):
    pass


def _connect_args(url: str, timeout: int) -> dict:
    """Driver-specific connection options (SQLite does not accept connect_timeout)."""
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {"connect_timeout": timeout}


# Use NullPool for serverless/proxy environments (Neon pooled)
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args=_connect_args(DATABASE_URL, 10),
)

# For Alembic migrations, use direct connection
def get_migration_engine():
    return create_engine(
        DATABASE_URL_DIRECT,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args=_connect_args(DATABASE_URL_DIRECT, 30),
    )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()