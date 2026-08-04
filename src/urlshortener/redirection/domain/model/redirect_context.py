"""``RedirectContext`` - the immutable facts of one inbound redirect request.

Phase 1 only uses ``short_code``; the remaining fields are populated anyway because:

* the click event published on every redirect carries them (Phase 2 analytics), and
* Phase 3 geo/device routing rules and IP filtering are evaluated from them.

Populating them now costs nothing and means neither later phase has to re-instrument the
request path. **Do not** drop a field because Phase 1 does not read it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RedirectContext:
    """Everything the redirect pipeline is allowed to know about a request.

    The pipeline must not receive the raw framework ``Request`` object: keeping the
    context framework-free is what allows interceptors (Phase 3) to be unit-tested with
    no HTTP layer and keeps the application layer free of FastAPI (rule L-05).

    ``client_ip`` is the caller's address as determined by the API layer (first hop of
    ``X-Forwarded-For`` when behind the ingress, otherwise the peer address).
    """

    short_code: str
    requested_at: datetime
    client_ip: str | None = None
    user_agent: str | None = None
    referrer: str | None = None
