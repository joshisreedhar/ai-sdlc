"""Click Consumer stub process entry point (P1-03).

Run with ``python -m urlshortener.apps.click_consumer.main``. Reads click events off the
``clicks.v1`` Redis stream and logs them - no parsing, no enrichment, no persistence.
Phase 2 replaces this whole process with Celery workers consuming the same stream and the
same ``ClickEvent`` contract.

This module intentionally does not import ``urlshortener.link_management`` or
``urlshortener.redirection``: the Click Consumer depends only on ``contracts`` +
``shared_kernel`` + its own ``analytics`` package.
"""

from __future__ import annotations

import asyncio
import os
import socket

import redis.asyncio as redis_asyncio

from urlshortener.analytics.application.services.logging_click_event_handler import (
    LoggingClickEventHandler,
)
from urlshortener.analytics.infrastructure.messaging.redis_stream_click_event_subscriber import (  # noqa: E501
    DEFAULT_BLOCK_MILLISECONDS,
    RedisStreamClickEventSubscriber,
)
from urlshortener.shared_kernel.config.settings import Settings
from urlshortener.shared_kernel.logging.structured_logging import (
    configure_logging,
    get_logger,
)

logger = get_logger(__name__)

REDIS_SOCKET_TIMEOUT_SECONDS: float = (DEFAULT_BLOCK_MILLISECONDS / 1000) + 5
"""Comfortably above the subscriber's ``BLOCK`` duration, so the client's own socket read
timeout never races the server-side block and raises a spurious ``TimeoutError``."""


def consumer_name() -> str:
    """A reasonably unique identity for this process within the consumer group."""
    return f"{socket.gethostname()}-{os.getpid()}"


async def run(settings: Settings) -> None:
    """Build the adapters and consume ``settings.click_event_stream`` until cancelled."""
    client = redis_asyncio.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
    )
    subscriber = RedisStreamClickEventSubscriber(
        client=client,
        stream=settings.click_event_stream,
        consumer_group=settings.click_event_consumer_group,
        consumer_name=consumer_name(),
    )
    handler = LoggingClickEventHandler()
    try:
        logger.info(
            "click_consumer_started",
            extra={
                "stream": settings.click_event_stream,
                "consumer_group": settings.click_event_consumer_group,
            },
        )
        await subscriber.run(handler)
    finally:
        await client.aclose()


def bootstrap() -> None:
    """Read configuration once, install logging and run the consumer loop."""
    settings = Settings()
    configure_logging(settings.log_level)
    asyncio.run(run(settings))


if __name__ == "__main__":
    bootstrap()
