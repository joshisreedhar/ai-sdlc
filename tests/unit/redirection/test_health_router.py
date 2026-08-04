"""P1-02 / F-8: liveness and readiness endpoints on the Redirection Engine."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tests.unit.redirection.fakes import FrozenClock
from urlshortener.redirection.api.routers import health_router, redirect_router
from urlshortener.redirection.application.pipeline.redirect_pipeline import (
    RedirectPipeline,
)
from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.model.redirect_decision import (
    RedirectDecision,
    RedirectToDestination,
)

pytestmark = pytest.mark.unit


def _client(ready=None, with_redirect_route=False):
    app = FastAPI()
    if ready is not None:

        async def probe() -> bool:
            return ready

        app.state.readiness_probe = probe
    app.include_router(health_router.router)
    if with_redirect_route:

        async def terminal(_: RedirectContext) -> RedirectDecision:
            return RedirectToDestination(destination_url="https://example.com/")

        app.state.redirect_pipeline = RedirectPipeline(
            terminal_handler=terminal, interceptors=()
        )
        app.state.clock = FrozenClock()
        app.include_router(redirect_router.router)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    )


async def test_liveness_is_cheap_and_needs_no_dependency():
    async with _client() as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_reports_200_when_dependencies_answer():
    async with _client(ready=True) as client:
        response = await client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_readiness_reports_503_when_a_dependency_is_down():
    async with _client(ready=False) as client:
        response = await client.get("/readyz")

    assert response.status_code == 503


@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
async def test_the_catch_all_redirect_route_does_not_swallow_the_probes(path):
    """`GET /{short_code}` matches anything, so the probes must be mounted first."""
    async with _client(ready=True, with_redirect_route=True) as client:
        response = await client.get(path)

    assert response.status_code == 200
