"""``Link`` - the aggregate root of the link management context.

Phase 1 shape only. Later phases extend this entity *additively*:

* Phase 3: ``expires_at``, ``password_hash``, ``max_uses``, access rules;
* Phase 4: ``domain_id`` (custom domain), ``is_custom_alias``, pixel configuration;
* Phase 5: ``owner_id``.

Every one of those is a nullable/defaulted addition. Nothing about the Phase 1 shape
needs to change to accommodate them - see ``artifacts/architecture/overall_architecture.md``
section 3.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from urlshortener.link_management.domain.value_objects.destination_url import (
    DestinationUrl,
)
from urlshortener.link_management.domain.value_objects.short_code import ShortCode


@dataclass(frozen=True, slots=True)
class Link:
    """A short code and the destination it resolves to.

    ``id`` is the database surrogate key and is ``None`` until the link is persisted.
    It is deliberately *not* the short code: Phase 4 makes short-code uniqueness
    per-custom-domain, and a surrogate key lets that constraint widen without rewriting
    foreign keys.
    """

    short_code: ShortCode
    destination_url: DestinationUrl
    created_at: datetime
    id: int | None = None
