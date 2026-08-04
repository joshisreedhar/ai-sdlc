"""Outbound port for emitting click events to the message broker."""

from __future__ import annotations

from typing import Protocol

from urlshortener.contracts.events.click_event import ClickEvent


class ClickEventPublisher(Protocol):
    """Publishes a click event for asynchronous processing.

    Phase 1 is backed by Redis Streams. Phase 2 may swap in a Celery/RabbitMQ adapter;
    because callers depend on this port rather than on a client library, that swap is one
    new class in ``infrastructure.messaging`` plus one line in the composition root.

    Callers must treat ``publish`` as best-effort. The redirect response is already on the
    wire by the time it runs.
    """

    async def publish(self, event: ClickEvent) -> None:
        """Emit the event. May raise; the dispatcher is responsible for swallowing."""
        ...
