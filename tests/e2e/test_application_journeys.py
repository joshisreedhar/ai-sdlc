"""Black-box, multi-process E2E coverage for the Phase 1 application-level user
journeys (P1-01, P1-02, P1-03).

Unlike ``tests/integration/**`` (which drives each FastAPI app in-process through
``httpx.ASGITransport``) and ``tests/e2e/test_docker_compose_stack.py`` (which proves
the *containers* for P1-04 boot and wire together), this module treats the system the
way a real consumer would: three independently running OS processes (Management API,
Redirection Engine, Click Consumer), talking to each other only over real sockets
(HTTP and Redis), backed by a real PostgreSQL database migrated with Alembic. Nothing
here imports application code directly except tiny helpers (``ClickEvent``, settings
env-var names) needed to assert on the wire contract.

Requires a reachable PostgreSQL and Redis (``us-pg``/``us-redis`` per
``scripts/run_local.sh``, or any instance reachable via the
``URLSHORTENER_DATABASE_URL`` / ``URLSHORTENER_REDIS_URL`` environment variables).
Opt-in, like the rest of ``tests/e2e``: ``pytest -m e2e tests/e2e``.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import redis.asyncio as redis_asyncio

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://urlshortener:urlshortener@localhost:5432/urlshortener"
)
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

STARTUP_TIMEOUT_SECONDS = 30.0
CONSUMER_STARTUP_GRACE_SECONDS = 1.0


def _database_url() -> str:
    return os.environ.get("URLSHORTENER_DATABASE_URL", DEFAULT_DATABASE_URL)


def _redis_url() -> str:
    return os.environ.get("URLSHORTENER_REDIS_URL", DEFAULT_REDIS_URL)


def _database_is_reachable(url: str) -> bool:
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def probe() -> bool:
        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
        finally:
            await engine.dispose()

    return asyncio.run(probe())


def _redis_is_reachable(url: str) -> bool:
    import asyncio

    async def probe() -> bool:
        client = redis_asyncio.from_url(url)
        try:
            await client.ping()
            return True
        except Exception:
            return False
        finally:
            await client.aclose()

    return asyncio.run(probe())


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _StreamingProcess:
    """A subprocess whose stdout/stderr is tailed into an in-memory buffer.

    Needed because the Click Consumer has no HTTP readiness endpoint - readiness is
    observed by watching its structured logs for the startup line, and test
    assertions later grep the same buffer for the log line the consumer emits per
    processed event.
    """

    def __init__(self, command: list[str], env: dict[str, str]) -> None:
        self.process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.lines: list[str] = []
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            with self._lock:
                self.lines.append(line)

    def output(self) -> str:
        with self._lock:
            return "".join(self.lines)

    def wait_for(self, needle: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if needle in self.output():
                return
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"process exited early (code {self.process.returncode}) "
                    f"before logging {needle!r}:\n{self.output()}"
                )
            time.sleep(0.05)
        raise TimeoutError(f"never saw {needle!r} in output:\n{self.output()}")

    def stop(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)
        self._thread.join(timeout=5)


def _wait_until_ready(url: str, deadline: float, process: _StreamingProcess) -> None:
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.process.poll() is not None:
            raise RuntimeError(
                f"process exited early (code {process.process.returncode}) "
                f"while waiting for {url}:\n{process.output()}"
            )
        try:
            response = httpx.get(url, timeout=2)
            if response.status_code == 200:
                return
        except httpx.HTTPError as error:
            last_error = error
        time.sleep(0.2)
    raise TimeoutError(f"{url} never became ready") from last_error


@pytest.fixture(scope="module")
def infra() -> tuple[str, str]:
    database_url = _database_url()
    redis_url = _redis_url()
    if not _database_is_reachable(database_url):
        pytest.skip(
            f"PostgreSQL is not reachable at {database_url} "
            "(try `podman start us-pg` per scripts/run_local.sh)"
        )
    if not _redis_is_reachable(redis_url):
        pytest.skip(
            f"Redis is not reachable at {redis_url} "
            "(try `podman start us-redis` per scripts/run_local.sh)"
        )
    return database_url, redis_url


@pytest.fixture(scope="module")
def migrated_database(infra: tuple[str, str]) -> str:
    """Bring the schema to head with Alembic, the same command the containers run."""
    from alembic import command
    from alembic.config import Config

    database_url, _ = infra
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return database_url


@pytest.fixture(scope="module")
def live_stack(
    migrated_database: str, infra: tuple[str, str]
) -> Iterator[dict[str, str]]:
    """Start the Management API, Redirection Engine and Click Consumer as three real,
    independently running OS processes wired to real PostgreSQL/Redis, exactly the way
    ``scripts/run_local.sh`` does for manual testing - only the Click Consumer is added
    here so the full P1-03 publish-to-consume path is exercised black-box.

    A per-run stream/consumer-group name keeps this module isolated from any other
    Click Consumer that might already be running locally or via docker-compose.
    """
    _, redis_url = infra
    run_id = uuid.uuid4().hex[:8]
    stream = f"test.e2e.clicks.{run_id}"
    consumer_group = f"test-e2e-analytics-{run_id}"

    management_port = _free_port()
    redirection_port = _free_port()

    base_env = {
        **os.environ,
        "URLSHORTENER_DATABASE_URL": migrated_database,
        "URLSHORTENER_REDIS_URL": redis_url,
        "URLSHORTENER_CLICK_EVENT_STREAM": stream,
        "URLSHORTENER_CLICK_EVENT_CONSUMER_GROUP": consumer_group,
        "PYTHONUNBUFFERED": "1",
    }

    management_env = {
        **base_env,
        "URLSHORTENER_SHORT_URL_BASE": f"http://localhost:{management_port}",
    }

    processes: list[_StreamingProcess] = []
    try:
        management_api = _StreamingProcess(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "urlshortener.apps.management_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(management_port),
            ],
            env=management_env,
        )
        processes.append(management_api)

        redirection_engine = _StreamingProcess(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "urlshortener.apps.redirection_engine.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(redirection_port),
            ],
            env=base_env,
        )
        processes.append(redirection_engine)

        click_consumer = _StreamingProcess(
            [sys.executable, "-m", "urlshortener.apps.click_consumer.main"],
            env=base_env,
        )
        processes.append(click_consumer)

        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        _wait_until_ready(
            f"http://localhost:{management_port}/readyz", deadline, management_api
        )
        _wait_until_ready(
            f"http://localhost:{redirection_port}/readyz", deadline, redirection_engine
        )
        # The consumer group is created at "$" (see RedisStreamClickEventSubscriber):
        # it only sees events published after the group exists. Wait for the
        # composition root's startup log line, then a short grace period for the
        # XGROUP CREATE round-trip to complete server-side before any test publishes.
        click_consumer.wait_for("click_consumer_started", STARTUP_TIMEOUT_SECONDS)
        time.sleep(CONSUMER_STARTUP_GRACE_SECONDS)

        yield {
            "management_api_url": f"http://localhost:{management_port}",
            "redirection_engine_url": f"http://localhost:{redirection_port}",
            "redis_url": redis_url,
            "stream": stream,
            "consumer_group": consumer_group,
            "click_consumer_output": click_consumer,  # type: ignore[dict-item]
        }
    finally:
        for process in reversed(processes):
            with contextlib.suppress(Exception):
                process.stop()


@pytest.fixture()
async def clean_links_table(migrated_database: str) -> None:
    """Each test creates its own link(s); truncating keeps runs independent without
    needing to restart the long-lived ``live_stack`` processes between tests."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(migrated_database)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("TRUNCATE TABLE links RESTART IDENTITY"))
    finally:
        await engine.dispose()


async def test_a_link_created_via_the_management_api_redirects_via_the_redirection_engine(
    live_stack, clean_links_table
):
    """The core Phase 1 product loop (P1-01 + P1-02): create, then successfully
    redirect, across two independently running processes."""
    destination = "https://example.com/e2e/create-then-redirect?ref=qa"

    async with httpx.AsyncClient() as client:
        created = await client.post(
            f"{live_stack['management_api_url']}/links",
            json={"long_url": destination},
        )
        assert created.status_code == 201
        body = created.json()
        short_code = body["short_code"]
        assert body["short_url"] == f"{live_stack['management_api_url']}/{short_code}"

        redirected = await client.get(
            f"{live_stack['redirection_engine_url']}/{short_code}",
            follow_redirects=False,
        )

    assert redirected.status_code == 302
    assert redirected.headers["location"] == destination


async def test_redirecting_an_unknown_short_code_returns_404(live_stack):
    """P1-02 Scenario 3: an unknown short code is a 404, not a redirect."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{live_stack['redirection_engine_url']}/does-not-exist-e2e",
            follow_redirects=False,
        )

    assert response.status_code == 404
    assert "location" not in response.headers


async def test_a_click_event_is_published_and_consumed_without_blocking_the_redirect(
    live_stack, clean_links_table
):
    """P1-03 Scenarios 1, 3 and 4, proven across real, independently running
    processes: the redirect completes fast without waiting on the broker, and the
    separately running Click Consumer process observes and acknowledges the event."""
    destination = "https://example.com/e2e/click-event"

    async with httpx.AsyncClient() as client:
        created = await client.post(
            f"{live_stack['management_api_url']}/links",
            json={"long_url": destination},
        )
        short_code = created.json()["short_code"]

        started_at = time.monotonic()
        redirected = await client.get(
            f"{live_stack['redirection_engine_url']}/{short_code}",
            follow_redirects=False,
        )
        elapsed_seconds = time.monotonic() - started_at

    assert redirected.status_code == 302
    # Generous ceiling: the point is proving the response isn't gated on broker
    # round-trips/consumer processing, not asserting a strict latency SLA.
    assert elapsed_seconds < 2.0

    # The stub consumer is a separate OS process; give its poll loop a moment to pick
    # the event up and log it, then assert it was received and fully acknowledged
    # (XPENDING back to zero) rather than merely published.
    consumer_output = live_stack["click_consumer_output"]
    consumer_output.wait_for(short_code, timeout=5.0)
    assert '"message": "click_event_received"' in consumer_output.output()

    redis_client = redis_asyncio.from_url(
        live_stack["redis_url"], decode_responses=True
    )
    try:
        deadline = time.monotonic() + 5.0
        pending = -1
        while time.monotonic() < deadline:
            pending_info = await redis_client.xpending(
                live_stack["stream"], live_stack["consumer_group"]
            )
            pending = pending_info["pending"]
            if pending == 0:
                break
            await asyncio.sleep(0.1)
        assert pending == 0
    finally:
        await redis_client.aclose()


async def test_an_unknown_short_code_never_reaches_the_click_consumer(live_stack):
    """A 404 must never masquerade as a click for the future analytics pipeline."""
    consumer_output = live_stack["click_consumer_output"]
    before = consumer_output.output()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{live_stack['redirection_engine_url']}/still-does-not-exist-e2e",
            follow_redirects=False,
        )

    assert response.status_code == 404
    # Give any (incorrect) publish a moment to surface before asserting its absence.
    await asyncio.sleep(0.5)
    after = consumer_output.output()
    assert "still-does-not-exist-e2e" not in after[len(before) :]
