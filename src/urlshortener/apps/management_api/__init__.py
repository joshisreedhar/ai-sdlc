"""Management API composition root.

Run: ``uvicorn urlshortener.apps.management_api.main:app --port 8000``

[PHASE 1 / P1-01 + P1-04 - DEVELOPER] Create:

``container.py``
    Build ``Settings``, the async SQLAlchemy engine/session factory, ``SystemClock``,
    ``Base62ShortCodeGenerator``, ``SqlAlchemyLinkRepository`` and ``LinkCreationService``.
    Publish the *application-level* objects on ``app.state`` so that
    ``link_management.api.dependencies`` can read them back without importing
    infrastructure (rule L-04).

``main.py``
    ``app = create_app()`` with an async lifespan that opens and closes the engine,
    ``configure_logging(settings.log_level)``, the ``link_router``, and ``/healthz`` +
    ``/readyz``. ``/readyz`` must actually check PostgreSQL (``SELECT 1``); Phase 2 points
    Kubernetes probes at these two endpoints unchanged.
"""
