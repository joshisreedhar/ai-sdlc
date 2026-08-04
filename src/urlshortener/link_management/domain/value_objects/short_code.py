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

BASE62_ALPHABET: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
MIN_SHORT_CODE_LENGTH: int = 4
MAX_SHORT_CODE_LENGTH: int = 64


@dataclass(frozen=True, slots=True)
class ShortCode:
    """A URL-safe, base62 short code."""

    value: str

    # [PHASE 1 / P1-01 - DEVELOPER] Enforce the invariants documented above in
    # ``__post_init__`` and raise ``InvalidShortCode`` on violation. Keep the check pure:
    # no I/O, no uniqueness check (uniqueness is a repository concern, not an invariant
    # of the value itself).
