"""P1-02: the Redis ``LinkCache`` adapter against a real server."""

from __future__ import annotations

import pytest
import redis.asyncio as redis_asyncio

from urlshortener.redirection.domain.model.cached_link import CachedLink, cache_key
from urlshortener.redirection.infrastructure.cache.redis_link_cache import (
    RedisLinkCache,
)

pytestmark = [pytest.mark.integration]

DESTINATION = "https://example.com/landing"


@pytest.fixture()
async def client(redis_url):
    connection = redis_asyncio.from_url(redis_url, decode_responses=True)
    try:
        await connection.delete(cache_key("abcd123"))
        yield connection
        await connection.delete(cache_key("abcd123"))
    finally:
        await connection.aclose()


async def test_round_trips_a_cached_link(client):
    cache = RedisLinkCache(client)

    await cache.put(
        CachedLink(short_code="abcd123", destination_url=DESTINATION), ttl_seconds=60
    )
    entry = await cache.get("abcd123")

    assert entry is not None
    assert entry.destination_url == DESTINATION


async def test_stores_the_document_under_the_versioned_key_with_a_ttl(client):
    cache = RedisLinkCache(client)

    await cache.put(
        CachedLink(short_code="abcd123", destination_url=DESTINATION), ttl_seconds=60
    )

    assert await client.exists("link:v1:abcd123") == 1
    assert 0 < await client.ttl("link:v1:abcd123") <= 60


async def test_reports_a_missing_key_as_a_miss(client):
    assert await RedisLinkCache(client).get("abcd123") is None


async def test_an_unreachable_server_is_a_miss_not_an_error():
    unreachable = redis_asyncio.from_url(
        "redis://127.0.0.1:1/0", socket_connect_timeout=1
    )
    cache = RedisLinkCache(unreachable)
    try:
        assert await cache.get("abcd123") is None
        await cache.put(
            CachedLink(short_code="abcd123", destination_url=DESTINATION),
            ttl_seconds=60,
        )
    finally:
        await unreachable.aclose()
