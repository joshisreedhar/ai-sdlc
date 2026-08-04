"""P1-01 / F-11: the ``links`` table shape later phases have to extend additively.

Asserted here rather than only in a migration test because these choices are
architectural commitments (overall_architecture.md section 3.4), not incidental DDL.
"""

from __future__ import annotations

import pytest
from sqlalchemy import BigInteger, DateTime, String, Text

from urlshortener.link_management.infrastructure.persistence.orm import Base, LinkModel

pytestmark = pytest.mark.unit

TABLE = Base.metadata.tables["links"]


def test_maps_to_the_links_table():
    assert LinkModel.__tablename__ == "links"


def test_uses_a_surrogate_primary_key_rather_than_the_short_code():
    primary_key = [column.name for column in TABLE.primary_key.columns]

    assert primary_key == ["id"]
    assert isinstance(TABLE.c.id.type, BigInteger)


def test_short_code_is_varchar_64_and_not_null():
    column = TABLE.c.short_code

    assert isinstance(column.type, String)
    assert column.type.length == 64
    assert column.nullable is False


def test_long_url_is_unbounded_text_and_not_null():
    assert isinstance(TABLE.c.long_url.type, Text)
    assert TABLE.c.long_url.nullable is False


@pytest.mark.parametrize("name", ["created_at", "updated_at"])
def test_timestamps_are_timezone_aware_and_not_null(name):
    column = TABLE.c[name]

    assert isinstance(column.type, DateTime)
    assert column.type.timezone is True
    assert column.nullable is False


def test_short_code_is_uniquely_indexed():
    matching = [index for index in TABLE.indexes if index.name == "ux_links_short_code"]

    assert len(matching) == 1
    assert matching[0].unique is True
    assert [column.name for column in matching[0].columns] == ["short_code"]


def test_carries_no_later_phase_columns():
    assert set(TABLE.c.keys()) == {
        "id",
        "short_code",
        "long_url",
        "created_at",
        "updated_at",
    }
