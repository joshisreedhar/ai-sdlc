"""Composition root for the Management API.

The only module in the service allowed to name a concrete adapter (rule L-06). Every
collaborator is built here from the injected ``Settings`` and published on ``app.state``,
where ``link_management.api.dependencies`` reads it back as an abstraction.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from urlshortener.link_management.api.routers import health_router, link_router
from urlshortener.link_management.application.services.link_creation_service import (
    LinkCreationService,
)
from urlshortener.link_management.infrastructure.persistence.engine import (
    create_database_engine,
    create_session_factory,
)
from urlshortener.link_management.infrastructure.persistence.sqlalchemy_link_repository import (  # noqa: E501
    SqlAlchemyLinkRepository,
)
from urlshortener.link_management.infrastructure.shortcode.base62_short_code_generator import (  # noqa: E501
    Base62ShortCodeGenerator,
)
from urlshortener.shared_kernel.config.settings import Settings
from urlshortener.shared_kernel.logging.structured_logging import get_logger
from urlshortener.shared_kernel.time.clock import SystemClock

logger = get_logger(__name__)


def create_app(settings: Settings) -> FastAPI:
    """Build the Management API application with all adapters wired in."""
    engine = create_database_engine(settings.database_url)
    link_repository = SqlAlchemyLinkRepository(create_session_factory(engine))
    link_creation_service = LinkCreationService(
        link_repository=link_repository,
        short_code_generator=Base62ShortCodeGenerator(settings.short_code_length),
        clock=SystemClock(),
        short_url_base=settings.short_url_base,
        max_attempts=settings.short_code_max_attempts,
    )

    async def readiness_probe() -> bool:
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            logger.warning("readiness_check_failed", extra={"dependency": "postgresql"})
            return False
        return True

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("management_api_started", extra={"app_env": settings.app_env})
        yield
        await engine.dispose()

    app = FastAPI(
        title="URL Shortener - Management API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.link_creation_service = link_creation_service
    app.state.readiness_probe = readiness_probe
    app.include_router(health_router.router)
    app.include_router(link_router.router)
    return app
