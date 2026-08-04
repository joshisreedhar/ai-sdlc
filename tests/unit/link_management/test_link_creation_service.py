"""P1-01: ``LinkCreationService`` use-case behaviour.

Covers acceptance scenarios 1 (create), 2 (invalid URL rejected by the domain) and
3 (collision retry, including the non-atomic check-then-insert race).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.unit.link_management.fakes import (
    FrozenClock,
    InMemoryLinkRepository,
    RacingLinkRepository,
    ScriptedShortCodeGenerator,
)
from urlshortener.link_management.application.dto.create_link_command import (
    CreateLinkCommand,
)
from urlshortener.link_management.application.services.link_creation_service import (
    LinkCreationService,
)
from urlshortener.link_management.domain.errors import (
    InvalidDestinationUrl,
    ShortCodeGenerationExhausted,
)

pytestmark = pytest.mark.unit

LONG_URL = "https://example.com/a/very/long/path?utm_source=newsletter"


def _service(
    repository=None,
    generator=None,
    clock=None,
    short_url_base="http://localhost:8001",
    max_attempts=5,
):
    return LinkCreationService(
        link_repository=repository or InMemoryLinkRepository(),
        short_code_generator=generator or ScriptedShortCodeGenerator(["abcd123"]),
        clock=clock or FrozenClock(),
        short_url_base=short_url_base,
        max_attempts=max_attempts,
    )


async def test_creates_a_link_and_returns_the_code_and_full_short_url():
    repository = InMemoryLinkRepository()
    service = _service(
        repository=repository,
        generator=ScriptedShortCodeGenerator(["abcd123"]),
        short_url_base="https://sho.rt",
    )

    view = await service.create_link(CreateLinkCommand(long_url=LONG_URL))

    assert view.short_code == "abcd123"
    assert view.short_url == "https://sho.rt/abcd123"


async def test_persists_the_mapping_through_the_repository():
    repository = InMemoryLinkRepository()
    service = _service(
        repository=repository, generator=ScriptedShortCodeGenerator(["abcd123"])
    )

    await service.create_link(CreateLinkCommand(long_url=LONG_URL))

    stored = repository.links["abcd123"]
    assert stored.destination_url.value == LONG_URL
    assert stored.short_code.value == "abcd123"


async def test_stamps_creation_time_from_the_injected_clock():
    instant = datetime(2030, 6, 1, 12, 0, 0, tzinfo=UTC)
    repository = InMemoryLinkRepository()
    service = _service(repository=repository, clock=FrozenClock(instant))

    await service.create_link(CreateLinkCommand(long_url=LONG_URL))

    assert repository.links["abcd123"].created_at == instant


async def test_does_not_emit_a_double_slash_when_the_base_ends_with_one():
    service = _service(short_url_base="https://sho.rt/")

    view = await service.create_link(CreateLinkCommand(long_url=LONG_URL))

    assert view.short_url == "https://sho.rt/abcd123"


async def test_rejects_a_destination_that_is_not_an_absolute_http_url():
    repository = InMemoryLinkRepository()
    service = _service(repository=repository)

    with pytest.raises(InvalidDestinationUrl):
        await service.create_link(CreateLinkCommand(long_url="not-a-url"))

    assert repository.links == {}
    assert repository.add_calls == []


async def test_retries_when_the_generated_code_is_already_taken():
    repository = InMemoryLinkRepository(taken={"taken01", "taken02"})
    generator = ScriptedShortCodeGenerator(["taken01", "taken02", "free003"])
    service = _service(repository=repository, generator=generator)

    view = await service.create_link(CreateLinkCommand(long_url=LONG_URL))

    assert view.short_code == "free003"
    assert generator.generate_calls == 3
    assert set(repository.links) == {"free003"}


async def test_retries_when_a_concurrent_insert_wins_the_race():
    repository = RacingLinkRepository(losing_codes={"raced01"})
    generator = ScriptedShortCodeGenerator(["raced01", "free003"])
    service = _service(repository=repository, generator=generator)

    view = await service.create_link(CreateLinkCommand(long_url=LONG_URL))

    assert view.short_code == "free003"
    assert [link.short_code.value for link in repository.add_calls] == [
        "raced01",
        "free003",
    ]


async def test_gives_up_after_the_configured_number_of_attempts():
    repository = InMemoryLinkRepository(taken={f"taken0{index}" for index in range(3)})
    generator = ScriptedShortCodeGenerator([f"taken0{index}" for index in range(3)])
    service = _service(repository=repository, generator=generator, max_attempts=3)

    with pytest.raises(ShortCodeGenerationExhausted):
        await service.create_link(CreateLinkCommand(long_url=LONG_URL))

    assert generator.generate_calls == 3
    assert repository.links == {}


async def test_never_hands_the_same_code_to_two_destinations():
    repository = InMemoryLinkRepository()
    generator = ScriptedShortCodeGenerator(["code001", "code001", "code002"])
    service = _service(repository=repository, generator=generator, max_attempts=5)

    first = await service.create_link(CreateLinkCommand(long_url="https://a.example"))
    second = await service.create_link(CreateLinkCommand(long_url="https://b.example"))

    assert first.short_code != second.short_code
    assert repository.links["code001"].destination_url.value == "https://a.example"
    assert repository.links["code002"].destination_url.value == "https://b.example"
