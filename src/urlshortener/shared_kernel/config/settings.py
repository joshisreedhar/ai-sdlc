"""Application settings, sourced from environment variables.

Every field maps to an environment variable prefixed with ``URLSHORTENER_``
(see ``.env.example``).

Usage rule: instantiate ``Settings`` **once, in the composition root**
(``urlshortener.apps.<service>.container``) and inject it downwards. Do not create a
module-level singleton and do not call ``Settings()`` from library code - that breaks
test isolation and container configuration injection.

The defaults below are *local development* defaults. Any non-local environment MUST
override at least ``URLSHORTENER_DATABASE_URL``, ``URLSHORTENER_REDIS_URL`` and
``URLSHORTENER_SHORT_URL_BASE``.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Phase 1 configuration surface.

    Later phases extend this class additively (object storage, GeoIP database path,
    rate-limit windows, OTel endpoint, ...). Never rename or repurpose an existing
    field: deployed environments already set it.
    """

    model_config = SettingsConfigDict(
        env_prefix="URLSHORTENER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # --- General ---------------------------------------------------------
    app_env: str = "local"
    log_level: str = "INFO"

    # --- Datastores ------------------------------------------------------
    database_url: str = (
        "postgresql+asyncpg://urlshortener:urlshortener@localhost:5432/urlshortener"
    )
    redis_url: str = "redis://localhost:6379/0"

    # --- Link creation (Management API) ----------------------------------
    short_url_base: str = "http://localhost:8001"
    short_code_length: int = Field(default=7, ge=4, le=32)
    short_code_max_attempts: int = Field(default=5, ge=1, le=20)

    # --- Redirection Engine ----------------------------------------------
    link_cache_ttl_seconds: int = Field(default=3600, ge=1)

    # --- Click event stream ----------------------------------------------
    click_event_stream: str = "clicks.v1"
    click_event_consumer_group: str = "analytics"
    click_stream_max_len: int = Field(default=100_000, ge=1_000)
