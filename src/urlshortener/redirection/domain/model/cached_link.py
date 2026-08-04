"""``CachedLink`` - the versioned Redis cache document.

The cache stores a JSON **document**, not a bare URL string. That is a deliberate
evolutionary choice: Phase 3 needs to cache routing rules, expiry and password flags
alongside the destination, and a bare string would force either a second round trip or a
breaking cache format change mid-rollout.

The key prefix embeds the schema version (``link:v1:``), so a future incompatible payload
can be rolled out as ``link:v2:`` while old and new pods run side by side.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

CACHE_SCHEMA_VERSION: int = 1
CACHE_KEY_PREFIX: str = f"link:v{CACHE_SCHEMA_VERSION}:"


class CachedLink(BaseModel):
    """Cached resolution of a short code."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    schema_version: int = CACHE_SCHEMA_VERSION
    short_code: str
    destination_url: str


def cache_key(short_code: str) -> str:
    """Return the Redis key for a short code."""
    return f"{CACHE_KEY_PREFIX}{short_code}"
