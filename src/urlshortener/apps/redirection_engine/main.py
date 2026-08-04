"""Redirection Engine process entry point.

Run with ``uvicorn urlshortener.apps.redirection_engine.main:app``.
"""

from __future__ import annotations

from fastapi import FastAPI

from urlshortener.apps.redirection_engine.container import create_app
from urlshortener.shared_kernel.config.settings import Settings
from urlshortener.shared_kernel.logging.structured_logging import configure_logging


def bootstrap() -> FastAPI:
    """Read configuration once, install logging and build the application."""
    settings = Settings()
    configure_logging(settings.log_level)
    return create_app(settings)


app = bootstrap()
