"""In-memory test doubles for the link management ports.

They exist so that the use case can be exercised with no PostgreSQL and no framework,
which is exactly what architecture rules L-02 and L-05 are there to guarantee.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import UTC, datetime

from urlshortener.link_management.domain.errors import InvalidShortCode
from urlshortener.link_management.domain.model.link import Link
from urlshortener.link_management.domain.value_objects.short_code import ShortCode


class InMemoryLinkRepository:
    """A ``LinkRepository`` backed by a dict, with the unique constraint enforced."""

    def __init__(self, taken: Iterable[str] = ()) -> None:
        self.links: dict[str, Link] = {}
        self.taken: set[str] = set(taken)
        self.add_calls: list[Link] = []
        self.exists_calls: list[str] = []

    async def add(self, link: Link) -> None:
        self.add_calls.append(link)
        code = link.short_code.value
        if code in self.taken or code in self.links:
            raise InvalidShortCode(f"short code already taken: {code}")
        self.links[code] = link

    async def exists_by_short_code(self, short_code: ShortCode) -> bool:
        self.exists_calls.append(short_code.value)
        return short_code.value in self.taken or short_code.value in self.links

    async def find_by_short_code(self, short_code: ShortCode) -> Link | None:
        return self.links.get(short_code.value)


class RacingLinkRepository(InMemoryLinkRepository):
    """Reports a code as free, then loses the race on insert.

    Reproduces the non-atomic check-then-insert window that the creation service must
    survive (P1-01 scenario 3).
    """

    def __init__(self, losing_codes: Iterable[str]) -> None:
        super().__init__()
        self._losing_codes = set(losing_codes)

    async def exists_by_short_code(self, short_code: ShortCode) -> bool:
        self.exists_calls.append(short_code.value)
        return short_code.value in self.links

    async def add(self, link: Link) -> None:
        self.add_calls.append(link)
        code = link.short_code.value
        if code in self._losing_codes:
            raise InvalidShortCode(f"unique violation on {code}")
        self.links[code] = link


class ScriptedShortCodeGenerator:
    """A ``ShortCodeGenerator`` yielding a predetermined sequence of codes."""

    def __init__(self, codes: Iterable[str]) -> None:
        self._codes: Iterator[str] = iter(list(codes))
        self.generate_calls = 0

    def generate(self) -> ShortCode:
        self.generate_calls += 1
        return ShortCode(next(self._codes))


class FrozenClock:
    """A ``Clock`` stuck at a fixed instant."""

    def __init__(self, instant: datetime | None = None) -> None:
        self.instant = instant or datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    def now(self) -> datetime:
        return self.instant
