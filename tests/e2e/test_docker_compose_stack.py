"""P1-04 Scenario 2: the full stack, started only from containers, does the round trip.

Brings up ``docker-compose.yml`` with a real compose provider (``docker compose`` if
present, otherwise ``podman compose``), creates a link through the containerized
Management API and resolves it through the containerized Redirection Engine - proving
the images this phase ships are independently deployable.

This is deliberately excluded from the default ``pytest`` run (see the ``-m "not e2e"``
default in ``pyproject.toml``): it needs a working container runtime, builds three
images and binds the same host ports (5432, 6379, 8001, 8002) the manual dev script
uses, so it must not be running at the same time as ``scripts/run_local.sh`` or another
compose stack. Run it explicitly with ``pytest -m e2e tests/e2e``.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_NAME = "urlshortener-e2e"
MANAGEMENT_API_URL = "http://localhost:8001"
REDIRECTION_ENGINE_URL = "http://localhost:8002"
STARTUP_TIMEOUT_SECONDS = 180


def _compose_command() -> list[str] | None:
    """Prefer a real Docker Engine; fall back to Podman's compose provider."""
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("podman"):
        return ["podman", "compose"]
    return None


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True, capture_output=True, text=True)


def _wait_until_ready(url: str, deadline: float) -> None:
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=2)
            if response.status_code == 200:
                return
        except httpx.HTTPError as error:
            last_error = error
        time.sleep(1)
    raise TimeoutError(f"{url} never became ready") from last_error


@pytest.fixture(scope="module")
def compose_stack() -> Iterator[None]:
    compose = _compose_command()
    if compose is None:
        pytest.skip("neither docker nor podman is available")

    base = [*compose, "-f", str(REPO_ROOT / "docker-compose.yml"), "-p", PROJECT_NAME]
    try:
        _run([*base, "up", "-d", "--build"])
    except subprocess.CalledProcessError as error:
        pytest.fail(f"compose up failed: {error.stderr}")

    try:
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        _wait_until_ready(f"{MANAGEMENT_API_URL}/readyz", deadline)
        _wait_until_ready(f"{REDIRECTION_ENGINE_URL}/readyz", deadline)
        yield
    finally:
        _run([*base, "down", "-v"])


def test_a_link_created_through_the_containerized_api_redirects_end_to_end(
    compose_stack,
):
    destination = "https://example.com/e2e-round-trip"

    created = httpx.post(
        f"{MANAGEMENT_API_URL}/links", json={"long_url": destination}, timeout=5
    )
    assert created.status_code == 201
    short_code = created.json()["short_code"]

    redirected = httpx.get(
        f"{REDIRECTION_ENGINE_URL}/{short_code}", follow_redirects=False, timeout=5
    )
    assert redirected.status_code == 302
    assert redirected.headers["location"] == destination
