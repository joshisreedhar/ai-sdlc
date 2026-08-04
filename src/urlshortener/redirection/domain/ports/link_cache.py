"""Cache port for short-code resolution (Redis in Phase 1)."""

from __future__ import annotations

from typing import Protocol

from urlshortener.redirection.domain.model.cached_link import CachedLink


class LinkCache(Protocol):
    """Low-latency lookup in front of the system of record.

    Implementations MUST be failure-tolerant from the caller's point of view: a cache
    outage degrades latency, never correctness. Adapters therefore swallow and log
    connection errors, returning ``None`` from ``get`` and doing nothing in ``put``.
    """

    async def get(self, short_code: str) -> CachedLink | None:
        """Return the cached entry, or ``None`` on a miss or cache failure."""
        ...

    async def put(self, entry: CachedLink, ttl_seconds: int) -> None:
        """Store an entry with a TTL. Never raises to the caller."""
        ...
