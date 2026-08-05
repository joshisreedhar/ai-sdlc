"""Composition root for the Redirection Engine.

The interceptor sequence handed to ``RedirectPipeline`` is written out explicitly, even
though it is empty, because this line is the entire Phase 3 extension seam: expiration,
password gating and geo/device routing arrive by appending to it, changing no other file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

import redis.asyncio as redis_asyncio
from fastapi import FastAPI
from sqlalchemy import text

from urlshortener.redirection.api.routers import health_router, redirect_router
from urlshortener.redirection.application.pipeline.redirect_interceptor import (
    RedirectInterceptor,
)
from urlshortener.redirection.application.pipeline.redirect_pipeline import (
    RedirectPipeline,
)
from urlshortener.redirection.application.services.click_event_dispatcher import (
    ClickEventDispatcher,
)
from urlshortener.redirection.application.services.link_resolution_service import (
    LinkResolutionService,
)
from urlshortener.redirection.infrastructure.cache.redis_link_cache import (
    RedisLinkCache,
)
from urlshortener.redirection.infrastructure.messaging.redis_stream_click_event_publisher import (  # noqa: E501
    RedisStreamClickEventPublisher,
)
from urlshortener.redirection.infrastructure.persistence.engine import (
    create_read_engine,
)
from urlshortener.redirection.infrastructure.persistence.sqlalchemy_link_read_repository import (  # noqa: E501
    SqlAlchemyLinkReadRepository,
)
from urlshortener.shared_kernel.config.settings import Settings
from urlshortener.shared_kernel.logging.structured_logging import get_logger
from urlshortener.shared_kernel.time.clock import SystemClock

logger = get_logger(__name__)

REDIRECT_INTERCEPTORS: Sequence[RedirectInterceptor] = ()
"""Ordered redirect interceptors. Intentionally empty in Phase 1.

Phase 3 registers ExpirationInterceptor, PasswordGateInterceptor and
GeoDeviceRoutingInterceptor here, in that order; Phase 4 appends
PixelInterstitialInterceptor. Nothing else has to change.
"""


def create_app(settings: Settings) -> FastAPI:
    """Build the Redirection Engine application with all adapters wired in."""
    engine = create_read_engine(settings.database_url)
    redis_client = redis_asyncio.from_url(settings.redis_url, decode_responses=True)

    resolution_service = LinkResolutionService(
        link_cache=RedisLinkCache(redis_client),
        link_read_repository=SqlAlchemyLinkReadRepository(engine),
        cache_ttl_seconds=settings.link_cache_ttl_seconds,
    )
    pipeline = RedirectPipeline(
        terminal_handler=resolution_service.resolve,
        interceptors=REDIRECT_INTERCEPTORS,
    )
    click_event_dispatcher = ClickEventDispatcher(
        publisher=RedisStreamClickEventPublisher(
            redis_client,
            stream=settings.click_event_stream,
            max_len=settings.click_stream_max_len,
        )
    )

    async def readiness_probe() -> bool:
        ready = True
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            logger.warning("readiness_check_failed", extra={"dependency": "postgresql"})
            ready = False
        try:
            await redis_client.ping()
        except Exception:
            logger.warning("readiness_check_failed", extra={"dependency": "redis"})
            ready = False
        return ready

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("redirection_engine_started", extra={"app_env": settings.app_env})
        yield
        await engine.dispose()
        await redis_client.aclose()

    app = FastAPI(
        title="URL Shortener - Redirection Engine",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.clock = SystemClock()
    app.state.redirect_pipeline = pipeline
    app.state.click_event_dispatcher = click_event_dispatcher
    app.state.readiness_probe = readiness_probe
    # Health first: GET /{short_code} matches any single segment and would otherwise
    # turn /healthz into a short-code lookup.
    app.include_router(health_router.router)
    app.include_router(redirect_router.router)
    return app
