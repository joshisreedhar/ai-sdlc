"""Redis Streams adapter implementing the ``ClickEventPublisher`` port (P1-03).

``XADD`` is deliberately **not** fault-tolerant here, unlike ``RedisLinkCache``: a broker
failure must propagate so that ``ClickEventDispatcher`` - the one component whose job is
to isolate the visitor from a broker outage - can catch it, log it and swallow it.
Swallowing it here would hide the failure from the component responsible for reacting
to it.
"""

from __future__ import annotations

from redis.asyncio import Redis

from urlshortener.contracts.events.click_event import ClickEvent

PAYLOAD_FIELD: str = "payload"


class RedisStreamClickEventPublisher:
    """``XADD`` onto a bounded (``MAXLEN ~``) Redis stream."""

    def __init__(self, client: Redis, stream: str, max_len: int) -> None:
        self._client = client
        self._stream = stream
        self._max_len = max_len

    async def publish(self, event: ClickEvent) -> None:
        """Append ``event`` to the stream. May raise; callers must not assume success."""
        await self._client.xadd(
            self._stream,
            {PAYLOAD_FIELD: event.model_dump_json()},
            maxlen=self._max_len,
            approximate=True,
        )
