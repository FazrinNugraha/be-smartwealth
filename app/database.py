"""
SmartWealth Backend â€” Database Configuration

Async SQLAlchemy engine and session management for Neon PostgreSQL.
"""

import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def normalize_database_url(url: str) -> str:
    """Convert Neon/libpq URLs into SQLAlchemy's asyncpg URL format."""
    clean_url = url.split("?", 1)[0]
    if clean_url.startswith("postgresql://"):
        return clean_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return clean_url


# â”€â”€ SSL Context for Neon.tech â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# asyncpg requires a proper ssl.SSLContext, not a string
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

# Clean DATABASE_URL (remove query params that asyncpg doesn't support)
database_url = normalize_database_url(settings.DATABASE_URL)

# â”€â”€ Async Engine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
engine = create_async_engine(
    database_url,
    echo=not settings.is_production,  # Log SQL queries in development
    pool_size=5,
    max_overflow=10,
    connect_args={
        "ssl": ssl_context,  # Neon requires SSL
        "timeout": 120,  # Extended timeout for Neon connection
        "command_timeout": 120,
        "server_settings": {
            "application_name": "smartwealth_backend",
        },
    },
    pool_timeout=30,
    pool_pre_ping=True,  # Verify connections before using them
)

# â”€â”€ Session Factory â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# â”€â”€ Base Model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


# â”€â”€ Dependency â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async def get_db():
    """
    FastAPI dependency that provides a database session.
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
