"""Transport schemas for the Management API link endpoints.

The request is validated with Pydantic so that a malformed payload is rejected with a
422 before any domain object is constructed (P1-01 acceptance scenario 2). The submitted
URL is nevertheless carried through as the **exact string the caller sent**: a shortener
that silently normalises its input would redirect visitors somewhere subtly different
from what was requested.
"""

from __future__ import annotations

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    TypeAdapter,
    ValidationError,
    field_validator,
)

_ABSOLUTE_HTTP_URL: TypeAdapter[AnyHttpUrl] = TypeAdapter(AnyHttpUrl)


class CreateLinkRequest(BaseModel):
    """``POST /links`` request body."""

    model_config = ConfigDict(extra="forbid")

    long_url: str

    @field_validator("long_url")
    @classmethod
    def _must_be_an_absolute_http_url(cls, value: str) -> str:
        try:
            _ABSOLUTE_HTTP_URL.validate_python(value)
        except ValidationError as error:
            raise ValueError("must be an absolute http(s) URL") from error
        return value


class CreateLinkResponse(BaseModel):
    """``POST /links`` response body."""

    model_config = ConfigDict(frozen=True)

    short_code: str
    short_url: str
