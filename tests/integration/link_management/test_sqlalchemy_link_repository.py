"""P1-01: the SQLAlchemy ``LinkRepository`` adapter against real PostgreSQL.

Also covers acceptance scenario 4: the schema these tests run against is produced by
``alembic upgrade head``, not by ``create_all()``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from urlshortener.link_management.domain.errors import InvalidShortCode
from urlshortener.link_management.domain.model.link import Link
from urlshortener.link_management.domain.value_objects.destination_url import (
    DestinationUrl,
)
from urlshortener.link_management.domain.value_objects.short_code import ShortCode
from urlshortener.link_management.infrastructure.persistence.engine import (
    create_database_engine,
    create_session_factory,
)
from urlshortener.link_management.infrastructure.persistence.sqlalchemy_link_repository import (  # noqa: E501
    SqlAlchemyLinkRepository,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture()
async def repository(empty_links_table):
    engine = create_database_engine(empty_links_table)
    try:
        yield SqlAlchemyLinkRepository(create_session_factory(engine))
    finally:
        await engine.dispose()


def _link(code: str, url: str = "https://example.com/page") -> Link:
    return Link(
        short_code=ShortCode(code),
        destination_url=DestinationUrl(url),
        created_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    )


async def test_adds_and_reads_back_a_link(repository):
    await repository.add(_link("abcd123"))

    found = await repository.find_by_short_code(ShortCode("abcd123"))

    assert found is not None
    assert found.short_code == ShortCode("abcd123")
    assert found.destination_url == DestinationUrl("https://example.com/page")
    assert found.id is not None


async def test_reports_an_unknown_short_code_as_missing(repository):
    assert await repository.find_by_short_code(ShortCode("nothere")) is None
    assert await repository.exists_by_short_code(ShortCode("nothere")) is False


async def test_reports_a_stored_short_code_as_existing(repository):
    await repository.add(_link("abcd123"))

    assert await repository.exists_by_short_code(ShortCode("abcd123")) is True


async def test_surfaces_a_unique_violation_as_invalid_short_code(repository):
    await repository.add(_link("abcd123", "https://first.example"))

    with pytest.raises(InvalidShortCode):
        await repository.add(_link("abcd123", "https://second.example"))

    found = await repository.find_by_short_code(ShortCode("abcd123"))
    assert found is not None
    assert found.destination_url.value == "https://first.example"


async def test_stays_usable_after_a_unique_violation(repository):
    await repository.add(_link("abcd123"))
    with pytest.raises(InvalidShortCode):
        await repository.add(_link("abcd123"))

    await repository.add(_link("efgh456"))

    assert await repository.exists_by_short_code(ShortCode("efgh456")) is True
