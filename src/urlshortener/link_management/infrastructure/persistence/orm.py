"""SQLAlchemy declarative mapping for the ``links`` table.

Schema decisions here are load-bearing for later phases (see
``artifacts/architecture/overall_architecture.md`` section 3.4):

* a **surrogate** ``id`` primary key, so Phase 4 can widen short-code uniqueness to
  ``(domain_id, short_code)`` without rewriting foreign keys;
* ``short_code VARCHAR(64)`` with a named unique index, because Phase 4 custom aliases
  are longer than a generated code;
* ``timestamptz`` columns as the baseline for every later audit/expiry feature.

The table is created by an Alembic migration, never by ``create_all()`` - the migration
is what containers and CI run before the first request is served.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SHORT_CODE_MAX_LENGTH: int = 64


class Base(DeclarativeBase):
    """Declarative base for the link management context."""


class LinkModel(Base):
    """Row mapping for ``links``. Never leaves the infrastructure layer."""

    __tablename__ = "links"
    __table_args__ = (Index("ux_links_short_code", "short_code", unique=True),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    short_code: Mapped[str] = mapped_column(
        String(SHORT_CODE_MAX_LENGTH), nullable=False
    )
    long_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
