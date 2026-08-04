"""Input DTO for the link creation use case.

Deliberately a plain, transport-agnostic value: the same command is what a Phase 5 bulk
importer or webhook consumer would build, with no FastAPI request in sight.

Later phases extend it *additively* with optional fields (Phase 3 password/expiry,
Phase 4 custom alias/domain). Nothing here needs to change for that.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateLinkCommand:
    """A request to shorten one destination URL."""

    long_url: str
