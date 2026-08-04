"""The handler signature every stage of the redirect pipeline conforms to."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from urlshortener.redirection.domain.model.redirect_context import RedirectContext
from urlshortener.redirection.domain.model.redirect_decision import RedirectDecision

RedirectHandler = Callable[[RedirectContext], Awaitable[RedirectDecision]]
"""Async function turning a request context into a decision.

Both the terminal handler (``LinkResolutionService.resolve``) and the ``next_handler``
passed to an interceptor use this shape, which is what makes the chain composable.
"""
