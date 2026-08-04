"""Redirection use cases.

Class names must end with ``Service`` or ``Dispatcher`` (architecture rule N-03).

[PHASE 1 / P1-02 - DEVELOPER] ``LinkResolutionService``
    ``async resolve(context: RedirectContext) -> RedirectDecision`` - the pipeline's
    terminal handler. Cache first, PostgreSQL on miss, cache fill, then
    ``RedirectToDestination`` or ``LinkNotFound``. A Redis failure degrades to the
    database path; it never fails the request.

[PHASE 1 / P1-03 - DEVELOPER] ``ClickEventDispatcher``
    ``async dispatch(context: RedirectContext) -> None`` - builds the ``ClickEvent`` and
    publishes it. Must catch every exception except ``asyncio.CancelledError``, log at
    WARNING, and return normally. It is invoked *after* the response is written and must
    never be awaited inline in the request path.
"""
