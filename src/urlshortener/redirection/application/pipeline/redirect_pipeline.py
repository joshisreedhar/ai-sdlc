"""``RedirectPipeline`` - composes interceptors around a terminal handler.

Provided by the Architect as fixed infrastructure for the Phase 3/4 extension seam.
Phase 1 constructs it with an empty interceptor sequence and does not modify this file.
"""

from __future__ import annotations

from collections.abc import Sequence

from urlshortener.redirection.application.pipeline.redirect_handler import (
    RedirectHandler,
)
from urlshortener.redirection.application.pipeline.redirect_interceptor import (
    RedirectInterceptor,
)
from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.model.redirect_decision import RedirectDecision


class RedirectPipeline:
    """Runs the registered interceptors in order, then the terminal handler.

    The chain is composed once at construction time, not per request, so the hot path
    costs one ``await`` per registered interceptor and nothing else.

    Example (Phase 1 - no interceptors)::

        pipeline = RedirectPipeline(
            terminal_handler=resolution_service.resolve,
            interceptors=(),
        )

    Example (Phase 3 - order is significant, defined in the composition root)::

        pipeline = RedirectPipeline(
            terminal_handler=resolution_service.resolve,
            interceptors=(expiration, password_gate, geo_device_routing),
        )
    """

    def __init__(
        self,
        terminal_handler: RedirectHandler,
        interceptors: Sequence[RedirectInterceptor] = (),
    ) -> None:
        self._terminal_handler = terminal_handler
        self._interceptors: tuple[RedirectInterceptor, ...] = tuple(interceptors)
        self._entrypoint: RedirectHandler = self._compose()

    @property
    def interceptors(self) -> tuple[RedirectInterceptor, ...]:
        """The registered interceptors, in execution order."""
        return self._interceptors

    async def execute(self, context: RedirectContext) -> RedirectDecision:
        """Run the pipeline for one request."""
        return await self._entrypoint(context)

    def _compose(self) -> RedirectHandler:
        handler = self._terminal_handler
        for interceptor in reversed(self._interceptors):
            handler = self._wrap(interceptor, handler)
        return handler

    @staticmethod
    def _wrap(
        interceptor: RedirectInterceptor,
        next_handler: RedirectHandler,
    ) -> RedirectHandler:
        async def _invoke(context: RedirectContext) -> RedirectDecision:
            return await interceptor.intercept(context, next_handler)

        return _invoke
