"""Phase boundary rules P-01 .. P-05 for phase_1_mvp.

Specification: artifacts/architecture/phase_1_mvp/archunit_specs.md, section 4.

These rules stop Phase 1 from accidentally implementing later-phase behaviour. The phase
that legitimately introduces a feature is expected to relax or delete the matching rule -
that deletion is a deliberate, reviewable act, which is the point.
"""

from __future__ import annotations

import pytest

from tests.architecture._arch import (
    PACKAGE_NAME,
    PACKAGE_ROOT,
    classes_of,
    context_of,
    describe,
    imports_of,
    is_within,
    iter_modules,
    root_package_of,
)

pytestmark = pytest.mark.architecture

MIDDLEWARE_DIR = PACKAGE_ROOT / "redirection" / "api" / "middleware"
INTERCEPTOR_PROTOCOL_MODULE = (
    f"{PACKAGE_NAME}.redirection.application.pipeline.redirect_interceptor"
)
REDIRECTION_API = f"{PACKAGE_NAME}.redirection.api"
RESOLUTION_SERVICE_MODULE = (
    f"{PACKAGE_NAME}.redirection.application.services.link_resolution_service"
)

# Libraries that belong to later phases. Importing one early is the clearest possible
# signal that work has leaked across a phase boundary.
FUTURE_PHASE_LIBRARIES: frozenset[str] = frozenset(
    {
        "celery",  # Phase 2 - async analytics pipeline
        "user_agents",  # Phase 2 - User-Agent parsing
        "ua_parser",  # Phase 2 - User-Agent parsing
        "geoip2",  # Phase 2/3 - GeoIP resolution
        "maxminddb",  # Phase 2/3 - GeoIP resolution
        "prometheus_client",  # Phase 2/6 - metrics
        "opentelemetry",  # Phase 2/6 - tracing
        "boto3",  # Phase 4 - object storage for QR codes
        "segno",  # Phase 4 - QR code generation
        "qrcode",  # Phase 4 - QR code generation
        "jinja2",  # Phase 4/6 - interstitial and Link-in-Bio pages
    }
)


def test_middleware_package_is_reserved_and_empty():
    """P-01: the Phase 3 filtering mount point exists and stays empty."""
    assert MIDDLEWARE_DIR.is_dir(), (
        "P-01 redirection/api/middleware/ must exist in Phase 1 as the reserved mount "
        "point for Phase 3 IP and bot filtering."
    )
    unexpected = sorted(
        path.name
        for path in MIDDLEWARE_DIR.iterdir()
        if path.is_file() and path.name != "__init__.py"
    )
    assert not unexpected, describe(
        unexpected,
        "P-01 IP/bot filtering middleware is Phase 3 scope. The package is reserved "
        "now so that Phase 3 does not have to restructure the request path.",
    )


def test_no_interceptor_implementations_in_phase_1():
    """P-02: the redirect pipeline runs zero interceptors in Phase 1."""
    violations: list[str] = []
    for module in iter_modules():
        if module.name == INTERCEPTOR_PROTOCOL_MODULE:
            continue
        for class_def in classes_of(module):
            if class_def.name.endswith("Interceptor"):
                violations.append(f"{module.location}: {class_def.name}")
    assert not violations, describe(
        violations,
        "P-02 Expiration, password gating and geo/device routing are Phase 3. Phase 1 "
        "delivers the seam, not the rules.",
    )


def test_no_future_phase_dependencies():
    """P-03: no later-phase library may be imported yet."""
    violations: list[str] = []
    for module in iter_modules():
        for target in imports_of(module):
            root = root_package_of(target)
            if root in FUTURE_PHASE_LIBRARIES:
                violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "P-03 A future-phase library in Phase 1 code means scope has leaked. Check "
        "the 'Explicitly Out of Scope' table in the phase C4 document.",
    )


def test_router_goes_through_the_pipeline():
    """P-04: the API layer must not bypass the interceptor chain."""
    violations: list[str] = []
    for module in iter_modules():
        if not is_within(module.name, REDIRECTION_API):
            continue
        for target in imports_of(module):
            if is_within(target, RESOLUTION_SERVICE_MODULE):
                violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "P-04 Calling LinkResolutionService directly from a router would silently "
        "bypass every Phase 3 interceptor on the highest-traffic path in the product. "
        "Depend on RedirectPipeline instead.",
    )


def test_analytics_persists_nothing_in_phase_1():
    """P-05: the click consumer is a logging stub until Phase 2."""
    forbidden = {"sqlalchemy", "asyncpg", "alembic"}
    violations: list[str] = []
    for module in iter_modules():
        if context_of(module.name) != "analytics":
            continue
        for target in imports_of(module):
            if root_package_of(target) in forbidden:
                violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "P-05 Analytics storage, enrichment and query endpoints are Phase 2. Phase 1 "
        "proves the publish-to-consume path and nothing more.",
    )
