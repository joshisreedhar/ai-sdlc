"""Stub click-event handler (P1-03): logs and returns - no parsing, no persistence.

Phase 2 replaces this class with an enrichment handler (User-Agent parsing, GeoIP
resolution, analytics persistence). Because the subscriber depends on the
``ClickEventHandler`` port rather than on this class, that swap touches only the
composition root.
"""

from __future__ import annotations

from urlshortener.contracts.events.click_event import ClickEvent
from urlshortener.shared_kernel.logging.structured_logging import get_logger

logger = get_logger(__name__)


class LoggingClickEventHandler:
    """Logs the event as structured JSON. Idempotent: logging twice is harmless."""

    async def handle(self, event: ClickEvent) -> None:
        """Log the event. Never raises, so the caller always acknowledges it."""
        logger.info(
            "click_event_received",
            extra={
                "event_id": str(event.event_id),
                "short_code": event.short_code,
                "occurred_at": event.occurred_at.isoformat(),
                "client_ip": event.client_ip,
                "user_agent": event.user_agent,
                "referrer": event.referrer,
            },
        )
