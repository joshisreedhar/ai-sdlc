"""In-memory test doubles for the redirection ports.

The redirect hot path is the highest-traffic code in the product, so it must be
exercisable with no Redis, no PostgreSQL and no HTTP server.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from urlshortener.redirection.domain.model.cached_link import CachedLink
from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.model.resolved_link import ResolvedLink


class InMemoryLinkCache:
    """A ``LinkCache`` backed by a dict, recording every interaction."""

    def __init__(self, entries: Mapping[str, str] | None = None) -> None:
        self.entries: dict[str, CachedLink] = {
            code: CachedLink(short_code=code, destination_url=url)
            for code, url in (entries or {}).items()
        }
        self.get_calls: list[str] = []
        self.put_calls: list[tuple[CachedLink, int]] = []

    async def get(self, short_code: str) -> CachedLink | None:
        self.get_calls.append(short_code)
        return self.entries.get(short_code)

    async def put(self, entry: CachedLink, ttl_seconds: int) -> None:
        self.put_calls.append((entry, ttl_seconds))
        self.entries[entry.short_code] = entry


class UnavailableLinkCache(InMemoryLinkCache):
    """A cache that is down: every read misses and every write is discarded.

    This is the behaviour the ``LinkCache`` port mandates of its adapters, so the
    resolution service must still serve the redirect from PostgreSQL.
    """

    async def get(self, short_code: str) -> CachedLink | None:
        self.get_calls.append(short_code)
        return None

    async def put(self, entry: CachedLink, ttl_seconds: int) -> None:
        self.put_calls.append((entry, ttl_seconds))


class InMemoryLinkReadRepository:
    """A ``LinkReadRepository`` backed by a dict."""

    def __init__(self, rows: Mapping[str, str] | None = None) -> None:
        self.rows: dict[str, str] = dict(rows or {})
        self.find_calls: list[str] = []

    async def find_by_short_code(self, short_code: str) -> ResolvedLink | None:
        self.find_calls.append(short_code)
        destination = self.rows.get(short_code)
        if destination is None:
            return None
        return ResolvedLink(short_code=short_code, destination_url=destination)


class FrozenClock:
    """A ``Clock`` stuck at a fixed instant."""

    def __init__(self, instant: datetime | None = None) -> None:
        self.instant = instant or datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)

    def now(self) -> datetime:
        return self.instant


class RecordingClickEventDispatcher:
    """Stands in for ``ClickEventDispatcher``, recording every context it is given."""

    def __init__(self) -> None:
        self.dispatched: list[RedirectContext] = []

    async def dispatch(self, context: RedirectContext) -> None:
        self.dispatched.append(context)
