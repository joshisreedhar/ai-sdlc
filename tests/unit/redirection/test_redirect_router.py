"""P1-02: the ``GET /{short_code}`` transport contract.

The router is driven through a real ``RedirectPipeline`` with zero interceptors - the
same object the composition root builds - so the Phase 3 seam is exercised rather than
bypassed.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tests.unit.redirection.fakes import FrozenClock
from urlshortener.redirection.api.routers import redirect_router
from urlshortener.redirection.application.pipeline.redirect_pipeline import (
    RedirectPipeline,
)
from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.model.redirect_decision import (
    LinkNotFound,
    RedirectDecision,
    RedirectToDestination,
)

pytestmark = pytest.mark.unit

DESTINATION = "https://example.com/landing?utm_source=news"


class RecordingTerminalHandler:
    """Captures the context the pipeline was given and returns a fixed decision."""

    def __init__(self, decision: RedirectDecision) -> None:
        self._decision = decision
        self.contexts: list[RedirectContext] = []

    async def __call__(self, context: RedirectContext) -> RedirectDecision:
        self.contexts.append(context)
        return self._decision


class UnhandledDecision(RedirectDecision):
    """Stands in for a decision subclass a later phase might add."""

    __slots__ = ()


def _client(handler, clock=None, raise_app_exceptions=True):
    app = FastAPI()
    app.state.redirect_pipeline = RedirectPipeline(
        terminal_handler=handler, interceptors=()
    )
    app.state.clock = clock or FrozenClock()
    app.include_router(redirect_router.router)
    return AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions),
        base_url="http://testserver",
        follow_redirects=False,
    )


async def test_redirects_with_302_and_the_destination_in_the_location_header():
    handler = RecordingTerminalHandler(
        RedirectToDestination(destination_url=DESTINATION)
    )

    async with _client(handler) as client:
        response = await client.get("/abcd123")

    assert response.status_code == 302
    assert response.headers["location"] == DESTINATION


async def test_forbids_intermediaries_from_caching_the_redirect():
    handler = RecordingTerminalHandler(
        RedirectToDestination(destination_url=DESTINATION)
    )

    async with _client(handler) as client:
        response = await client.get("/abcd123")

    assert response.headers["cache-control"] == "no-store"


async def test_an_unknown_short_code_is_404_with_no_location_header():
    handler = RecordingTerminalHandler(LinkNotFound(short_code="missing"))

    async with _client(handler) as client:
        response = await client.get("/missing")

    assert response.status_code == 404
    assert "location" not in response.headers


async def test_a_decision_the_router_does_not_know_raises():
    """A new decision subclass must never silently fall through to a redirect."""
    handler = RecordingTerminalHandler(UnhandledDecision())

    async with _client(handler) as client:
        with pytest.raises(NotImplementedError):
            await client.get("/abcd123")


async def test_a_decision_the_router_does_not_know_surfaces_as_a_server_error():
    handler = RecordingTerminalHandler(UnhandledDecision())

    async with _client(handler, raise_app_exceptions=False) as client:
        response = await client.get("/abcd123")

    assert response.status_code == 500


async def test_the_pipeline_receives_the_requested_short_code():
    handler = RecordingTerminalHandler(
        RedirectToDestination(destination_url=DESTINATION)
    )

    async with _client(handler) as client:
        await client.get("/abcd123")

    assert [context.short_code for context in handler.contexts] == ["abcd123"]


async def test_the_context_carries_the_request_metadata_phase_2_and_3_will_need():
    handler = RecordingTerminalHandler(
        RedirectToDestination(destination_url=DESTINATION)
    )
    clock = FrozenClock()

    async with _client(handler, clock=clock) as client:
        await client.get(
            "/abcd123",
            headers={
                "user-agent": "Mozilla/5.0 (test)",
                "referer": "https://referrer.example/page",
            },
        )

    context = handler.contexts[0]
    assert context.user_agent == "Mozilla/5.0 (test)"
    assert context.referrer == "https://referrer.example/page"
    assert context.requested_at == clock.now()


async def test_the_client_ip_is_the_first_hop_of_x_forwarded_for():
    handler = RecordingTerminalHandler(
        RedirectToDestination(destination_url=DESTINATION)
    )

    async with _client(handler) as client:
        await client.get(
            "/abcd123",
            headers={"x-forwarded-for": "203.0.113.7, 70.41.3.18, 150.172.238.178"},
        )

    assert handler.contexts[0].client_ip == "203.0.113.7"


async def test_the_client_ip_falls_back_to_the_peer_address():
    handler = RecordingTerminalHandler(
        RedirectToDestination(destination_url=DESTINATION)
    )

    async with _client(handler) as client:
        await client.get("/abcd123")

    assert handler.contexts[0].client_ip == "127.0.0.1"
