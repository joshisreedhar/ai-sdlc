"""READ-ONLY persistence port for the redirect path."""

from __future__ import annotations

from typing import Protocol

from urlshortener.redirection.domain.model.resolved_link import ResolvedLink


class LinkReadRepository(Protocol):
    """Fallback lookup against PostgreSQL when the cache misses.

    This port exposes reads only, and its implementation must issue ``SELECT`` statements
    only. The redirect path never writes to the system of record - click data leaves via
    the message broker (architecture rule D-04 / N-08).
    """

    async def find_by_short_code(self, short_code: str) -> ResolvedLink | None:
        """Return the link for the short code, or ``None`` if it does not exist."""
        ...
