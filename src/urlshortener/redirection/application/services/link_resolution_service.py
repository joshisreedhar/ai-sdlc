"""Cache-first short-code resolution - the redirect pipeline's terminal handler (P1-02).

Redis is authoritative for latency, PostgreSQL is authoritative for truth. A cache
outage therefore costs latency and nothing else: the ``LinkCache`` port guarantees its
adapters never raise, so a failed lookup is indistinguishable from a miss and the request
falls through to the system of record.

There is deliberately **no negative caching** in Phase 1. Nothing can invalidate a cache
entry yet (links are immutable until Phase 3), so caching a 404 would make a newly
created link unreachable for a full TTL.
"""

from __future__ import annotations

from urlshortener.redirection.domain.model.cached_link import CachedLink
from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.model.redirect_decision import (
    LinkNotFound,
    RedirectDecision,
    RedirectToDestination,
)
from urlshortener.redirection.domain.ports.link_cache import LinkCache
from urlshortener.redirection.domain.ports.link_read_repository import (
    LinkReadRepository,
)
from urlshortener.shared_kernel.logging.structured_logging import get_logger

logger = get_logger(__name__)


class LinkResolutionService:
    """Resolves a short code to a redirect decision, cache first."""

    def __init__(
        self,
        link_cache: LinkCache,
        link_read_repository: LinkReadRepository,
        cache_ttl_seconds: int,
    ) -> None:
        self._link_cache = link_cache
        self._link_read_repository = link_read_repository
        self._cache_ttl_seconds = cache_ttl_seconds

    async def resolve(self, context: RedirectContext) -> RedirectDecision:
        """Return the decision for ``context``. Bound as the pipeline's terminal handler."""
        short_code = context.short_code

        cached = await self._link_cache.get(short_code)
        if cached is not None:
            return RedirectToDestination(destination_url=cached.destination_url)

        resolved = await self._link_read_repository.find_by_short_code(short_code)
        if resolved is None:
            logger.info("short_code_not_found", extra={"short_code": short_code})
            return LinkNotFound(short_code=short_code)

        await self._link_cache.put(
            CachedLink(
                short_code=resolved.short_code,
                destination_url=resolved.destination_url,
            ),
            ttl_seconds=self._cache_ttl_seconds,
        )
        return RedirectToDestination(destination_url=resolved.destination_url)
