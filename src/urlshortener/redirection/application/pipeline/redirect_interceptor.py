"""``RedirectInterceptor`` - the contract every future redirect rule implements.

DO NOT IMPLEMENT THIS PROTOCOL IN PHASE 1 (architecture rule P-02).

An interceptor may:

* short-circuit, by returning a ``RedirectDecision`` without calling ``next_handler``
  (for example an expired link);
* delegate and then adjust, by awaiting ``next_handler(context)`` and returning a
  modified decision (for example a geo/device destination override);
* delegate untouched, by returning ``await next_handler(context)``.

An interceptor must be pure with respect to the context: it never mutates
``RedirectContext`` (it is frozen) and never writes to the system of record.
"""

from __future__ import annotations

from typing import Protocol

from urlshortener.redirection.application.pipeline.redirect_handler import (
    RedirectHandler,
)
from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.model.redirect_decision import RedirectDecision


class RedirectInterceptor(Protocol):
    """A single stage in the redirect pipeline."""

    async def intercept(
        self,
        context: RedirectContext,
        next_handler: RedirectHandler,
    ) -> RedirectDecision:
        """Handle the request, optionally delegating to ``next_handler``."""
        ...
