"""P1-03 Scenario 4: the publish -> consume path is unbroken end to end.

Proves deliverability against a real Redis server: an event written by
``RedisStreamClickEventPublisher`` is picked up, handled and acknowledged by
``RedisStreamClickEventSubscriber``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
import redis.asyncio as redis_asyncio

from tests.unit.analytics.fakes import RecordingClickEventHandler
from urlshortener.analytics.infrastructure.messaging.redis_stream_click_event_subscriber import (  # noqa: E501
    RedisStreamClickEventSubscriber,
)
from urlshortener.contracts.events.click_event import ClickEvent
from urlshortener.redirection.infrastructure.messaging.redis_stream_click_event_publisher import (  # noqa: E501
    RedisStreamClickEventPublisher,
)

pytestmark = [pytest.mark.integration]

STREAM = "test.clicks.publish_consume.v1"
GROUP = "test-analytics"


@pytest.fixture()
async def client(redis_url):
    connection = redis_asyncio.from_url(redis_url, decode_responses=True)
    try:
        await connection.delete(STREAM)
        yield connection
        await connection.delete(STREAM)
    finally:
        await connection.aclose()


async def test_a_published_event_is_consumed_and_acknowledged(client):
    """The consumer group is created at ``$`` (per the architecture spec), i.e. it only
    sees messages published *after* the subscriber has started - the same ordering a
    real deployment has (the consumer is already running when traffic arrives)."""
    publisher = RedisStreamClickEventPublisher(client, stream=STREAM, max_len=1000)
    subscriber = RedisStreamClickEventSubscriber(
        client=client,
        stream=STREAM,
        consumer_group=GROUP,
        consumer_name="test-consumer",
        block_milliseconds=200,
    )
    handler = RecordingClickEventHandler()

    task = asyncio.ensure_future(subscriber.run(handler))
    try:
        await asyncio.sleep(0.05)  # let the consumer group be created
        event = ClickEvent(short_code="abcd123", occurred_at=datetime.now(UTC))
        await publisher.publish(event)
        await asyncio.sleep(0.3)  # let the loop pick the message up
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert [received.short_code for received in handler.events] == ["abcd123"]

    pending = await client.xpending(STREAM, GROUP)
    assert pending["pending"] == 0
