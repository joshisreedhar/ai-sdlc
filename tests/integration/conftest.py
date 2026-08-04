"""Shared fixtures for tests that need real PostgreSQL / Redis.

Every fixture skips (rather than fails) when the backing service is unreachable, so the
suite stays runnable on a laptop with nothing started. CI brings the services up via the
compose stack, where these tests do run.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://urlshortener:urlshortener@localhost:5432/urlshortener"
)
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def _database_url() -> str:
    return os.environ.get("URLSHORTENER_DATABASE_URL", DEFAULT_DATABASE_URL)


def _redis_url() -> str:
    return os.environ.get("URLSHORTENER_REDIS_URL", DEFAULT_REDIS_URL)


def _database_is_reachable(url: str) -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def probe() -> bool:
        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
        finally:
            await engine.dispose()

    return asyncio.run(probe())


def _redis_is_reachable(url: str) -> bool:
    import redis.asyncio as redis_asyncio

    async def probe() -> bool:
        client = redis_asyncio.from_url(url)
        try:
            await client.ping()
            return True
        except Exception:
            return False
        finally:
            await client.aclose()

    return asyncio.run(probe())


@pytest.fixture(scope="session")
def postgres_url() -> str:
    url = _database_url()
    if not _database_is_reachable(url):
        pytest.skip(f"PostgreSQL is not reachable at {url}")
    return url


@pytest.fixture(scope="session")
def redis_url() -> str:
    url = _redis_url()
    if not _redis_is_reachable(url):
        pytest.skip(f"Redis is not reachable at {url}")
    return url


@pytest.fixture(scope="session")
def migrated_database(postgres_url: str) -> str:
    """Bring the schema to head with Alembic - the same command containers run."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(config, "head")
    return postgres_url


@pytest.fixture()
def empty_links_table(migrated_database: str) -> Iterator[str]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def truncate() -> None:
        engine = create_async_engine(migrated_database)
        try:
            async with engine.begin() as connection:
                await connection.execute(text("TRUNCATE TABLE links RESTART IDENTITY"))
        finally:
            await engine.dispose()

    asyncio.run(truncate())
    yield migrated_database
    asyncio.run(truncate())
