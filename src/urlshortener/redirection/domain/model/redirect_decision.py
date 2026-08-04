"""``RedirectDecision`` - the outcome of running the redirect pipeline.

Open/closed by design: the API layer maps a decision *type* to an HTTP response, so a
later phase adds behaviour by adding a subclass plus one new mapping branch, and never by
editing an existing branch.

Phase 1 ships exactly two decisions. Planned additions (DO NOT IMPLEMENT NOW):

* ``AccessDenied``      - Phase 3, IP/bot filtering or per-link allow list
* ``LinkExpired``       - Phase 3, expiration / max-use restrictions
* ``ServeInterstitial`` - Phase 3 password auth page, Phase 4 conversion-pixel page
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_REDIRECT_STATUS_CODE: int = 302
"""302 (Found), not 301.

A 301 is cached indefinitely by browsers, which would hide destination changes introduced
in Phase 3 and suppress the click events the analytics pipeline depends on. Read the
status code from this constant so that making it per-link configurable later is a
one-place change.
"""


class RedirectDecision:
    """Base type for every possible outcome of the redirect pipeline."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class RedirectToDestination(RedirectDecision):
    """Send the visitor to ``destination_url``."""

    destination_url: str
    status_code: int = DEFAULT_REDIRECT_STATUS_CODE


@dataclass(frozen=True, slots=True)
class LinkNotFound(RedirectDecision):
    """No link exists for this short code; the API layer responds 404."""

    short_code: str
