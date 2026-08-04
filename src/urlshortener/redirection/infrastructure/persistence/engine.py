"""Async SQLAlchemy engine for the redirect fallback path.

Separate from the Management API's engine on purpose: the two contexts must not share a
module (rule D-01), and this one is intended to be pointed at a database role holding
read-only grants. That operational control - not a keyword scan of adapter internals - is
the real enforcement of "the Redirection Engine never writes" (see archunit_specs.md
section 5).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_read_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Build the async engine used for cache-miss lookups."""
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)
