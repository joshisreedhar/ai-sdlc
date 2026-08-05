"""P1-03: the Click Consumer composition root, end to end against a real Redis server."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
import redis.asyncio as redis_asyncio

from urlshortener.apps.click_consumer.main import run
from urlshortener.contracts.events.click_event import ClickEvent
from urlshortener.shared_kernel.config.settings import Settings

pytestmark = [pytest.mark.integration]

STREAM = "test.clicks.consumer_main.v1"
GROUP = "test-consumer-main"


@pytest.fixture()
async def client(redis_url):
    connection = redis_asyncio.from_url(redis_url, decode_responses=True)
    try:
        await connection.delete(STREAM)
        yield connection
        await connection.delete(STREAM)
    finally:
        await connection.aclose()


async def test_the_composition_root_consumes_a_published_event(
    redis_url, client, caplog
):
    """The consumer group starts at ``$``, so the composition root must already be
    running before an event is published - the same ordering a real deployment has."""
    settings = Settings(
        redis_url=redis_url,
        click_event_stream=STREAM,
        click_event_consumer_group=GROUP,
    )

    with caplog.at_level("INFO"):
        task = asyncio.ensure_future(run(settings))
        try:
            await asyncio.sleep(0.05)  # let the consumer group be created
            event = ClickEvent(short_code="abcd123", occurred_at=datetime.now(UTC))
            await client.xadd(STREAM, {"payload": event.model_dump_json()})
            await asyncio.sleep(0.3)  # let the loop pick the message up
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    assert any(
        record.__dict__.get("short_code") == "abcd123" for record in caplog.records
    )
