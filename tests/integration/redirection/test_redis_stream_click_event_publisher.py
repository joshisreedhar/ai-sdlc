"""P1-03: the Redis Streams ``ClickEventPublisher`` adapter against a real server."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
import redis.asyncio as redis_asyncio
from redis.exceptions import RedisError

from urlshortener.contracts.events.click_event import ClickEvent
from urlshortener.redirection.infrastructure.messaging.redis_stream_click_event_publisher import (  # noqa: E501
    RedisStreamClickEventPublisher,
)

pytestmark = [pytest.mark.integration]

STREAM = "test.clicks.publisher.v1"


@pytest.fixture()
async def client(redis_url):
    connection = redis_asyncio.from_url(redis_url, decode_responses=True)
    try:
        await connection.delete(STREAM)
        yield connection
        await connection.delete(STREAM)
    finally:
        await connection.aclose()


async def test_adds_the_event_to_the_configured_stream(client):
    publisher = RedisStreamClickEventPublisher(client, stream=STREAM, max_len=1000)
    event = ClickEvent(short_code="abcd123", occurred_at=datetime.now(UTC))

    await publisher.publish(event)

    entries = await client.xrange(STREAM)
    assert len(entries) == 1
    _, fields = entries[0]
    assert json.loads(fields["payload"])["short_code"] == "abcd123"


async def test_an_unreachable_server_propagates_the_failure():
    unreachable = redis_asyncio.from_url(
        "redis://127.0.0.1:1/0", socket_connect_timeout=1
    )
    publisher = RedisStreamClickEventPublisher(unreachable, stream=STREAM, max_len=1000)
    try:
        with pytest.raises(RedisError):
            await publisher.publish(
                ClickEvent(short_code="abcd123", occurred_at=datetime.now(UTC))
            )
    finally:
        await unreachable.aclose()
