"""P1-03: fire-and-forget click event publishing.

``ClickEventDispatcher`` is the boundary that guarantees a broker outage can never
surface to a visitor: every failure raised by the publisher is caught here, logged and
swallowed, except cancellation.
"""

from __future__ import annotations

import asyncio

import pytest

from tests.unit.redirection.fakes import FrozenClock
from urlshortener.contracts.events.click_event import ClickEvent
from urlshortener.redirection.application.services.click_event_dispatcher import (
    ClickEventDispatcher,
)
from urlshortener.redirection.domain.model.redirect_context import RedirectContext

pytestmark = pytest.mark.unit


class RecordingPublisher:
    """Stands in for a ``ClickEventPublisher``, optionally raising on publish."""

    def __init__(self, raises: BaseException | None = None) -> None:
        self.events: list[ClickEvent] = []
        self._raises = raises

    async def publish(self, event: ClickEvent) -> None:
        self.events.append(event)
        if self._raises is not None:
            raise self._raises


def _context(short_code: str = "abcd123") -> RedirectContext:
    return RedirectContext(
        short_code=short_code,
        requested_at=FrozenClock().now(),
        client_ip="203.0.113.7",
        user_agent="pytest-agent",
        referrer="https://referrer.example",
    )


async def test_builds_a_click_event_from_the_context_and_publishes_it():
    publisher = RecordingPublisher()
    context = _context()

    await ClickEventDispatcher(publisher).dispatch(context)

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.short_code == "abcd123"
    assert event.occurred_at == context.requested_at
    assert event.client_ip == "203.0.113.7"
    assert event.user_agent == "pytest-agent"
    assert event.referrer == "https://referrer.example"


async def test_a_connection_failure_is_logged_and_swallowed():
    publisher = RecordingPublisher(raises=ConnectionError("broker unreachable"))

    await ClickEventDispatcher(publisher).dispatch(_context())  # must not raise


async def test_an_unexpected_exception_type_is_also_swallowed():
    publisher = RecordingPublisher(raises=RuntimeError("boom"))

    await ClickEventDispatcher(publisher).dispatch(_context())  # must not raise


async def test_cancellation_is_not_swallowed():
    publisher = RecordingPublisher(raises=asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ClickEventDispatcher(publisher).dispatch(_context())
