"""HTTP layer for the Management API.

May import ``application``, ``domain``, ``shared_kernel`` and ``contracts``.
Must NOT import ``infrastructure`` or ``apps`` (architecture rule L-04): concrete
adapters are built in the composition root and read back from ``app.state`` in
``dependencies.py``, typed as the application/domain abstraction.

[PHASE 1 / P1-01 - DEVELOPER] Create here:
    dependencies.py             FastAPI ``Depends`` providers reading ``request.app.state``
    schemas/link_schemas.py     ``CreateLinkRequest`` / ``CreateLinkResponse``
    routers/link_router.py      ``POST /links``
"""
