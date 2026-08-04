"""Output DTO for the link creation use case.

Separate from both the ``Link`` entity and the API response schema: the entity carries
domain value objects that no caller should have to unwrap, and the API schema belongs to
the transport, which the application layer must not depend on.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinkView:
    """What a caller gets back after creating a link."""

    short_code: str
    short_url: str
