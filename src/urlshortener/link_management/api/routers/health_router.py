"""Liveness and readiness probes for the Management API (F-8).

Shipped in Phase 1 even though nothing scrapes them yet: Phase 2's Kubernetes
Deployment points its ``livenessProbe``/``readinessProbe`` at these exact paths, and
adding them later would mean re-releasing the image.

``/healthz`` answers "is this process alive?" and must stay dependency-free - a liveness
probe that fails when the database blips would restart healthy pods. ``/readyz`` answers
"can this process serve traffic?" and therefore does check dependencies, via a probe the
composition root publishes on ``app.state``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from urlshortener.link_management.api.dependencies import (
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
