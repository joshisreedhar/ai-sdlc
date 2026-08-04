"""``POST /links`` - the Management API's link creation endpoint (story P1-01)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from urlshortener.link_management.api.dependencies import get_link_creation_service
from urlshortener.link_management.api.schemas.link_schemas import (
    CreateLinkRequest,
    CreateLinkResponse,
)
from urlshortener.link_management.application.dto.create_link_command import (
    CreateLinkCommand,
)
from urlshortener.link_management.application.services.link_creation_service import (
    LinkCreationService,
)
from urlshortener.link_management.domain.errors import (
    InvalidDestinationUrl,
    ShortCodeGenerationExhausted,
)

UNPROCESSABLE_CONTENT: int = 422
"""HTTP 422, spelled as a literal.

Starlette renamed ``HTTP_422_UNPROCESSABLE_ENTITY`` to ``..._CONTENT`` mid-1.x and
deprecated the old name, so neither constant is safe across the supported range.
"""

router = APIRouter(tags=["links"])


@router.post(
    "/links",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateLinkResponse,
    summary="Create a short link",
)
async def create_link(
    payload: CreateLinkRequest,
    service: Annotated[LinkCreationService, Depends(get_link_creation_service)],
) -> CreateLinkResponse:
    """Shorten a destination URL and return the code plus the full short URL."""
    try:
        view = await service.create_link(CreateLinkCommand(long_url=payload.long_url))
    except InvalidDestinationUrl as error:
        raise HTTPException(
            status_code=UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except ShortCodeGenerationExhausted as error:
        # The caller did nothing wrong: the keyspace is contended right now.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not allocate a short code, please retry.",
        ) from error
    return CreateLinkResponse(short_code=view.short_code, short_url=view.short_url)
