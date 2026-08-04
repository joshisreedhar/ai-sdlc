"""``DestinationUrl`` value object.

Invariants (story P1-01 - to be enforced by the implementation):

* a well-formed **absolute** URL with a scheme in ``ALLOWED_SCHEMES`` and a non-empty host;
* immutable once constructed;
* a violation raises ``urlshortener.link_management.domain.errors.InvalidDestinationUrl``.

This is the domain-level guard. The API layer additionally validates the inbound payload
with Pydantic so that a malformed request is rejected with a 422 before any domain object
is constructed (P1-01 acceptance scenario 2). Both checks are intentional: the domain must
be safe when driven from a future non-HTTP entry point (Phase 5 bulk import, webhooks).
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from urlshortener.link_management.domain.errors import InvalidDestinationUrl

ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})


@dataclass(frozen=True, slots=True)
class DestinationUrl:
    """The absolute URL a short code resolves to."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or any(character.isspace() for character in self.value):
            raise InvalidDestinationUrl(
                "destination URL must be non-empty and contain no whitespace"
            )
        parts = urlsplit(self.value)
        if parts.scheme.lower() not in ALLOWED_SCHEMES:
            raise InvalidDestinationUrl(
                f"destination URL scheme must be one of "
                f"{sorted(ALLOWED_SCHEMES)}, got {parts.scheme!r}"
            )
        if not parts.hostname:
            raise InvalidDestinationUrl("destination URL must have a host")
