"""P1-02: the read-only PostgreSQL fallback adapter."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from urlshortener.redirection.infrastructure.persistence.engine import (
    create_read_engine,
)
from urlshortener.redirection.infrastructure.persistence.sqlalchemy_link_read_repository import (  # noqa: E501
    SqlAlchemyLinkReadRepository,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture()
async def engine(empty_links_table):
    created = create_read_engine(empty_links_table)
    try:
        yield created
    finally:
        await created.dispose()


@pytest.fixture()
async def seeded(engine):
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO links (short_code, long_url) "
                "VALUES ('abcd123', 'https://example.com/landing')"
            )
        )
    return engine


async def test_finds_a_seeded_link(seeded):
    repository = SqlAlchemyLinkReadRepository(seeded)

    resolved = await repository.find_by_short_code("abcd123")

    assert resolved is not None
    assert resolved.short_code == "abcd123"
    assert resolved.destination_url == "https://example.com/landing"


async def test_reports_an_unknown_short_code_as_none(seeded):
    repository = SqlAlchemyLinkReadRepository(seeded)

    assert await repository.find_by_short_code("missing") is None


async def test_a_lookup_leaves_the_table_untouched(seeded):
    repository = SqlAlchemyLinkReadRepository(seeded)

    await repository.find_by_short_code("abcd123")
    await repository.find_by_short_code("missing")

    async with seeded.connect() as connection:
        count = (
            await connection.execute(text("SELECT count(*) FROM links"))
        ).scalar_one()
    assert count == 1
