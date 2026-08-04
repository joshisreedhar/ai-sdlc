"""Injectable clock."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Source of the current time. Always timezone-aware, always UTC."""

    def now(self) -> datetime:
        """Return the current instant as a timezone-aware UTC ``datetime``."""
        ...


class SystemClock:
    """Production ``Clock`` backed by the system wall clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)
