"""P1-03: the Redis Streams ``ClickEventSubscriber`` adapter.

``run`` loops forever by contract, so every test bounds it with
``asyncio.wait_for(..., timeout=...)`` and expects the resulting ``TimeoutError`` - that
cancellation is exactly how the real process is expected to be stopped (SIGTERM cancels
the task the composition root scheduled it on).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

import pytest
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from tests.unit.analytics.fakes import RecordingClickEventHandler
from urlshortener.analytics.infrastructure.messaging.redis_stream_click_event_subscriber import (  # noqa: E501
    RedisStreamClickEventSubscriber,
)
from urlshortener.contracts.events.click_event import ClickEvent

pytestmark = pytest.mark.unit

STREAM = "clicks.v1"
GROUP = "analytics"
BOUND = 0.05

StreamBatch = list[tuple[str, list[tuple[str, dict[str, str]]]]]


class FakeStreamRedisClient:
    """Stands in for ``redis.asyncio.Redis``, implementing the subscriber's calls."""

    def __init__(
        self, batches: list[StreamBatch] | None = None, busygroup: bool = False
    ) -> None:
        self._batches: list[StreamBatch] = list(batches or [])
        self.busygroup = busygroup
        self.xgroup_create_calls: list[tuple[str, str, str, bool]] = []
        self.xack_calls: list[tuple[str, str, tuple[str, ...]]] = []

    async def xgroup_create(
        self, name: str, groupname: str, id: str = "$", mkstream: bool = False
    ) -> bool:
        self.xgroup_create_calls.append((name, groupname, id, mkstream))
        if self.busygroup:
            raise ResponseError("BUSYGROUP Consumer Group name already exists")
        return True

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int | None = None,
        block: int | None = None,
    ) -> StreamBatch | None:
        if self._batches:
            return self._batches.pop(0)
        await asyncio.sleep(3600)  # simulate blocking, waiting for new messages
        return None

    async def xack(self, name: str, groupname: str, *ids: str) -> int:
        self.xack_calls.append((name, groupname, ids))
        return len(ids)


def _subscriber(client: FakeStreamRedisClient) -> RedisStreamClickEventSubscriber:
    return RedisStreamClickEventSubscriber(
        client=cast(Redis, client),
        stream=STREAM,
        consumer_group=GROUP,
        consumer_name="test-consumer",
    )


async def _run_bounded(
    subscriber: RedisStreamClickEventSubscriber,
    handler: RecordingClickEventHandler,
) -> None:
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(subscriber.run(handler), timeout=BOUND)


async def test_creates_the_consumer_group_from_the_stream_start():
    client = FakeStreamRedisClient()

    await _run_bounded(_subscriber(client), RecordingClickEventHandler())

    assert client.xgroup_create_calls == [(STREAM, GROUP, "$", True)]


async def test_an_already_existing_consumer_group_is_not_an_error():
    client = FakeStreamRedisClient(busygroup=True)

    await _run_bounded(_subscriber(client), RecordingClickEventHandler())  # no raise


async def test_dispatches_each_message_to_the_handler_and_acknowledges_it():
    event = ClickEvent(short_code="abcd123", occurred_at=datetime.now(UTC))
    client = FakeStreamRedisClient(
        batches=[[(STREAM, [("1-1", {"payload": event.model_dump_json()})])]]
    )
    handler = RecordingClickEventHandler()

    await _run_bounded(_subscriber(client), handler)

    assert [received.short_code for received in handler.events] == ["abcd123"]
    assert client.xack_calls == [(STREAM, GROUP, ("1-1",))]


async def test_an_unreadable_payload_is_acknowledged_and_skipped():
    client = FakeStreamRedisClient(
        batches=[[(STREAM, [("1-1", {"payload": "not json at all"})])]]
    )
    handler = RecordingClickEventHandler()

    await _run_bounded(_subscriber(client), handler)

    assert handler.events == []
    assert client.xack_calls == [(STREAM, GROUP, ("1-1",))]


async def test_a_message_with_no_payload_field_is_acknowledged_and_skipped():
    client = FakeStreamRedisClient(batches=[[(STREAM, [("1-1", {})])]])
    handler = RecordingClickEventHandler()

    await _run_bounded(_subscriber(client), handler)

    assert handler.events == []
    assert client.xack_calls == [(STREAM, GROUP, ("1-1",))]
