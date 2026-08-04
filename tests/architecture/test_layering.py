"""Layered architecture rules L-01 .. L-06.

Specification: artifacts/architecture/phase_1_mvp/archunit_specs.md, section 1.
"""

from __future__ import annotations

import pytest

from tests.architecture._arch import (
    PACKAGE_NAME,
    context_of,
    describe,
    imports_of,
    in_subpackage,
    internal_imports_of,
    is_within,
    iter_modules,
    layer_of,
    root_package_of,
)

pytestmark = pytest.mark.architecture

APPS_PACKAGE = f"{PACKAGE_NAME}.apps"

# Frameworks that must never reach the domain or the use-case layer. pydantic is
# deliberately absent: it is the project's declared modelling library.
FORBIDDEN_FRAMEWORKS: frozenset[str] = frozenset(
    {
        "fastapi",
        "starlette",
        "sqlalchemy",
        "asyncpg",
        "redis",
        "alembic",
        "celery",
        "uvicorn",
    }
)


def _cross_layer_violations(source: str, forbidden: set[str]) -> list[str]:
    violations: list[str] = []
    for module in iter_modules():
        if layer_of(module.name) != source:
            continue
        for target in internal_imports_of(module):
            hits_layer = layer_of(target) in forbidden
            hits_apps = is_within(target, APPS_PACKAGE)
            if hits_layer or hits_apps:
                violations.append(f"{module.location}: {module.name} -> {target}")
    return violations


def test_domain_depends_on_nothing_above_it():
    """L-01: domain must not access application, infrastructure, api or apps."""
    forbidden = {"application", "infrastructure", "api"}
    violations = _cross_layer_violations("domain", forbidden)
    assert not violations, describe(
        violations,
        "L-01 The domain layer is the innermost layer: it may depend on shared_kernel "
        "and contracts only.",
    )


def test_application_does_not_depend_on_infrastructure_api_or_apps():
    """L-02: application may depend on domain, never outwards."""
    violations = _cross_layer_violations("application", {"infrastructure", "api"})
    assert not violations, describe(
        violations,
        "L-02 Use cases depend on domain ports, never on adapters or transport. "
        "Inject the adapter from the composition root instead.",
    )


def test_infrastructure_depends_only_inward():
    """L-03: adapters implement domain ports; they never reach up into use cases."""
    violations = _cross_layer_violations("infrastructure", {"application", "api"})
    assert not violations, describe(
        violations,
        "L-03 An adapter that needs a use case is a sign the dependency is inverted "
        "the wrong way round; move the orchestration into the application layer.",
    )


def test_api_does_not_depend_on_infrastructure():
    """L-04: transport talks to use cases; wiring happens in the composition root."""
    violations = _cross_layer_violations("api", {"infrastructure"})
    assert not violations, describe(
        violations,
        "L-04 Routers and dependency providers must read pre-built collaborators from "
        "app.state, typed as the application/domain abstraction.",
    )


def test_domain_and_application_are_framework_free():
    """L-05: no web/db/broker framework below the infrastructure layer."""
    violations: list[str] = []
    for module in iter_modules():
        if layer_of(module.name) not in {"domain", "application"}:
            continue
        for target in imports_of(module):
            if root_package_of(target) in FORBIDDEN_FRAMEWORKS:
                violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "L-05 Domain and application code must be executable with no I/O framework "
        "installed, which is what keeps it unit-testable with fakes.",
    )


def test_infrastructure_is_only_wired_from_the_composition_root():
    """L-06: concrete adapters are constructed only in urlshortener.apps."""
    violations: list[str] = []
    for module in iter_modules():
        importer_is_app = is_within(module.name, APPS_PACKAGE)
        importer_is_infra = layer_of(module.name) == "infrastructure"
        for target in internal_imports_of(module):
            if not in_subpackage(target, "infrastructure"):
                continue
            same_context = context_of(module.name) == context_of(target)
            if importer_is_app or (importer_is_infra and same_context):
                continue
            violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "L-06 Only apps/<service>/container.py may name a concrete adapter. "
        "Everything else depends on the port.",
    )
