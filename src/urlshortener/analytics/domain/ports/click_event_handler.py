"""Inbound port: what to do with a consumed click event."""

from __future__ import annotations

from typing import Protocol

from urlshortener.contracts.events.click_event import ClickEvent


class ClickEventHandler(Protocol):
    """Processes a single click event.

    Phase 1's only implementation logs the event and returns. Phase 2 replaces it with an
    enrichment handler (User-Agent parsing, GeoIP resolution, analytics persistence).
    Because the subscriber depends on this port rather than on a concrete handler, that
    is a one-class change with no effect on the transport.

    Implementations must be idempotent: the broker delivers at-least-once.
    """

    async def handle(self, event: ClickEvent) -> None:
        """Process the event. Raising signals a failure and prevents acknowledgement."""
        ...
