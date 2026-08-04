"""P1-02: cache-first short-code resolution.

Covers acceptance scenarios 1 (cache hit, no PostgreSQL), 2 (miss, fallback and cache
fill) and 3 (unknown code).
"""

from __future__ import annotations

import pytest

from tests.unit.redirection.fakes import (
    FrozenClock,
    InMemoryLinkCache,
    InMemoryLinkReadRepository,
    UnavailableLinkCache,
)
from urlshortener.redirection.application.services.link_resolution_service import (
    LinkResolutionService,
)
from urlshortener.redirection.domain.model.cached_link import CACHE_SCHEMA_VERSION
from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.model.redirect_decision import (
    DEFAULT_REDIRECT_STATUS_CODE,
    LinkNotFound,
    RedirectToDestination,
)

pytestmark = pytest.mark.unit

DESTINATION = "https://example.com/landing?utm_source=news"
TTL_SECONDS = 3600


def _context(short_code: str = "abcd123") -> RedirectContext:
    return RedirectContext(
        short_code=short_code,
        requested_at=FrozenClock().now(),
        client_ip="203.0.113.7",
        user_agent="pytest",
        referrer="https://referrer.example",
    )


def _service(cache=None, repository=None, ttl_seconds=TTL_SECONDS):
    return LinkResolutionService(
        link_cache=cache if cache is not None else InMemoryLinkCache(),
        link_read_repository=(
            repository if repository is not None else InMemoryLinkReadRepository()
        ),
        cache_ttl_seconds=ttl_seconds,
    )


async def test_a_cache_hit_resolves_without_touching_postgresql():
    cache = InMemoryLinkCache({"abcd123": DESTINATION})
    repository = InMemoryLinkReadRepository({"abcd123": "https://stale.example"})
    service = _service(cache=cache, repository=repository)

    decision = await service.resolve(_context())

    assert decision == RedirectToDestination(destination_url=DESTINATION)
    assert repository.find_calls == []


async def test_a_cache_miss_falls_back_to_postgresql():
    cache = InMemoryLinkCache()
    repository = InMemoryLinkReadRepository({"abcd123": DESTINATION})
    service = _service(cache=cache, repository=repository)

    decision = await service.resolve(_context())

    assert decision == RedirectToDestination(destination_url=DESTINATION)
    assert repository.find_calls == ["abcd123"]


async def test_a_cache_miss_fills_the_cache_with_a_versioned_document():
    cache = InMemoryLinkCache()
    repository = InMemoryLinkReadRepository({"abcd123": DESTINATION})
    service = _service(cache=cache, repository=repository, ttl_seconds=120)

    await service.resolve(_context())

    assert len(cache.put_calls) == 1
    entry, ttl = cache.put_calls[0]
    assert ttl == 120
    assert entry.short_code == "abcd123"
    assert entry.destination_url == DESTINATION
    assert entry.schema_version == CACHE_SCHEMA_VERSION


async def test_the_filled_cache_serves_the_next_request():
    cache = InMemoryLinkCache()
    repository = InMemoryLinkReadRepository({"abcd123": DESTINATION})
    service = _service(cache=cache, repository=repository)

    await service.resolve(_context())
    await service.resolve(_context())

    assert repository.find_calls == ["abcd123"]


async def test_an_unknown_short_code_yields_link_not_found():
    cache = InMemoryLinkCache()
    repository = InMemoryLinkReadRepository()
    service = _service(cache=cache, repository=repository)

    decision = await service.resolve(_context("missing"))

    assert decision == LinkNotFound(short_code="missing")


async def test_a_miss_is_never_negatively_cached():
    cache = InMemoryLinkCache()
    service = _service(cache=cache, repository=InMemoryLinkReadRepository())

    await service.resolve(_context("missing"))

    assert cache.put_calls == []


async def test_an_unavailable_cache_degrades_to_the_postgresql_path():
    cache = UnavailableLinkCache()
    repository = InMemoryLinkReadRepository({"abcd123": DESTINATION})
    service = _service(cache=cache, repository=repository)

    first = await service.resolve(_context())
    second = await service.resolve(_context())

    assert first == RedirectToDestination(destination_url=DESTINATION)
    assert second == RedirectToDestination(destination_url=DESTINATION)
    assert repository.find_calls == ["abcd123", "abcd123"]


async def test_uses_302_so_that_browsers_do_not_cache_the_mapping_forever():
    cache = InMemoryLinkCache({"abcd123": DESTINATION})
    service = _service(cache=cache)

    decision = await service.resolve(_context())

    assert isinstance(decision, RedirectToDestination)
    assert decision.status_code == DEFAULT_REDIRECT_STATUS_CODE == 302
