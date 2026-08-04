"""Link management domain errors."""

from __future__ import annotations

from urlshortener.shared_kernel.domain.errors import DomainError


class InvalidShortCode(DomainError):
    """The supplied short code violates the short-code invariants."""


class InvalidDestinationUrl(DomainError):
    """The supplied destination URL is not a well-formed absolute http(s) URL."""


class ShortCodeGenerationExhausted(DomainError):
    """Short-code generation collided on every permitted attempt.

    Signals contention or an exhausted keyspace. The API layer should map this to a
    ``503``-style response, never a ``4xx``: the caller did nothing wrong.
    """
