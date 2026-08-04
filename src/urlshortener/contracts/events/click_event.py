"""Click event - the contract between the Redirection Engine and the analytics pipeline.

Phase 1 only *publishes* this event and logs it in a stub consumer. The payload is
nevertheless already rich enough for Phase 2's real pipeline (User-Agent parsing, GeoIP
resolution, referrer attribution), so that switching on analytics requires no change to
the Redirection Engine.

Forward compatibility:

* ``extra="ignore"`` means a v1 consumer can safely read a v2 event that has gained
  fields, which is what makes a rolling deploy of the consumer safe.
* ``schema_version`` is written by the producer and must be checked by any consumer that
  behaves differently across versions.
* New fields must be optional with a default. Never remove or retype an existing field.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

CLICK_EVENT_SCHEMA_VERSION: int = 1


class ClickEvent(BaseModel):
    """A single visitor click on a short link."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    schema_version: int = CLICK_EVENT_SCHEMA_VERSION
    event_id: UUID = Field(default_factory=uuid4)
    short_code: str
    occurred_at: datetime
    client_ip: str | None = None
    user_agent: str | None = None
    referrer: str | None = None
