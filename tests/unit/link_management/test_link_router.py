"""P1-01: the ``POST /links`` transport contract.

The router is exercised against a stubbed application service published on
``app.state``, which is exactly how the composition root wires the real one. No
database, no Redis, no settings.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from urlshortener.link_management.api.routers import link_router
from urlshortener.link_management.application.dto.create_link_command import (
    CreateLinkCommand,
)
from urlshortener.link_management.application.dto.link_view import LinkView
from urlshortener.link_management.domain.errors import (
    InvalidDestinationUrl,
    ShortCodeGenerationExhausted,
)

pytestmark = pytest.mark.unit


class StubLinkCreationService:
    def __init__(self, view=None, error=None):
        self._view = view or LinkView(
            short_code="abcd123", short_url="http://localhost:8001/abcd123"
        )
        self._error = error
        self.commands: list[CreateLinkCommand] = []

    async def create_link(self, command: CreateLinkCommand) -> LinkView:
        self.commands.append(command)
        if self._error is not None:
            raise self._error
        return self._view


def _client(service):
    app = FastAPI()
    app.state.link_creation_service = service
    app.include_router(link_router.router)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def test_returns_201_with_the_short_code_and_short_url():
    service = StubLinkCreationService()

    async with _client(service) as client:
        response = await client.post(
            "/links", json={"long_url": "https://example.com/page"}
        )

    assert response.status_code == 201
    assert response.json() == {
        "short_code": "abcd123",
        "short_url": "http://localhost:8001/abcd123",
    }


async def test_passes_the_submitted_url_through_to_the_use_case_verbatim():
    service = StubLinkCreationService()
    url = "https://example.com/deep/path?utm_source=news&x=1#frag"

    async with _client(service) as client:
        await client.post("/links", json={"long_url": url})

    assert service.commands == [CreateLinkCommand(long_url=url)]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"long_url": ""},
        {"long_url": "example.com"},
        {"long_url": "/relative"},
        {"long_url": "ftp://example.com/f"},
        {"long_url": "javascript:alert(1)"},
        {"long_url": 42},
        {"wrong_field": "https://example.com"},
    ],
    ids=[
        "missing-field",
        "empty",
        "no-scheme",
        "relative",
        "wrong-scheme",
        "javascript",
        "not-a-string",
        "unknown-field",
    ],
)
async def test_rejects_an_invalid_payload_with_422_and_never_reaches_the_use_case(
    payload,
):
    service = StubLinkCreationService()

    async with _client(service) as client:
        response = await client.post("/links", json=payload)

    assert response.status_code == 422
    assert service.commands == []


async def test_maps_a_domain_url_rejection_to_422():
    service = StubLinkCreationService(error=InvalidDestinationUrl("nope"))

    async with _client(service) as client:
        response = await client.post("/links", json={"long_url": "https://example.com"})

    assert response.status_code == 422


async def test_maps_exhausted_short_code_generation_to_503():
    service = StubLinkCreationService(error=ShortCodeGenerationExhausted("no space"))

    async with _client(service) as client:
        response = await client.post("/links", json={"long_url": "https://example.com"})

    assert response.status_code == 503
