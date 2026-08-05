"""In-memory test doubles for the analytics ports."""

from __future__ import annotations

from urlshortener.contracts.events.click_event import ClickEvent


class RecordingClickEventHandler:
    """A ``ClickEventHandler`` that records every event it is given."""

    def __init__(self) -> None:
        self.events: list[ClickEvent] = []

    async def handle(self, event: ClickEvent) -> None:
        self.events.append(event)
