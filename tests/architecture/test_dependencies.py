"""Cross-module dependency rules D-01 .. D-07.

Specification: artifacts/architecture/phase_1_mvp/archunit_specs.md, section 2.
"""

from __future__ import annotations

import pytest

from tests.architecture._arch import (
    BOUNDED_CONTEXTS,
    PACKAGE_NAME,
    TOP_LEVEL_PACKAGES,
    attribute_accesses,
    context_of,
    describe,
    imports_of,
    internal_imports_of,
    is_within,
    iter_modules,
)

pytestmark = pytest.mark.architecture

APPS_PACKAGE = f"{PACKAGE_NAME}.apps"
SHARED_KERNEL_PACKAGE = f"{PACKAGE_NAME}.shared_kernel"
CONTRACTS_PACKAGE = f"{PACKAGE_NAME}.contracts"
CONFIG_PACKAGE = f"{SHARED_KERNEL_PACKAGE}.config"


def test_bounded_contexts_do_not_import_each_other():
    """D-01: contexts integrate through contracts or the datastore, never by import."""
    violations: list[str] = []
    for module in iter_modules():
        source = context_of(module.name)
        if source not in BOUNDED_CONTEXTS:
            continue
        for target in internal_imports_of(module):
            destination = context_of(target)
            if destination in BOUNDED_CONTEXTS and destination != source:
                violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "D-01 A shared type between two bounded contexts couples their release "
        "cycles. Publish a schema in urlshortener.contracts instead.",
    )


def test_shared_kernel_is_a_sink():
    """D-02: shared_kernel imports nothing else from the project."""
    violations: list[str] = []
    for module in iter_modules():
        if not is_within(module.name, SHARED_KERNEL_PACKAGE):
            continue
        for target in internal_imports_of(module):
            if not is_within(target, SHARED_KERNEL_PACKAGE):
                violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "D-02 Everything depends on shared_kernel, so shared_kernel must depend on "
        "nothing - otherwise it becomes a cycle and a change amplifier.",
    )


def test_contracts_are_standalone():
    """D-03: wire schemas must be importable by any producer or consumer."""
    violations: list[str] = []
    for module in iter_modules():
        if not is_within(module.name, CONTRACTS_PACKAGE):
            continue
        for target in internal_imports_of(module):
            if not is_within(target, CONTRACTS_PACKAGE):
                violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "D-03 A contract that drags project code with it cannot be shared safely "
        "between separately deployed processes.",
    )


def test_redirection_never_reaches_into_the_write_side():
    """D-04: the redirect hot path is structurally read-only."""
    write_side = f"{PACKAGE_NAME}.link_management"
    violations: list[str] = []
    for module in iter_modules():
        if context_of(module.name) != "redirection":
            continue
        for target in internal_imports_of(module):
            if is_within(target, write_side):
                violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "D-04 The Redirection Engine must never acquire write capability. Click data "
        "leaves via the message broker, not via the system of record.",
    )


def _top_level_graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {package: set() for package in TOP_LEVEL_PACKAGES}
    for module in iter_modules():
        source = context_of(module.name)
        if source not in graph:
            continue
        for target in internal_imports_of(module):
            destination = context_of(target)
            if destination in graph and destination != source:
                graph[source].add(destination)
    return graph


def _find_cycle(graph: dict[str, set[str]]) -> list[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def walk(node: str) -> list[str]:
        if node in visiting:
            start = stack.index(node)
            return [*stack[start:], node]
        if node in visited:
            return []
        visiting.add(node)
        stack.append(node)
        for neighbour in sorted(graph[node]):
            cycle = walk(neighbour)
            if cycle:
                return cycle
        stack.pop()
        visiting.discard(node)
        visited.add(node)
        return []

    for package in sorted(graph):
        cycle = walk(package)
        if cycle:
            return cycle
    return []


def test_no_cycles_between_top_level_packages():
    """D-05: the top-level package graph must be a DAG."""
    cycle = _find_cycle(_top_level_graph())
    assert not cycle, describe(
        [" -> ".join(cycle)],
        "D-05 A cycle between top-level packages makes independent deployment and "
        "independent testing impossible.",
    )


def test_nothing_imports_the_composition_roots():
    """D-06: urlshortener.apps is consumed by entry points and tests only."""
    violations: list[str] = []
    for module in iter_modules():
        if is_within(module.name, APPS_PACKAGE):
            continue
        for target in internal_imports_of(module):
            if is_within(target, APPS_PACKAGE):
                violations.append(f"{module.location}: {module.name} -> {target}")
    assert not violations, describe(
        violations,
        "D-06 Library code that imports a composition root inherits every adapter and "
        "every piece of configuration that root builds.",
    )


def test_environment_is_read_only_in_the_config_module():
    """D-07: configuration enters the system in exactly one place."""
    forbidden = {"os.environ", "os.getenv"}
    violations: list[str] = []
    for module in iter_modules():
        if is_within(module.name, CONFIG_PACKAGE):
            continue
        for access in attribute_accesses(module):
            if access in forbidden:
                violations.append(f"{module.location}: {module.name} uses {access}")
        for target in imports_of(module):
            if target in forbidden:
                violations.append(f"{module.location}: {module.name} imports {target}")
    assert not violations, describe(
        violations,
        "D-07 Reading the environment outside Settings makes configuration invisible "
        "to tests, to the container spec and to the next reader.",
    )
