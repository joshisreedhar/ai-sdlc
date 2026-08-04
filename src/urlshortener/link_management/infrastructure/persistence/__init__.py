"""PostgreSQL persistence adapters (SQLAlchemy 2.x async).

Class names here must end with ``Repository``, ``Model``, ``Table``, ``Factory`` or
``Base`` (architecture rule N-05).

[PHASE 1 / P1-01 - DEVELOPER] Create here:
    orm.py                          declarative ``LinkModel`` mapped to the ``links`` table
    engine.py                       async engine + session factory built from ``Settings``
    sqlalchemy_link_repository.py   ``SqlAlchemyLinkRepository`` implementing ``LinkRepository``

The table itself is created by an Alembic migration, never by ``metadata.create_all()``
at import time (P1-01 acceptance scenario 4).
"""
