"""AST-based structural analysis harness - the project's ArchUnit equivalent.

Why an in-repo harness instead of a library:

* it needs **no third-party dependency**, so the rules run in the leanest CI job and in a
  pre-commit hook;
* it **never imports application code**, so a rule cannot be defeated by an import-time
  side effect and the suite runs with no database, broker or settings available;
* it can express Python-specific rules that generic tools cannot, such as "every class in
  ``domain.ports`` must be a ``typing.Protocol``".

Rules are declared in ``artifacts/architecture/<phase>/archunit_specs.md`` and are
implemented in the sibling ``test_*.py`` modules. Every rule is written to pass
*vacuously* on an empty package, so adding a package in a later phase cannot break an
existing rule.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
PACKAGE_NAME = "urlshortener"
PACKAGE_ROOT = SRC_ROOT / PACKAGE_NAME

LAYERS: tuple[str, ...] = ("domain", "application", "infrastructure", "api")
BOUNDED_CONTEXTS: tuple[str, ...] = ("link_management", "redirection", "analytics")
TOP_LEVEL_PACKAGES: tuple[str, ...] = (
    "shared_kernel",
    "contracts",
    "link_management",
    "redirection",
    "analytics",
    "apps",
)

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class ModuleInfo:
    """One parsed Python module under ``src/urlshortener``."""

    name: str
    path: Path
    tree: ast.Module

    @property
    def is_package_init(self) -> bool:
        return self.path.name == "__init__.py"

    @property
    def package(self) -> str:
        """Dotted name of the package this module lives in.

        For an ``__init__.py`` that is the module's own dotted name.
        """
        if self.is_package_init:
            return self.name
        head, _, _ = self.name.rpartition(".")
        return head

    @property
    def parts(self) -> tuple[str, ...]:
        return tuple(self.name.split("."))

    @property
    def location(self) -> str:
        """Repo-relative path, for readable assertion messages."""
        return str(self.path.relative_to(REPO_ROOT))


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC_ROOT).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


@lru_cache(maxsize=1)
def iter_modules() -> tuple[ModuleInfo, ...]:
    """Every module under ``src/urlshortener``, parsed once and cached."""
    modules: list[ModuleInfo] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        modules.append(ModuleInfo(name=_module_name(path), path=path, tree=tree))
    return tuple(modules)


def in_subpackage(dotted: str, *segments: str) -> bool:
    """Whether ``dotted`` contains ``segments`` as consecutive dotted parts."""
    parts = dotted.split(".")
    width = len(segments)
    for index in range(len(parts) - width + 1):
        if tuple(parts[index : index + width]) == segments:
            return True
    return False


def modules_in(*segments: str) -> tuple[ModuleInfo, ...]:
    """Modules whose dotted name contains the given consecutive path segments."""
    return tuple(m for m in iter_modules() if in_subpackage(m.name, *segments))


def is_within(dotted: str, package: str) -> bool:
    """Whether ``dotted`` is ``package`` itself or lives beneath it."""
    return dotted == package or dotted.startswith(f"{package}.")


def is_internal(dotted: str) -> bool:
    """Whether an import target belongs to this project."""
    return is_within(dotted, PACKAGE_NAME)


def layer_of(dotted: str) -> str | None:
    """The architectural layer a dotted name belongs to, if any."""
    for part in dotted.split("."):
        if part in LAYERS:
            return part
    return None


def context_of(dotted: str) -> str | None:
    """The top-level package (bounded context or otherwise) of a dotted name."""
    parts = dotted.split(".")
    if len(parts) < 2 or parts[0] != PACKAGE_NAME:
        return None
    return parts[1]


def root_package_of(dotted: str) -> str:
    """The first segment of a dotted name (``redis.asyncio`` -> ``redis``)."""
    return dotted.split(".", 1)[0]


def _resolve_relative(module: ModuleInfo, node: ast.ImportFrom) -> str:
    base_parts = module.package.split(".") if module.package else []
    if node.level > 1:
        trim = node.level - 1
        base_parts = base_parts[:-trim] if trim < len(base_parts) else []
    base = ".".join(base_parts)
    if node.module:
        return f"{base}.{node.module}" if base else node.module
    return base


def imports_of(module: ModuleInfo) -> tuple[str, ...]:
    """Absolute dotted import targets of a module, relative imports resolved.

    For ``from a.b import c`` both ``a.b`` and ``a.b.c`` are reported, so a rule can
    match either the module or the imported name with a simple prefix test.
    """
    targets: list[str] = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_relative(module, node)
            if not base:
                continue
            targets.append(base)
            for alias in node.names:
                targets.append(f"{base}.{alias.name}")
    return tuple(targets)


def internal_imports_of(module: ModuleInfo) -> tuple[str, ...]:
    """Import targets that belong to this project."""
    return tuple(target for target in imports_of(module) if is_internal(target))


def classes_of(module: ModuleInfo) -> tuple[ast.ClassDef, ...]:
    """Every class defined in a module, including nested ones."""
    found: list[ast.ClassDef] = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.ClassDef):
            found.append(node)
    return tuple(found)


def functions_of(node: ast.AST) -> tuple[FunctionNode, ...]:
    """Every function/method defined below ``node``, including nested ones."""
    found: list[FunctionNode] = []
    for child in ast.walk(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            found.append(child)
    return tuple(found)


def methods_of(class_def: ast.ClassDef) -> tuple[FunctionNode, ...]:
    """Directly declared methods of a class."""
    found: list[FunctionNode] = []
    for node in class_def.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            found.append(node)
    return tuple(found)


def dotted_name(node: ast.AST) -> str | None:
    """Render ``ast.Name``/``ast.Attribute`` chains as a dotted string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def base_names(class_def: ast.ClassDef) -> tuple[str, ...]:
    """Simple names of a class's bases (``typing.Protocol`` -> ``Protocol``)."""
    names: list[str] = []
    for base in class_def.bases:
        target = base.value if isinstance(base, ast.Subscript) else base
        dotted = dotted_name(target)
        if dotted:
            names.append(dotted.rsplit(".", 1)[-1])
    return tuple(names)


def attribute_accesses(module: ModuleInfo) -> tuple[str, ...]:
    """Every attribute access in the module, rendered dotted (``os.environ``)."""
    accesses: list[str] = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Attribute):
            dotted = dotted_name(node)
            if dotted:
                accesses.append(dotted)
    return tuple(accesses)


def plain_call_names(module: ModuleInfo) -> tuple[str, ...]:
    """Names of non-attribute call targets, e.g. ``print(...)`` -> ``print``."""
    names: list[str] = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.append(node.func.id)
    return tuple(names)


def module_level_names(module: ModuleInfo) -> frozenset[str]:
    """Names bound at module top level (assignments, defs, classes, imports)."""
    names: set[str] = set()
    for node in module.tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return frozenset(names)


def describe(violations: list[str], rule: str) -> str:
    """Build a readable failure message for an assertion."""
    listed = "\n  - ".join(violations)
    return f"{rule}\nViolations ({len(violations)}):\n  - {listed}"
