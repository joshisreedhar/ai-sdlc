"""FastAPI dependency accessors for the Management API.

Collaborators are built once in ``apps.management_api.container`` and published on
``app.state``; this module hands them back typed as the *application* abstraction. That
is what keeps the API layer free of any adapter import (architecture rule L-04) and
testable by assigning a fake to ``app.state``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request

from urlshortener.link_management.application.services.link_creation_service import (
    LinkCreationService,
)

ReadinessProbe = Callable[[], Awaitable[bool]]
"""Answers "can this process serve traffic?" - dependency checks live in the root."""


def get_link_creation_service(request: Request) -> LinkCreationService:
    """Return the link creation use case published by the composition root."""
    service: LinkCreationService = request.app.state.link_creation_service
    return service


def get_readiness_probe(request: Request) -> ReadinessProbe:
    """Return the readiness probe published by the composition root."""
    probe: ReadinessProbe = request.app.state.readiness_probe
    return probe
