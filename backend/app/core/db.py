"""
app/core/db.py
Async SQLAlchemy engine, session factory, and base model.
All database access goes through get_db() dependency.
Never construct a session outside of this module.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine — pooled, async
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # detect stale connections
    pool_size=10,
    max_overflow=20,
    connect_args={"timeout": 1, "command_timeout": 3},
    echo=not settings.is_production,  # log SQL only in dev
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Declarative base with common columns
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """All ORM models inherit from this."""
    pass


class TimestampMixin:
    """Adds id, created_at, updated_at to every table."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an AsyncSession, rolls back on exception, always closes.
    Use as: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Readiness check helper (used by /readiness endpoint)
# ---------------------------------------------------------------------------
async def check_db_connection() -> bool:
    """Returns True if the database is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


_db_online: bool | None = None
_last_db_check: float = 0.0


async def is_db_available() -> bool:
    """Returns True if the database is reachable, caching result for 15s to keep offline latency under 1ms."""
    global _db_online, _last_db_check
    import time
    now = time.time()
    if _db_online is not None and (now - _last_db_check) < 15:
        return _db_online
    _db_online = await check_db_connection()
    _last_db_check = now
    return _db_online
