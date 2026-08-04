"""``ResolvedLink`` - the redirection context's read model of a link.

Intentionally *not* ``link_management.domain.model.Link``: the two contexts must not share
a type (architecture rule D-01), and the redirect path needs only what it needs. Phase 3
extends this read model with expiry/password/rule data; the write-side entity evolves
independently.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolvedLink:
    """A short code and the destination it currently resolves to."""

    short_code: str
    destination_url: str
