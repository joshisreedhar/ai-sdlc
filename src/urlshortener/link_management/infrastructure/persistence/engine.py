"""Async SQLAlchemy engine and session factory construction.

Plain functions rather than a singleton: the engine owns a connection pool tied to one
event loop, so it must be created and disposed by the process that owns it - the
composition root - not by whichever module happens to be imported first.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

SessionFactory = async_sessionmaker[AsyncSession]


def create_database_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Build the async engine for ``database_url`` (an ``asyncpg`` DSN)."""
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> SessionFactory:
    """Build a session factory bound to ``engine``."""
    return async_sessionmaker(bind=engine, expire_on_commit=False)
