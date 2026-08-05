"""Redis Streams adapter implementing the ``ClickEventSubscriber`` port (P1-03 stub).

A consumer group gives at-least-once delivery with acknowledgement: a message stays
pending until ``handler.handle`` returns without raising, at which point it is
``XACK``-ed. Creating the group is idempotent - ``BUSYGROUP`` from a concurrent or
repeated startup is expected and silently ignored.

Replaced by a Celery-based consumer in Phase 2; the ``ClickEvent`` contract and the
``clicks.v1`` stream this reads survive that change untouched.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from urlshortener.analytics.domain.ports.click_event_handler import ClickEventHandler
from urlshortener.contracts.events.click_event import ClickEvent
from urlshortener.shared_kernel.logging.structured_logging import get_logger

logger = get_logger(__name__)

DEFAULT_BLOCK_MILLISECONDS: int = 2_000
"""Kept comfortably under redis-py's default client ``socket_timeout`` (5s): a ``BLOCK``
duration close to or above the client's own read timeout makes ``XREADGROUP`` race its
own socket, raising a spurious ``redis.exceptions.TimeoutError`` instead of returning an
empty result. Composition roots building a client for this subscriber should also give
it a ``socket_timeout`` comfortably larger than this value."""
DEFAULT_BATCH_SIZE: int = 10
PAYLOAD_FIELD: str = "payload"

# redis-py's own stubs type ``xreadgroup``'s return as a broad union covering every
# calling convention the client supports (dict form, cluster form, ...). Calling it the
# way this adapter does - a single stream, decoded responses - always returns this shape
# at runtime, so the cast documents that contract rather than fighting the stub.
StreamEntries = list[tuple[str, list[tuple[str, dict[str, str]]]]]


class RedisStreamClickEventSubscriber:
    """``XREADGROUP`` consumer loop over a single stream/consumer-group pair."""

    def __init__(
        self,
        client: Redis,
        stream: str,
        consumer_group: str,
        consumer_name: str,
        block_milliseconds: int = DEFAULT_BLOCK_MILLISECONDS,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._client = client
        self._stream = stream
        self._consumer_group = consumer_group
        self._consumer_name = consumer_name
        self._block_milliseconds = block_milliseconds
        self._batch_size = batch_size

    async def run(self, handler: ClickEventHandler) -> None:
        """Consume ``self._stream`` until cancelled, dispatching each event to ``handler``."""
        await self._ensure_consumer_group()
        while True:
            response = cast(
                "StreamEntries | None",
                await self._client.xreadgroup(
                    groupname=self._consumer_group,
                    consumername=self._consumer_name,
                    streams={self._stream: ">"},
                    count=self._batch_size,
                    block=self._block_milliseconds,
                ),
            )
            for _, messages in response or []:
                for message_id, fields in messages:
                    await self._handle_one(message_id, fields, handler)

    async def _ensure_consumer_group(self) -> None:
        try:
            await self._client.xgroup_create(
                self._stream, self._consumer_group, id="$", mkstream=True
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise

    async def _handle_one(
        self,
        message_id: str,
        fields: Mapping[str, str],
        handler: ClickEventHandler,
    ) -> None:
        event = self._parse(message_id, fields)
        if event is not None:
            await handler.handle(event)
        await self._client.xack(self._stream, self._consumer_group, message_id)

    def _parse(self, message_id: str, fields: Mapping[str, str]) -> ClickEvent | None:
        payload = fields.get(PAYLOAD_FIELD)
        if payload is None:
            logger.warning(
                "click_event_missing_payload", extra={"message_id": message_id}
            )
            return None
        try:
            return ClickEvent.model_validate_json(payload)
        except ValueError:
            logger.warning(
                "click_event_payload_unreadable", extra={"message_id": message_id}
            )
            return None
