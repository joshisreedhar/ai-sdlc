"""Redirection Engine composition root.

Run: ``uvicorn urlshortener.apps.redirection_engine.main:app --port 8001``

[PHASE 1 / P1-02 + P1-03 + P1-04 - DEVELOPER] Create:

``container.py``
    Build ``Settings``, the Redis client, the read-only async SQLAlchemy engine,
    ``SystemClock``, ``RedisLinkCache``, ``SqlAlchemyLinkReadRepository``,
    ``RedisStreamClickEventPublisher``, ``LinkResolutionService``,
    ``ClickEventDispatcher``, and finally::

        pipeline = RedirectPipeline(
            terminal_handler=resolution_service.resolve,
            interceptors=(),   # PHASE 1: intentionally empty. Phase 3 registers here.
        )

    Keep the ``interceptors=()`` argument explicit rather than relying on the default -
    it is the marker that tells the Phase 3 developer exactly where to add rules.

``main.py``
    ``app = create_app()`` with lifespan management for the Redis and database clients,
    ``configure_logging``, ``/healthz``, ``/readyz`` (checks Redis and PostgreSQL), and the
    ``redirect_router`` mounted LAST so its catch-all ``/{short_code}`` route does not
    shadow the health endpoints.

    Phase 3 mounts IP/bot filtering middleware here, ahead of the router. Leave the
    middleware list empty in Phase 1.
"""
