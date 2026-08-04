"""Liveness and readiness probes for the Redirection Engine (F-8).

Mount order matters here: ``GET /{short_code}`` matches any single path segment, so this
router must be included **before** the redirect router or the probes become short-code
lookups. The composition root does that, and a test pins it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from urlshortener.redirection.api.dependencies import (
    ReadinessProbe,
    get_readiness_probe,
)

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    """Report that the process is running. No dependency is consulted."""
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe")
async def readyz(
    probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)],
) -> dict[str, str]:
    """Report whether required dependencies are answering."""
    if not await probe():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="dependencies unavailable",
        )
    return {"status": "ready"}
