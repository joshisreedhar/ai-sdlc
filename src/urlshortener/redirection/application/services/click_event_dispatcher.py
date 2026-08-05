"""Fire-and-forget click event publishing - the boundary the visitor never sees (P1-03).

Every failure below ``asyncio.CancelledError`` is caught here and logged at WARNING. A
broker outage costs one analytics event, never a redirect: by the time ``dispatch`` runs,
the redirect response has already been written to the wire (see
``redirection.api.routers.redirect_router``, which schedules this as a
``starlette.background.BackgroundTask`` and never awaits it inline).
"""

from __future__ import annotations

import asyncio

from urlshortener.contracts.events.click_event import ClickEvent
from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.ports.click_event_publisher import (
    ClickEventPublisher,
)
from urlshortener.shared_kernel.logging.structured_logging import get_logger

logger = get_logger(__name__)


class ClickEventDispatcher:
    """Builds a ``ClickEvent`` from a ``RedirectContext`` and publishes it, never raising."""

    def __init__(self, publisher: ClickEventPublisher) -> None:
        self._publisher = publisher

    async def dispatch(self, context: RedirectContext) -> None:
        """Publish the click for ``context``. Must never surface a failure to the caller."""
        event = ClickEvent(
            short_code=context.short_code,
            occurred_at=context.requested_at,
            client_ip=context.client_ip,
            user_agent=context.user_agent,
            referrer=context.referrer,
        )
        try:
            await self._publisher.publish(event)
        except asyncio.CancelledError:
            raise
        except BaseException:
            logger.warning(
                "click_event_publish_failed",
                extra={"short_code": context.short_code},
                exc_info=True,
            )
