"""Random base62 short-code generator (story P1-01).

``secrets`` rather than ``random``: short codes are effectively public identifiers of
private destinations, so a predictable sequence would let an observer enumerate other
people's links.
"""

from __future__ import annotations

import secrets

from urlshortener.link_management.domain.value_objects.short_code import (
    BASE62_ALPHABET,
    MAX_SHORT_CODE_LENGTH,
    MIN_SHORT_CODE_LENGTH,
    ShortCode,
)


class Base62ShortCodeGenerator:
    """Produces cryptographically random, fixed-length base62 codes."""

    def __init__(self, length: int) -> None:
        if not MIN_SHORT_CODE_LENGTH <= length <= MAX_SHORT_CODE_LENGTH:
            raise ValueError(
                f"short code length must be between {MIN_SHORT_CODE_LENGTH} and "
                f"{MAX_SHORT_CODE_LENGTH}, got {length}"
            )
        self._length = length

    def generate(self) -> ShortCode:
        """Return a new candidate code. Uniqueness is the caller's concern."""
        return ShortCode(
            "".join(secrets.choice(BASE62_ALPHABET) for _ in range(self._length))
        )
