"""``ShortCode`` value object.

Invariants (story P1-01 - to be enforced by the implementation):

* non-empty, length between 4 and 64 characters inclusive;
* every character drawn from ``BASE62_ALPHABET`` (URL-safe, no separators, no padding);
* immutable once constructed;
* a violation raises ``urlshortener.link_management.domain.errors.InvalidShortCode``.

Evolution note: the 64-character ceiling (rather than a fixed generated length) exists so
that Phase 4 user-supplied custom aliases reuse this exact value object instead of
introducing a parallel type.
"""

from __future__ import annotations

from dataclasses import dataclass

from urlshortener.link_management.domain.errors import InvalidShortCode

BASE62_ALPHABET: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
MIN_SHORT_CODE_LENGTH: int = 4
MAX_SHORT_CODE_LENGTH: int = 64

_BASE62_CHARACTERS: frozenset[str] = frozenset(BASE62_ALPHABET)


@dataclass(frozen=True, slots=True)
class ShortCode:
    """A URL-safe, base62 short code."""

    value: str

    def __post_init__(self) -> None:
        if not MIN_SHORT_CODE_LENGTH <= len(self.value) <= MAX_SHORT_CODE_LENGTH:
            raise InvalidShortCode(
                f"short code must be between {MIN_SHORT_CODE_LENGTH} and "
                f"{MAX_SHORT_CODE_LENGTH} characters, got {len(self.value)}"
            )
        illegal = sorted(set(self.value) - _BASE62_CHARACTERS)
        if illegal:
            raise InvalidShortCode(
                f"short code must be base62; illegal characters: {''.join(illegal)!r}"
            )
