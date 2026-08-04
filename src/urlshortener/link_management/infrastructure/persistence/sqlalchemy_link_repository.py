"""PostgreSQL adapter implementing the ``LinkRepository`` port."""

from __future__ import annotations

from sqlalchemy import literal, select
from sqlalchemy.exc import IntegrityError

from urlshortener.link_management.domain.errors import InvalidShortCode
from urlshortener.link_management.domain.model.link import Link
from urlshortener.link_management.domain.value_objects.destination_url import (
    DestinationUrl,
)
from urlshortener.link_management.domain.value_objects.short_code import ShortCode
from urlshortener.link_management.infrastructure.persistence.engine import (
    SessionFactory,
)
from urlshortener.link_management.infrastructure.persistence.orm import LinkModel


class SqlAlchemyLinkRepository:
    """Read/write access to the ``links`` system of record."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def add(self, link: Link) -> None:
        """Insert a new link.

        A unique-constraint violation is surfaced as ``InvalidShortCode`` so that the
        creation service can treat a lost insert race as an ordinary collision.
        """
        async with self._session_factory() as session:
            session.add(self._to_row(link))
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise InvalidShortCode(
                    f"short code already taken: {link.short_code.value}"
                ) from error

    async def exists_by_short_code(self, short_code: ShortCode) -> bool:
        """Return whether the short code is already taken."""
        statement = (
            select(literal(True))
            .select_from(LinkModel)
            .where(LinkModel.short_code == short_code.value)
            .limit(1)
        )
        async with self._session_factory() as session:
            return (await session.execute(statement)).scalar_one_or_none() is not None

    async def find_by_short_code(self, short_code: ShortCode) -> Link | None:
        """Return the link for the short code, or ``None``."""
        statement = select(LinkModel).where(LinkModel.short_code == short_code.value)
        async with self._session_factory() as session:
            row = (await session.execute(statement)).scalar_one_or_none()
        return None if row is None else self._to_entity(row)

    @staticmethod
    def _to_row(link: Link) -> LinkModel:
        return LinkModel(
            short_code=link.short_code.value,
            long_url=link.destination_url.value,
            created_at=link.created_at,
            updated_at=link.created_at,
        )

    @staticmethod
    def _to_entity(row: LinkModel) -> Link:
        return Link(
            id=row.id,
            short_code=ShortCode(row.short_code),
            destination_url=DestinationUrl(row.long_url),
            created_at=row.created_at,
        )
