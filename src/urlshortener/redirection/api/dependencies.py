"""FastAPI dependency accessors for the Redirection Engine.

Note what is deliberately absent: there is no accessor for ``LinkResolutionService``.
The router must reach resolution *through* ``RedirectPipeline`` so that Phase 3's
interceptors cannot be silently bypassed on the highest-traffic path in the product
(architecture rule P-04).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request

from urlshortener.redirection.application.pipeline.redirect_pipeline import (
    RedirectPipeline,
)
from urlshortener.redirection.application.services.click_event_dispatcher import (
    ClickEventDispatcher,
)
from urlshortener.shared_kernel.time.clock import Clock

ReadinessProbe = Callable[[], Awaitable[bool]]
"""Answers "can this process serve traffic?" - dependency checks live in the root."""


def get_redirect_pipeline(request: Request) -> RedirectPipeline:
    """Return the redirect pipeline published by the composition root."""
    pipeline: RedirectPipeline = request.app.state.redirect_pipeline
    return pipeline


def get_click_event_dispatcher(request: Request) -> ClickEventDispatcher:
    """Return the click event dispatcher published by the composition root."""
    dispatcher: ClickEventDispatcher = request.app.state.click_event_dispatcher
    return dispatcher


def get_clock(request: Request) -> Clock:
    """Return the clock published by the composition root."""
    clock: Clock = request.app.state.clock
    return clock


def get_readiness_probe(request: Request) -> ReadinessProbe:
    """Return the readiness probe published by the composition root."""
    probe: ReadinessProbe = request.app.state.readiness_probe
    return probe
