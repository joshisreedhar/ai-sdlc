"""P1-01 scenarios 1 and 4: the fully wired Management API against real PostgreSQL."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from urlshortener.apps.management_api.container import create_app
from urlshortener.shared_kernel.config.settings import Settings

pytestmark = [pytest.mark.integration]


@pytest.fixture()
async def app(empty_links_table):
    settings = Settings(
        database_url=empty_links_table,
        short_url_base="http://localhost:8001",
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture()
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as async_client:
        yield async_client


async def test_creates_a_link_and_persists_it(client, empty_links_table):
    response = await client.post(
        "/links", json={"long_url": "https://example.com/landing?x=1"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["short_url"] == f"http://localhost:8001/{body['short_code']}"

    engine = create_async_engine(empty_links_table)
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text("SELECT long_url FROM links WHERE short_code = :code"),
                    {"code": body["short_code"]},
                )
            ).one()
    finally:
        await engine.dispose()

    assert row.long_url == "https://example.com/landing?x=1"


async def test_rejects_an_invalid_url_without_persisting_anything(
    client, empty_links_table
):
    response = await client.post("/links", json={"long_url": "not a url"})

    assert response.status_code == 422

    engine = create_async_engine(empty_links_table)
    try:
        async with engine.connect() as connection:
            count = (
                await connection.execute(text("SELECT count(*) FROM links"))
            ).scalar_one()
    finally:
        await engine.dispose()

    assert count == 0


async def test_two_creations_receive_distinct_short_codes(client):
    first = await client.post("/links", json={"long_url": "https://a.example/1"})
    second = await client.post("/links", json={"long_url": "https://b.example/2"})

    assert first.json()["short_code"] != second.json()["short_code"]


async def test_health_and_readiness_answer(client):
    assert (await client.get("/healthz")).status_code == 200
    assert (await client.get("/readyz")).status_code == 200
