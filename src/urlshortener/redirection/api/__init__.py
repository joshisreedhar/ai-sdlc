"""HTTP layer for the Redirection Engine.

[PHASE 1 / P1-02 - DEVELOPER] Create here:
    dependencies.py                 providers reading ``request.app.state``
    routers/redirect_router.py      ``GET /{short_code}``

The router must:

1. build a fully populated ``RedirectContext`` (short code, client IP, User-Agent,
   referrer, ``Clock.now()``);
2. call ``RedirectPipeline.execute(context)`` - never ``LinkResolutionService`` directly
   (architecture rule P-04);
3. map the returned ``RedirectDecision`` **by type** to a response:
   ``RedirectToDestination`` -> 302 + ``Location`` + ``Cache-Control: no-store``,
   ``LinkNotFound`` -> 404. Write the mapping so a new decision subclass added in Phase 3
   is a new branch, not an edit to an existing one;
4. schedule ``ClickEventDispatcher.dispatch`` so it runs *after* the response is written
   (``starlette.background.BackgroundTask`` on the response, or ``asyncio.create_task``
   with a retained reference). Never ``await`` it inline.

Register the catch-all ``GET /{short_code}`` route LAST, after ``/healthz`` and
``/readyz``, or it will shadow them.
"""
