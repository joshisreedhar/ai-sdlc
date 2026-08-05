"""P1-03: the Redis Streams ``ClickEventPublisher`` adapter.

Unlike ``RedisLinkCache``, this adapter does **not** swallow client failures itself: a
broker error must propagate to ``ClickEventDispatcher``, the one component whose job is
to isolate the visitor from it (see ``test_click_event_dispatcher.py``).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from urlshortener.contracts.events.click_event import ClickEvent
from urlshortener.redirection.infrastructure.messaging.redis_stream_click_event_publisher import (  # noqa: E501
    RedisStreamClickEventPublisher,
)

pytestmark = pytest.mark.unit

STREAM = "clicks.v1"


class FakeRedisClient:
    """Stands in for ``redis.asyncio.Redis``, implementing only ``xadd``."""

    def __init__(self, failing: bool = False) -> None:
        self.failing = failing
        self.xadd_calls: list[tuple[str, dict[str, str], int | None, bool]] = []

    async def xadd(self, name, fields, maxlen=None, approximate=True):
        if self.failing:
            raise RedisConnectionError("redis is down")
        self.xadd_calls.append((name, fields, maxlen, approximate))
        return "1-1"


def _publisher(
    client: FakeRedisClient, max_len: int = 1000
) -> RedisStreamClickEventPublisher:
    return RedisStreamClickEventPublisher(
        cast(Redis, client), stream=STREAM, max_len=max_len
    )


def _event(short_code: str = "abcd123") -> ClickEvent:
    return ClickEvent(short_code=short_code, occurred_at=datetime.now(UTC))


async def test_adds_the_event_to_the_configured_stream():
    client = FakeRedisClient()

    await _publisher(client).publish(_event())

    assert len(client.xadd_calls) == 1
    name, fields, maxlen, approximate = client.xadd_calls[0]
    assert name == STREAM
    assert maxlen == 1000
    assert approximate is True
    assert json.loads(fields["payload"])["short_code"] == "abcd123"


async def test_the_payload_round_trips_as_a_click_event():
    client = FakeRedisClient()
    event = _event()

    await _publisher(client).publish(event)

    _, fields, _, _ = client.xadd_calls[0]
    assert ClickEvent.model_validate_json(fields["payload"]) == event


async def test_a_client_failure_propagates_to_the_caller():
    client = FakeRedisClient(failing=True)

    with pytest.raises(RedisConnectionError):
        await _publisher(client).publish(_event())
