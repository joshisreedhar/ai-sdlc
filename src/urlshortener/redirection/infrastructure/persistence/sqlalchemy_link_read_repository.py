"""READ-ONLY PostgreSQL adapter implementing the ``LinkReadRepository`` port.

The ``links`` table is described here with SQLAlchemy Core rather than reused from
``link_management.infrastructure.persistence.orm``: sharing a mapped class would couple
the two contexts' release cycles (rule D-01/D-04). The redirect path also needs only two
columns, so a full ORM mapping would be dead weight on the hottest query in the product.

Only the columns this context reads are declared. That is not an oversight: it means a
Phase 3 column addition on the write side cannot break the redirect path.
"""

from __future__ import annotations

from sqlalchemy import Column, MetaData, String, Table, Text, select
from sqlalchemy.ext.asyncio import AsyncEngine

from urlshortener.redirection.domain.model.resolved_link import ResolvedLink

_metadata = MetaData()

links_table = Table(
    "links",
    _metadata,
    Column("short_code", String(64), nullable=False),
    Column("long_url", Text, nullable=False),
)


class SqlAlchemyLinkReadRepository:
    """Cache-miss fallback lookup. Issues ``SELECT`` statements and nothing else."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def find_by_short_code(self, short_code: str) -> ResolvedLink | None:
        """Return the link for the short code, or ``None`` if it does not exist."""
        statement = (
            select(links_table.c.short_code, links_table.c.long_url)
            .where(links_table.c.short_code == short_code)
            .limit(1)
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).one_or_none()
        if row is None:
            return None
        return ResolvedLink(short_code=row.short_code, destination_url=row.long_url)
