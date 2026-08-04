"""Short-code generation port."""

from __future__ import annotations

from typing import Protocol

from urlshortener.link_management.domain.value_objects.short_code import ShortCode


class ShortCodeGenerator(Protocol):
    """Produces candidate short codes.

    Deliberately *not* responsible for uniqueness: generation is a pure, side-effect-free
    concern and collision handling belongs to the creation use case, which owns the
    repository. Keeping them apart lets Phase 4's custom-alias flow reuse the collision
    logic without a generator, and lets a future counter/Snowflake-based generator drop in
    behind this same port.
    """

    def generate(self) -> ShortCode:
        """Return a new candidate short code. May collide; the caller retries."""
        ...
