"""``GET /{short_code}`` - the redirect hot path (story P1-02).

Two structural commitments live in this module and must survive every later phase:

1. The router calls ``RedirectPipeline.execute``, never the resolution service directly,
   so Phase 3 interceptors slot in without touching this file (rule P-04).
2. Decisions are mapped **by type**. A decision subclass added in a later phase without a
   matching branch raises rather than silently falling through to a redirect, which is
   why the fallthrough is a hard failure and not a default 404.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from starlette.background import BackgroundTask

from urlshortener.redirection.api.dependencies import (
    get_click_event_dispatcher,
    get_clock,
    get_redirect_pipeline,
)
from urlshortener.redirection.application.pipeline.redirect_pipeline import (
    RedirectPipeline,
)
from urlshortener.redirection.application.services.click_event_dispatcher import (
    ClickEventDispatcher,
)
from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.model.redirect_decision import (
    LinkNotFound,
    RedirectDecision,
    RedirectToDestination,
)
from urlshortener.shared_kernel.logging.structured_logging import get_logger
from urlshortener.shared_kernel.time.clock import Clock

logger = get_logger(__name__)

FORWARDED_FOR_HEADER = "x-forwarded-for"
NO_STORE_HEADERS = {"Cache-Control": "no-store"}
"""Keeps intermediaries from serving the redirect from their own cache.

Without it a CDN or corporate proxy could satisfy later clicks itself, suppressing the
click events the analytics promise depends on and hiding Phase 3 destination changes.
"""

router = APIRouter(tags=["redirect"])


@router.get(
    "/{short_code}",
    summary="Resolve a short code and redirect",
    response_class=RedirectResponse,
    responses={302: {"description": "Redirect to the destination"}, 404: {}},
)
async def redirect(
    short_code: str,
    request: Request,
    pipeline: Annotated[RedirectPipeline, Depends(get_redirect_pipeline)],
    clock: Annotated[Clock, Depends(get_clock)],
    click_event_dispatcher: Annotated[
        ClickEventDispatcher, Depends(get_click_event_dispatcher)
    ],
) -> Response:
    """Resolve ``short_code`` through the pipeline and map the decision to a response."""
    context = build_redirect_context(short_code, request, clock)
    decision = await pipeline.execute(context)
    return to_response(decision, context, click_event_dispatcher)


def build_redirect_context(
    short_code: str, request: Request, clock: Clock
) -> RedirectContext:
    """Reduce the framework request to the immutable facts the pipeline may see.

    Every field is populated even though Phase 1 reads only ``short_code``: Phase 2's
    analytics and Phase 3's routing rules need them, and re-instrumenting the hot path
    later would be a far more invasive change than carrying them now.
    """
    return RedirectContext(
        short_code=short_code,
        requested_at=clock.now(),
        client_ip=client_ip_of(request),
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    )


def client_ip_of(request: Request) -> str | None:
    """First hop of ``X-Forwarded-For`` when proxied, otherwise the peer address."""
    forwarded_for = request.headers.get(FORWARDED_FOR_HEADER)
    if forwarded_for:
        first_hop = forwarded_for.split(",")[0].strip()
        if first_hop:
            return first_hop
    return request.client.host if request.client else None


def to_response(
    decision: RedirectDecision,
    context: RedirectContext,
    click_event_dispatcher: ClickEventDispatcher,
) -> Response:
    """Map a decision type to its HTTP response.

    On a successful redirect, the click event is scheduled as a ``BackgroundTask`` -
    Starlette runs it only *after* the response has been sent, so publishing to the
    broker never delays the redirect (P1-03 Scenario 3).
    """
    match decision:
        case RedirectToDestination():
            return RedirectResponse(
                url=decision.destination_url,
                status_code=decision.status_code,
                headers=NO_STORE_HEADERS,
                background=BackgroundTask(click_event_dispatcher.dispatch, context),
            )
        case LinkNotFound():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found"
            )
        case _:
            logger.error(
                "unmapped_redirect_decision",
                extra={"decision": type(decision).__name__},
            )
            raise NotImplementedError(
                f"no HTTP mapping for decision {type(decision).__name__}"
            )
