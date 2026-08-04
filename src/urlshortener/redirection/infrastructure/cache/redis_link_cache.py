"""Redis adapter implementing the ``LinkCache`` port.

Total failure tolerance is the port's contract, not a defensive habit: this adapter sits
on the highest-traffic path in the product, and a cache incident must degrade latency
rather than availability. Every failure is therefore swallowed and logged - including
unexpected exception types, because "the cache client raised something we did not
anticipate" is precisely the case that must not reach the visitor.
"""

from __future__ import annotations

from redis.asyncio import Redis

from urlshortener.redirection.domain.model.cached_link import CachedLink, cache_key
from urlshortener.shared_kernel.logging.structured_logging import get_logger

logger = get_logger(__name__)


class RedisLinkCache:
    """Versioned ``CachedLink`` documents under the ``link:v1:`` key prefix.

    The driver type is named directly rather than hidden behind a local narrowing
    Protocol: ``..infrastructure.cache..`` may contain only ``*Cache`` classes
    (architecture rule N-05), and an adapter is exactly the layer that is *allowed* to
    know its driver. Callers depend on the ``LinkCache`` port, not on this class.
    """

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, short_code: str) -> CachedLink | None:
        """Return the cached entry, or ``None`` on a miss, a failure or a bad payload."""
        key = cache_key(short_code)
        try:
            raw = await self._client.get(key)
        except Exception:
            logger.warning("link_cache_read_failed", extra={"key": key}, exc_info=True)
            return None
        if raw is None:
            return None
        return self._parse(key, raw)

    async def put(self, entry: CachedLink, ttl_seconds: int) -> None:
        """Store an entry with a TTL. Never raises to the caller."""
        key = cache_key(entry.short_code)
        try:
            await self._client.set(key, entry.model_dump_json(), ex=ttl_seconds)
        except Exception:
            logger.warning("link_cache_write_failed", extra={"key": key}, exc_info=True)

    @staticmethod
    def _parse(key: str, raw: object) -> CachedLink | None:
        payload = raw.decode("utf-8") if isinstance(raw, bytes | bytearray) else raw
        try:
            return CachedLink.model_validate_json(str(payload))
        except ValueError:
            # A document written by an incompatible producer, or a corrupted value.
            # Treating it as a miss lets the request self-heal from PostgreSQL.
            logger.warning("link_cache_payload_unreadable", extra={"key": key})
            return None
