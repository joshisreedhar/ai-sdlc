"""P1-01: the base62 short-code generator adapter."""

from __future__ import annotations

import pytest

from urlshortener.link_management.domain.value_objects.short_code import (
    BASE62_ALPHABET,
    ShortCode,
)
from urlshortener.link_management.infrastructure.shortcode.base62_short_code_generator import (  # noqa: E501
    Base62ShortCodeGenerator,
)

pytestmark = pytest.mark.unit


def test_generates_a_short_code_of_the_configured_length():
    generator = Base62ShortCodeGenerator(length=7)

    code = generator.generate()

    assert isinstance(code, ShortCode)
    assert len(code.value) == 7


@pytest.mark.parametrize("length", [4, 6, 8, 12])
def test_honours_any_permitted_length(length):
    assert len(Base62ShortCodeGenerator(length=length).generate().value) == length


def test_uses_only_url_safe_base62_characters():
    generator = Base62ShortCodeGenerator(length=8)

    codes = [generator.generate().value for _ in range(200)]

    assert all(character in BASE62_ALPHABET for code in codes for character in code)


def test_successive_codes_are_effectively_unique():
    generator = Base62ShortCodeGenerator(length=7)

    codes = {generator.generate().value for _ in range(500)}

    assert len(codes) == 500


def test_rejects_a_length_the_short_code_value_object_would_refuse():
    with pytest.raises(ValueError):
        Base62ShortCodeGenerator(length=2)
