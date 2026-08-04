"""Inbound transport port: pulls click events off the broker."""

from __future__ import annotations

from typing import Protocol

from urlshortener.analytics.domain.ports.click_event_handler import ClickEventHandler


class ClickEventSubscriber(Protocol):
    """Long-running consumer loop.

    Phase 1 is backed by a Redis Streams consumer group; Phase 2 may replace it with a
    Celery worker consuming the same stream. Keeping the loop behind this port means the
    handler and the ``ClickEvent`` contract survive that change untouched.
    """

    async def run(self, handler: ClickEventHandler) -> None:
        """Consume until cancelled, dispatching each event to ``handler``."""
        ...
