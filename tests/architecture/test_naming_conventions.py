"""Naming and location conventions N-01 .. N-13.

Specification: artifacts/architecture/phase_1_mvp/archunit_specs.md, section 3.

Every rule is written so that an empty package passes: a rule constrains classes and
modules that exist, it never demands that they exist.
"""

from __future__ import annotations

import re

import pytest

from tests.architecture._arch import (
    PACKAGE_NAME,
    attribute_accesses,
    base_names,
    classes_of,
    describe,
    functions_of,
    in_subpackage,
    is_within,
    iter_modules,
    methods_of,
    module_level_names,
    modules_in,
    plain_call_names,
)

pytestmark = pytest.mark.architecture

TIME_PACKAGE = f"{PACKAGE_NAME}.shared_kernel.time"
REDIRECTION_PORTS = f"{PACKAGE_NAME}.redirection.domain.ports"

HUNGARIAN_INTERFACE = re.compile(r"^I[A-Z]")

JUNK_MODULE_NAMES: frozenset[str] = frozenset(
    {"utils", "util", "helpers", "helper", "common", "misc", "shared"}
)

READ_ONLY_METHOD_PREFIXES: tuple[str, ...] = (
    "get_",
    "find_",
    "exists_",
    "list_",
    "count_",
)

# Ports whose non-read method names are legitimate: neither touches the system of record.
READ_ONLY_PORT_EXEMPTIONS: frozenset[str] = frozenset(
    {
        f"{REDIRECTION_PORTS}.link_cache",
        f"{REDIRECTION_PORTS}.click_event_publisher",
    }
)

FORBIDDEN_TIME_CALLS: frozenset[str] = frozenset(
    {"datetime.now", "datetime.datetime.now"}
)


def _suffix_rule(segments: tuple[str, ...], suffixes: tuple[str, ...]) -> list[str]:
    violations: list[str] = []
    for module in modules_in(*segments):
        for class_def in classes_of(module):
            if not class_def.name.endswith(suffixes):
                allowed = ", ".join(suffixes)
                violations.append(
                    f"{module.location}: {class_def.name} (expected suffix: {allowed})"
                )
    return violations


def test_ports_are_protocols():
    """N-01: a port is an abstraction, never a concretion."""
    violations: list[str] = []
    for module in modules_in("domain", "ports"):
        for class_def in classes_of(module):
            if not {"Protocol", "ABC"} & set(base_names(class_def)):
                violations.append(f"{module.location}: {class_def.name}")
    assert not violations, describe(
        violations,
        "N-01 Classes in ..domain.ports.. must declare typing.Protocol (or abc.ABC) "
        "as a base, so that the Dependency Inversion Principle is checkable.",
    )


def test_no_impl_suffix_or_hungarian_interface_prefix():
    """N-02: name the implementation technology, not the fact that it implements."""
    violations: list[str] = []
    for module in iter_modules():
        for class_def in classes_of(module):
            name = class_def.name
            if name.endswith("Impl") or HUNGARIAN_INTERFACE.match(name):
                violations.append(f"{module.location}: {name}")
    assert not violations, describe(
        violations,
        "N-02 'FooImpl' and 'IFoo' carry no information. Prefer names such as "
        "SqlAlchemyLinkRepository or RedisLinkCache.",
    )


def test_application_service_suffix():
    """N-03: use-case classes are recognisable by name."""
    violations = _suffix_rule(
        ("application", "services"),
        ("Service", "Dispatcher", "Handler"),
    )
    assert not violations, describe(
        violations,
        "N-03 Classes in ..application.services.. must be named for their role.",
    )


def test_pipeline_class_suffix():
    """N-04: the redirect pipeline package contains only pipeline machinery."""
    violations = _suffix_rule(("application", "pipeline"), ("Pipeline", "Interceptor"))
    assert not violations, describe(
        violations,
        "N-04 ..application.pipeline.. is the redirect extension seam; anything that "
        "is not a Pipeline or an Interceptor belongs elsewhere.",
    )


def test_infrastructure_adapter_suffixes():
    """N-05: an adapter's name states what kind of adapter it is."""
    violations: list[str] = []
    violations += _suffix_rule(
        ("infrastructure", "persistence"),
        ("Repository", "Model", "Table", "Factory", "Base"),
    )
    violations += _suffix_rule(("infrastructure", "cache"), ("Cache",))
    violations += _suffix_rule(
        ("infrastructure", "messaging"),
        ("Publisher", "Subscriber", "Consumer"),
    )
    assert not violations, describe(
        violations,
        "N-05 Adapter names must identify the port they satisfy.",
    )


def test_router_module_naming_and_export():
    """N-06: routers are discoverable by filename and expose `router`."""
    violations: list[str] = []
    for module in modules_in("api", "routers"):
        if module.is_package_init:
            continue
        if not module.path.name.endswith("_router.py"):
            violations.append(f"{module.location}: filename must end with _router.py")
        if "router" not in module_level_names(module):
            violations.append(f"{module.location}: no module-level `router` defined")
    assert not violations, describe(
        violations,
        "N-06 A predictable router module shape is what lets a composition root mount "
        "every router without bespoke wiring.",
    )


def test_api_schema_suffix():
    """N-07: transport schemas are never reused as domain models."""
    violations = _suffix_rule(("api", "schemas"), ("Request", "Response"))
    assert not violations, describe(
        violations,
        "N-07 Classes in ..api.schemas.. must end with Request or Response.",
    )


def test_redirection_ports_are_read_only():
    """N-08: the redirect path may not grow a write capability."""
    violations: list[str] = []
    for module in iter_modules():
        if not is_within(module.name, REDIRECTION_PORTS):
            continue
        if module.name in READ_ONLY_PORT_EXEMPTIONS:
            continue
        for class_def in classes_of(module):
            for method in methods_of(class_def):
                if method.name.startswith("__"):
                    continue
                if not method.name.startswith(READ_ONLY_METHOD_PREFIXES):
                    violations.append(
                        f"{module.location}: {class_def.name}.{method.name}"
                    )
    assert not violations, describe(
        violations,
        "N-08 Methods on redirection ports must be named get_/find_/exists_/list_/"
        "count_. A mutation on this path belongs in the Management API.",
    )


def test_no_print_statements():
    """N-09: all output is structured JSON on stdout."""
    violations: list[str] = []
    for module in iter_modules():
        if "print" in plain_call_names(module):
            violations.append(module.location)
    assert not violations, describe(
        violations,
        "N-09 print() bypasses the log pipeline: no level, no timestamp, no context, "
        "and nothing for Fluentd/Logstash to parse.",
    )


def test_all_functions_are_return_annotated():
    """N-10: the mypy --strict contract, enforced structurally as well."""
    violations: list[str] = []
    for module in iter_modules():
        for function in functions_of(module.tree):
            if function.returns is None:
                violations.append(f"{module.location}: {function.name}()")
    assert not violations, describe(
        violations,
        "N-10 Every function and method under src/urlshortener needs a return "
        "annotation.",
    )


def test_no_junk_drawer_modules():
    """N-11: modules are named for a responsibility."""
    violations: list[str] = []
    for module in iter_modules():
        if module.path.stem in JUNK_MODULE_NAMES:
            violations.append(module.location)
    assert not violations, describe(
        violations,
        "N-11 utils.py/helpers.py/common.py accumulate unrelated code and become a "
        "dependency magnet. Name the module after what it does.",
    )


def test_time_is_obtained_through_the_clock_port():
    """N-12: time is an injected dependency, not ambient state."""
    violations: list[str] = []
    for module in iter_modules():
        if is_within(module.name, TIME_PACKAGE):
            continue
        for access in attribute_accesses(module):
            if access in FORBIDDEN_TIME_CALLS or access.endswith(".utcnow"):
                violations.append(f"{module.location}: {access}")
    assert not violations, describe(
        violations,
        "N-12 Depend on shared_kernel.time.Clock. Phase 3 link expiration cannot be "
        "tested deterministically against a wall clock.",
    )


def test_composition_root_module_names():
    """N-13: wiring code must not accumulate business logic."""
    allowed = {"main", "container"}
    violations: list[str] = []
    for module in iter_modules():
        parts = module.parts
        if len(parts) < 4 or parts[:2] != (PACKAGE_NAME, "apps"):
            continue
        if parts[3] not in allowed:
            violations.append(f"{module.location}: {module.name}")
    assert not violations, describe(
        violations,
        "N-13 apps/<service>/ may contain only __init__.py, main.py and container.py. "
        "Anything richer belongs in a bounded context.",
    )


def test_middleware_lives_only_in_the_api_layer():
    """Supporting check for N-13/L-04: middleware is a transport concern."""
    violations: list[str] = []
    for module in iter_modules():
        if "middleware" not in module.parts:
            continue
        if not in_subpackage(module.name, "api", "middleware"):
            violations.append(f"{module.location}: {module.name}")
    assert not violations, describe(
        violations,
        "Middleware belongs in <context>/api/middleware/, where it is visibly part of "
        "the request path rather than hidden inside a use case.",
    )
