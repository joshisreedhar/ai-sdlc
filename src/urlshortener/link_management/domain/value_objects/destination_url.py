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

ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})


@dataclass(frozen=True, slots=True)
class DestinationUrl:
    """The absolute URL a short code resolves to."""

    value: str

    # [PHASE 1 / P1-01 - DEVELOPER] Enforce the invariants documented above in
    # ``__post_init__`` and raise ``InvalidDestinationUrl`` on violation.
