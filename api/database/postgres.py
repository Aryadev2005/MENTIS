"""PostgreSQL connection with pgvector support via SQLAlchemy async engine."""

import logging
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from ..config import settings

logger = logging.getLogger(__name__)

engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    global engine, AsyncSessionLocal

    engine = create_async_engine(
        settings.POSTGRES_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
    )

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    from ..models.db import user, session, question, performance  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("PostgreSQL initialized with pgvector extension")


async def close_db() -> None:
    global engine
    if engine:
        await engine.dispose()
        engine = None
        logger.info("PostgreSQL connection closed")


async def get_session() -> AsyncIterator[AsyncSession]:
    if not AsyncSessionLocal:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency for database sessions."""
    async for session in get_session():
        yield session
