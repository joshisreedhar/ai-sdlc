"""URL Shortener & Analytics Platform.

Top-level package. The structure is a *modular monolith of bounded contexts* that is
deployed as several independent processes:

    shared_kernel/    cross-cutting primitives (settings, logging, clock, base errors)
    contracts/        versioned cross-process wire schemas (click events, ...)
    link_management/  BOUNDED CONTEXT - write side: creating and managing links
    redirection/      BOUNDED CONTEXT - read/hot path: resolving a short code and redirecting
    analytics/        BOUNDED CONTEXT - click ingestion and (from Phase 2) analytics
    apps/             composition roots, one per deployable process

Hard rules (statically enforced by ``tests/architecture``):

* Bounded contexts never import each other. They share only ``contracts`` and ``shared_kernel``.
* Within a context: ``api`` -> ``application`` -> ``domain``; ``infrastructure`` -> ``domain`` only.
* ``domain`` and ``application`` are framework-free (no fastapi/sqlalchemy/redis/celery).
* Concrete adapters are instantiated *only* in ``apps/<service>/container.py``.

See ``artifacts/architecture/overall_architecture.md`` for the full rationale and
``artifacts/architecture/<phase>/`` for what is in scope for the phase you are building.
"""

__all__: list[str] = []
