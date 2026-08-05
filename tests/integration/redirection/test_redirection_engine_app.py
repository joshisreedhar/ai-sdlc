"""P1-02: the fully wired Redirection Engine against real PostgreSQL and Redis.

Covers acceptance scenarios 1-3 end to end, plus the anti-corner-painting checklist item
that the router reaches resolution through ``RedirectPipeline`` with an explicitly empty
interceptor list.
"""

from __future__ import annotations

import json

import pytest
import redis.asyncio as redis_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from urlshortener.apps.redirection_engine.container import create_app
from urlshortener.redirection.domain.model.cached_link import cache_key
from urlshortener.shared_kernel.config.settings import Settings

pytestmark = [pytest.mark.integration]

DESTINATION = "https://example.com/landing?utm_source=news"


@pytest.fixture()
async def seeded_link(empty_links_table):
    engine = create_async_engine(empty_links_table)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO links (short_code, long_url) " "VALUES (:code, :url)"
                ),
                {"code": "abcd123", "url": DESTINATION},
            )
    finally:
        await engine.dispose()
    return "abcd123"


@pytest.fixture()
async def cold_cache(redis_url):
    connection = redis_asyncio.from_url(redis_url, decode_responses=True)
    try:
        await connection.delete(cache_key("abcd123"), cache_key("missing"))
        yield connection
        await connection.delete(cache_key("abcd123"), cache_key("missing"))
    finally:
        await connection.aclose()


@pytest.fixture()
async def client(empty_links_table, redis_url, cold_cache):
    settings = Settings(
        database_url=empty_links_table,
        redis_url=redis_url,
        link_cache_ttl_seconds=60,
    )
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as async_client,
    ):
        yield async_client


async def test_a_cache_miss_redirects_from_postgresql_and_fills_the_cache(
    client, seeded_link, cold_cache
):
    response = await client.get(f"/{seeded_link}")

    assert response.status_code == 302
    assert response.headers["location"] == DESTINATION
    assert response.headers["cache-control"] == "no-store"
    assert await cold_cache.exists(cache_key(seeded_link)) == 1


async def test_a_subsequent_request_is_served_from_the_cache(
    client, seeded_link, empty_links_table
):
    await client.get(f"/{seeded_link}")

    engine = create_async_engine(empty_links_table)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM links"))
    finally:
        await engine.dispose()

    response = await client.get(f"/{seeded_link}")

    assert response.status_code == 302
    assert response.headers["location"] == DESTINATION


async def test_an_unknown_short_code_is_404(client, seeded_link):
    response = await client.get("/missing")

    assert response.status_code == 404


async def test_health_and_readiness_answer(client):
    assert (await client.get("/healthz")).status_code == 200
    assert (await client.get("/readyz")).status_code == 200


async def test_the_pipeline_is_wired_with_an_explicitly_empty_interceptor_list(
    empty_links_table, redis_url
):
    app = create_app(Settings(database_url=empty_links_table, redis_url=redis_url))

    assert app.state.redirect_pipeline.interceptors == ()


@pytest.fixture()
async def clean_click_stream(redis_url):
    stream = "test.clicks.redirection_engine_app.v1"
    connection = redis_asyncio.from_url(redis_url, decode_responses=True)
    try:
        await connection.delete(stream)
        yield stream, connection
        await connection.delete(stream)
    finally:
        await connection.aclose()


async def test_a_successful_redirect_publishes_a_click_event(
    empty_links_table, redis_url, cold_cache, seeded_link, clean_click_stream
):
    """P1-03 Scenario 1: every redirect emits a click event to the broker."""
    stream, stream_connection = clean_click_stream
    settings = Settings(
        database_url=empty_links_table,
        redis_url=redis_url,
        link_cache_ttl_seconds=60,
        click_event_stream=stream,
    )
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as async_client,
    ):
        response = await async_client.get(f"/{seeded_link}")

    assert response.status_code == 302

    entries = await stream_connection.xrange(stream)
    assert len(entries) == 1
    _, fields = entries[0]
    assert json.loads(fields["payload"])["short_code"] == seeded_link


async def test_a_link_not_found_does_not_publish_a_click_event(
    empty_links_table, redis_url, cold_cache, clean_click_stream
):
    stream, stream_connection = clean_click_stream
    settings = Settings(
        database_url=empty_links_table,
        redis_url=redis_url,
        click_event_stream=stream,
    )
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as async_client,
    ):
        response = await async_client.get("/missing")

    assert response.status_code == 404
    assert await stream_connection.xrange(stream) == []
