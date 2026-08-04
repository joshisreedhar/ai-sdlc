"""P1-01: ``ShortCode`` value-object invariants."""

from __future__ import annotations

import dataclasses

import pytest

from urlshortener.link_management.domain.errors import InvalidShortCode
from urlshortener.link_management.domain.value_objects.short_code import (
    BASE62_ALPHABET,
    MAX_SHORT_CODE_LENGTH,
    MIN_SHORT_CODE_LENGTH,
    ShortCode,
)

pytestmark = pytest.mark.unit


def test_accepts_a_base62_code_and_preserves_it_verbatim():
    assert ShortCode("aZ09xYw").value == "aZ09xYw"


@pytest.mark.parametrize(
    "length",
    [MIN_SHORT_CODE_LENGTH, MIN_SHORT_CODE_LENGTH + 1, MAX_SHORT_CODE_LENGTH],
)
def test_accepts_every_permitted_length(length):
    assert len(ShortCode("a" * length).value) == length


@pytest.mark.parametrize(
    "value",
    ["", "a", "abc", "a" * (MAX_SHORT_CODE_LENGTH + 1)],
    ids=["empty", "one-char", "below-minimum", "above-maximum"],
)
def test_rejects_a_code_outside_the_permitted_length(value):
    with pytest.raises(InvalidShortCode):
        ShortCode(value)


@pytest.mark.parametrize(
    "value",
    ["abc-123", "abc_123", "abc 123", "abc/123", "abc.123", "abc+123", "abcé12"],
)
def test_rejects_characters_outside_the_base62_alphabet(value):
    with pytest.raises(InvalidShortCode):
        ShortCode(value)


def test_the_alphabet_itself_is_a_valid_code_body():
    assert ShortCode(BASE62_ALPHABET[:MAX_SHORT_CODE_LENGTH]).value


def test_is_immutable():
    code = ShortCode("abcd123")
    with pytest.raises(dataclasses.FrozenInstanceError):
        code.value = "other"  # type: ignore[misc]


def test_equal_values_are_equal_codes():
    assert ShortCode("abcd123") == ShortCode("abcd123")
    assert ShortCode("abcd123") != ShortCode("abcd124")
