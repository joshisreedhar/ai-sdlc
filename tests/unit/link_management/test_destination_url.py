"""P1-01: ``DestinationUrl`` value-object invariants."""

from __future__ import annotations

import dataclasses

import pytest

from urlshortener.link_management.domain.errors import InvalidDestinationUrl
from urlshortener.link_management.domain.value_objects.destination_url import (
    DestinationUrl,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "value",
    [
        "http://example.com",
        "https://example.com",
        "https://example.com/",
        "https://example.com/a/deep/path?q=1&r=2#fragment",
        "https://sub.domain.example.co.uk:8443/path",
        "HTTPS://EXAMPLE.COM/Path",
    ],
)
def test_accepts_absolute_http_and_https_urls(value):
    assert DestinationUrl(value).value == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "example.com",
        "/relative/path",
        "//example.com/protocol-relative",
        "http://",
        "https:///no-host",
        "ftp://example.com/file.txt",
        "javascript:alert(1)",
        "mailto:someone@example.com",
        "file:///etc/passwd",
        "http://exa mple.com",
    ],
)
def test_rejects_anything_that_is_not_an_absolute_http_url(value):
    with pytest.raises(InvalidDestinationUrl):
        DestinationUrl(value)


def test_is_immutable():
    url = DestinationUrl("https://example.com/x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        url.value = "https://elsewhere.example.com"  # type: ignore[misc]


def test_equal_values_are_equal_urls():
    assert DestinationUrl("https://example.com/x") == DestinationUrl(
        "https://example.com/x"
    )
