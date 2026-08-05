"""P1-03 Scenario 4: the stub click-event handler.

The only behaviour Phase 1 asks of the consumer is that it proves delivery by logging the
event - no User-Agent parsing, no GeoIP, no persistence, no aggregation.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from urlshortener.analytics.application.services.logging_click_event_handler import (
    LoggingClickEventHandler,
)
from urlshortener.contracts.events.click_event import ClickEvent

pytestmark = pytest.mark.unit


async def test_handling_an_event_does_not_raise():
    event = ClickEvent(short_code="abcd123", occurred_at=datetime.now(UTC))

    await LoggingClickEventHandler().handle(event)  # must not raise


async def test_logs_the_event_fields(caplog):
    event = ClickEvent(
        short_code="abcd123",
        occurred_at=datetime.now(UTC),
        client_ip="203.0.113.7",
        user_agent="pytest-agent",
        referrer="https://referrer.example",
    )

    with caplog.at_level("INFO"):
        await LoggingClickEventHandler().handle(event)

    [record] = caplog.records
    assert record.short_code == "abcd123"
    assert record.event_id == str(event.event_id)
    assert record.client_ip == "203.0.113.7"
    assert record.user_agent == "pytest-agent"
    assert record.referrer == "https://referrer.example"
