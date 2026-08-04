"""Persistence port for the link aggregate."""

from __future__ import annotations

from typing import Protocol

from urlshortener.link_management.domain.model.link import Link
from urlshortener.link_management.domain.value_objects.short_code import ShortCode


class LinkRepository(Protocol):
    """Read/write access to the ``links`` system of record.

    Only the Management API uses this port. The Redirection Engine has its own,
    deliberately read-only port (``redirection.domain.ports.link_read_repository``) so
    that the redirect hot path cannot acquire write capability by accident.
    """

    async def add(self, link: Link) -> None:
        """Persist a new link.

        Implementations must surface a unique-constraint violation on ``short_code`` as
        ``urlshortener.link_management.domain.errors.InvalidShortCode`` so the creation
        service can treat a concurrent insert as a collision and retry.
        """
        ...

    async def exists_by_short_code(self, short_code: ShortCode) -> bool:
        """Return whether the short code is already taken."""
        ...

    async def find_by_short_code(self, short_code: ShortCode) -> Link | None:
        """Return the link for the short code, or ``None``."""
        ...
