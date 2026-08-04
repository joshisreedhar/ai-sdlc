"""P1-01 / F-8: liveness and readiness endpoints on the Management API.

These are the exact probe endpoints Phase 2's Kubernetes deployment will reference, so
they ship with the first image rather than forcing a re-release later.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from urlshortener.link_management.api.routers import health_router

pytestmark = pytest.mark.unit


def _client(ready=None):
    app = FastAPI()
    if ready is not None:

        async def probe() -> bool:
            return ready

        app.state.readiness_probe = probe
    app.include_router(health_router.router)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


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
