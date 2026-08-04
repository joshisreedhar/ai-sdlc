"""P1-02: the Redis ``LinkCache`` adapter.

The port's contract is that a cache outage degrades latency, never correctness, so the
adapter must swallow every client failure. That is asserted here against a client double
rather than against a real server, so the failure path is deterministic.
"""

from __future__ import annotations

import json
from typing import cast

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from urlshortener.redirection.domain.model.cached_link import CachedLink
from urlshortener.redirection.infrastructure.cache.redis_link_cache import (
    RedisLinkCache,
)

pytestmark = pytest.mark.unit

KEY = "link:v1:abcd123"
DESTINATION = "https://example.com/landing"


class FakeRedisClient:
    """Stands in for ``redis.asyncio.Redis``, implementing only what the adapter calls."""

    def __init__(self, values=None, failing=False):
        self.values: dict[str, str] = dict(values or {})
        self.failing = failing
        self.set_calls: list[tuple[str, str, int | None]] = []

    async def get(self, name):
        if self.failing:
            raise RedisConnectionError("redis is down")
        return self.values.get(name)

    async def set(self, name, value, ex=None):
        if self.failing:
            raise RedisConnectionError("redis is down")
        self.set_calls.append((name, value, ex))
        self.values[name] = value


def _cache(client: FakeRedisClient) -> RedisLinkCache:
    return RedisLinkCache(cast(Redis, client))


def _document(short_code: str = "abcd123", destination: str = DESTINATION) -> str:
    return CachedLink(
        short_code=short_code, destination_url=destination
    ).model_dump_json()


async def test_reads_the_versioned_document_under_the_versioned_key():
    client = FakeRedisClient({KEY: _document()})

    entry = await _cache(client).get("abcd123")

    assert entry is not None
    assert entry.destination_url == DESTINATION
    assert entry.schema_version == 1


async def test_reports_a_miss_as_none():
    assert await _cache(FakeRedisClient()).get("abcd123") is None


async def test_reports_a_client_failure_as_a_miss():
    assert await _cache(FakeRedisClient(failing=True)).get("abcd123") is None


@pytest.mark.parametrize(
    "payload",
    ["not json at all", "{}", json.dumps({"short_code": "abcd123"}), ""],
    ids=["garbage", "empty-object", "missing-destination", "empty-string"],
)
async def test_treats_an_unreadable_cached_payload_as_a_miss(payload):
    client = FakeRedisClient({KEY: payload})

    assert await _cache(client).get("abcd123") is None


async def test_writes_the_document_with_the_requested_ttl():
    client = FakeRedisClient()
    entry = CachedLink(short_code="abcd123", destination_url=DESTINATION)

    await _cache(client).put(entry, ttl_seconds=900)

    assert len(client.set_calls) == 1
    key, value, ttl = client.set_calls[0]
    assert key == KEY
    assert ttl == 900
    assert json.loads(value)["destination_url"] == DESTINATION


async def test_a_write_failure_is_swallowed():
    entry = CachedLink(short_code="abcd123", destination_url=DESTINATION)

    await _cache(FakeRedisClient(failing=True)).put(entry, ttl_seconds=900)


async def test_a_written_entry_round_trips():
    client = FakeRedisClient()
    cache = _cache(client)

    await cache.put(
        CachedLink(short_code="abcd123", destination_url=DESTINATION), ttl_seconds=60
    )
    entry = await cache.get("abcd123")

    assert entry is not None
    assert entry.destination_url == DESTINATION
