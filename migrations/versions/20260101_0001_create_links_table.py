"""create links table

Revision ID: 0001_create_links_table
Revises:
Create Date: 2026-01-01

The Phase 1 schema. Key shape decisions (overall_architecture.md section 3.4):

* surrogate ``id`` primary key - Phase 4 widens short-code uniqueness to
  ``(domain_id, short_code)`` without rewriting foreign keys;
* ``short_code VARCHAR(64)`` - Phase 4 custom aliases are longer than generated codes;
* named unique index ``ux_links_short_code`` - the concurrent-insert guard the link
  creation service relies on.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_create_links_table"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "links",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("short_code", sa.String(length=64), nullable=False),
        sa.Column("long_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_links"),
    )
    op.create_index("ux_links_short_code", "links", ["short_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_links_short_code", table_name="links")
    op.drop_table("links")
