# ArchUnit Specifications — Phase 1: MVP (Core Redirection Loop)

**Phase ID:** `phase_1_mvp`
**Companion artifacts:** `./c4_architecture.md`, `./system_diagrams.md`
**Executable implementation:** `tests/architecture/` — run with `pytest tests/architecture`

## Implementation mechanism

Java's ArchUnit has no single canonical Python equivalent. These rules are implemented
in-repo as an **AST-based structural test harness** (`tests/architecture/_arch.py`) rather than via
a third-party library, because that harness:

- needs **no extra dependency**, so the rules run in the leanest CI job and as a pre-commit hook;
- **never imports application code**, so a rule cannot be defeated by an import-time side effect and
  the suite runs with no database, broker, or settings available;
- can express Python-specific rules a generic tool cannot, such as *"every class in `domain.ports`
  must be a `typing.Protocol`"*.

The harness exposes the primitives the rules are written against:

| Primitive | Meaning |
| --- | --- |
| `iter_modules()` | Every `.py` module under `src/urlshortener`, parsed once and cached |
| `imports_of(module)` / `internal_imports_of(module)` | Absolute dotted import targets (relative imports resolved) |
| `classes_of(module)` / `methods_of(cls)` / `functions_of(node)` | Declaration lookups |
| `base_names(cls)` | Simple names of a class's bases (`typing.Protocol` → `Protocol`) |
| `attribute_accesses(module)` / `plain_call_names(module)` | Usage lookups (`os.environ`, `print`) |
| `module_level_names(module)` | Names bound at module top level |
| `layer_of(dotted)` / `context_of(dotted)` / `in_subpackage(dotted, *segments)` | Structural classification |

Every rule below is written so that it **passes vacuously on an empty package**. Adding a package in
a later phase therefore cannot break an existing Phase 1 rule; only violating a stated constraint can.

Rule → test mapping is one-to-one; the test name is given for each rule.

---

<!-- PHASE: Phase 1 MVP START -->

## 1. Layered Architecture Rules

Layer order within every bounded context: `api` → `application` → `domain`, with `infrastructure`
depending inward on `domain` only, and `apps` as the sole composition root above them all.

**File:** `tests/architecture/test_layering.py`

| ID | Rule | Test |
| --- | --- | --- |
| **L-01** | Classes residing in a package `..domain..` should not access classes residing in a package `..application..`, `..infrastructure..`, `..api..`, or `urlshortener.apps..`. | `test_domain_depends_on_nothing_above_it` |
| **L-02** | Classes residing in a package `..application..` should not access classes residing in a package `..infrastructure..`, `..api..`, or `urlshortener.apps..`. They may access `..domain..`, `urlshortener.shared_kernel..`, and `urlshortener.contracts..`. | `test_application_does_not_depend_on_infrastructure_api_or_apps` |
| **L-03** | Classes residing in a package `..infrastructure..` should not access classes residing in a package `..application..`, `..api..`, or `urlshortener.apps..`. Adapters implement **domain** ports; they never reach up into use cases. | `test_infrastructure_depends_only_inward` |
| **L-04** | Classes residing in a package `..api..` should not access classes residing in a package `..infrastructure..` or `urlshortener.apps..`. Concrete adapters are constructed only in the composition root and read back from `app.state`, typed as the application/domain abstraction. | `test_api_does_not_depend_on_infrastructure` |
| **L-05** | Classes residing in a package `..domain..` or `..application..` should not access `fastapi`, `starlette`, `sqlalchemy`, `asyncpg`, `redis`, `alembic`, `celery`, or `uvicorn`. Domain and use-case logic must be executable without any I/O framework installed. (`pydantic` **is** permitted — it is the project's declared modelling library.) | `test_domain_and_application_are_framework_free` |
| **L-06** | Only modules residing in `urlshortener.apps..`, or in the *same bounded context's own* `..infrastructure..` package, may access classes residing in a package `..infrastructure..`. | `test_infrastructure_is_only_wired_from_the_composition_root` |

---

## 2. Dependency Rules

**File:** `tests/architecture/test_dependencies.py`

| ID | Rule | Test |
| --- | --- | --- |
| **D-01** | The bounded contexts `urlshortener.link_management`, `urlshortener.redirection`, and `urlshortener.analytics` should not access each other. All inter-context communication happens through `urlshortener.contracts` (schemas) or through the datastore. | `test_bounded_contexts_do_not_import_each_other` |
| **D-02** | Classes residing in `urlshortener.shared_kernel..` should not access any other `urlshortener` package. The shared kernel is a dependency sink. | `test_shared_kernel_is_a_sink` |
| **D-03** | Classes residing in `urlshortener.contracts..` should not access any other `urlshortener` package. Wire contracts must be independently importable by any producer or consumer. | `test_contracts_are_standalone` |
| **D-04** | No module in `urlshortener.redirection..` may access `urlshortener.link_management..`. The structural expression of the mandated read/write split on the redirect hot path. (A narrower restatement of D-01, kept as its own named rule because it is the highest-value constraint in the phase.) | `test_redirection_never_reaches_into_the_write_side` |
| **D-05** | The top-level package graph (`shared_kernel`, `contracts`, `link_management`, `redirection`, `analytics`, `apps`) must be acyclic. | `test_no_cycles_between_top_level_packages` |
| **D-06** | No module may access `urlshortener.apps..` except modules inside `urlshortener.apps..` itself. Composition roots are consumed by process entry points and tests only, never by library code. | `test_nothing_imports_the_composition_roots` |
| **D-07** | Only modules residing in `urlshortener.shared_kernel.config..` may access `os.environ` or `os.getenv`. All configuration flows through the injected `Settings` object. | `test_environment_is_read_only_in_the_config_module` |

---

## 3. Naming and Location Conventions

**File:** `tests/architecture/test_naming_conventions.py`

| ID | Rule | Test |
| --- | --- | --- |
| **N-01** | Every class residing in a package `..domain.ports..` must declare `typing.Protocol` (or `abc.ABC`) among its bases. Ports are abstractions, never concretions. | `test_ports_are_protocols` |
| **N-02** | No class anywhere in `urlshortener` may carry the suffix `Impl` or the Hungarian interface prefix `I` followed by an uppercase letter (`IRepository`). Name the *implementation technology* instead: `SqlAlchemyLinkRepository`, `RedisLinkCache`. | `test_no_impl_suffix_or_hungarian_interface_prefix` |
| **N-03** | Classes residing in a package `..application.services..` must have the suffix `Service`, `Dispatcher`, or `Handler`. | `test_application_service_suffix` |
| **N-04** | Classes residing in a package `..application.pipeline..` must have the suffix `Pipeline` or `Interceptor`. | `test_pipeline_class_suffix` |
| **N-05** | Classes residing in `..infrastructure.persistence..` must have the suffix `Repository`, `Model`, `Table`, `Factory`, or `Base`; in `..infrastructure.cache..` the suffix `Cache`; in `..infrastructure.messaging..` the suffix `Publisher`, `Subscriber`, or `Consumer`. | `test_infrastructure_adapter_suffixes` |
| **N-06** | Modules residing in a package `..api.routers..` must be named `*_router.py` and must define a module-level name `router`. | `test_router_module_naming_and_export` |
| **N-07** | Classes residing in a package `..api.schemas..` must have the suffix `Request` or `Response`. Transport schemas are never reused as domain models. | `test_api_schema_suffix` |
| **N-08** | Every method declared on a port in `urlshortener.redirection.domain.ports..` must be read-only by name — `get_*`, `find_*`, `exists_*`, `list_*`, `count_*`. Exempt: `...ports.link_cache` (cache fill) and `...ports.click_event_publisher` (event emission), neither of which touches the system of record. No `save_*`, `add_*`, `update_*`, or `delete_*` may exist on the redirect read path. | `test_redirection_ports_are_read_only` |
| **N-09** | No module under `src/urlshortener` may call the builtin `print`. All output goes through `shared_kernel.logging` (structured JSON to stdout). | `test_no_print_statements` |
| **N-10** | Every function and method defined under `src/urlshortener` must declare a return annotation, enforcing the `mypy --strict` contract structurally as well. | `test_all_functions_are_return_annotated` |
| **N-11** | No module under `src/urlshortener` may be named `utils.py`, `util.py`, `helpers.py`, `helper.py`, `common.py`, `misc.py`, or `shared.py`. Modules are named for a responsibility. | `test_no_junk_drawer_modules` |
| **N-12** | `datetime.now(...)` and `datetime.utcnow(...)` may only be called inside `urlshortener.shared_kernel.time..`. Everything else takes a `Clock` dependency, so that Phase 3 expiration logic is testable without freezing global time. | `test_time_is_obtained_through_the_clock_port` |
| **N-13** | Modules under a composition-root package (`urlshortener.apps.<service>`) must be named `__init__.py`, `main.py`, or `container.py`. Wiring code must not accumulate business logic. | `test_composition_root_module_names` |
| **N-14** | Any module whose path contains a `middleware` segment must reside in `<context>/api/middleware/`. Middleware is a transport concern and must be visibly part of the request path, not hidden inside a use case. | `test_middleware_lives_only_in_the_api_layer` |

---

## 4. Phase Boundary Rules

These rules exist specifically to stop Phase 1 from accidentally implementing later-phase behaviour.
The phase that legitimately introduces a feature is expected to relax or delete the matching rule —
that deletion is a deliberate, reviewable act, which is the point.

**File:** `tests/architecture/test_phase_boundaries.py`

| ID | Rule | Test | Relaxed by |
| --- | --- | --- | --- |
| **P-01** | The package `urlshortener.redirection.api.middleware` must exist and must contain no file other than `__init__.py`. It is the reserved mount point for Phase 3 IP/bot filtering middleware. | `test_middleware_package_is_reserved_and_empty` | Phase 3 |
| **P-02** | No class in `urlshortener` may carry the suffix `Interceptor` except the Protocol itself in `urlshortener.redirection.application.pipeline.redirect_interceptor`. Phase 1 delivers the seam, not the rules. | `test_no_interceptor_implementations_in_phase_1` | Phase 3 |
| **P-03** | No module in `urlshortener` may import a future-phase library: `celery`, `user_agents`, `ua_parser`, `geoip2`, `maxminddb`, `prometheus_client`, `opentelemetry`, `boto3`, `segno`, `qrcode`, `jinja2`. | `test_no_future_phase_dependencies` | Phases 2, 4, 6 (individually) |
| **P-04** | No module in `urlshortener.redirection.api..` may import `...application.services.link_resolution_service`. The router must reach resolution **through** `RedirectPipeline`, otherwise Phase 3's interceptors would be silently bypassed on the highest-traffic path in the product. | `test_router_goes_through_the_pipeline` | never |
| **P-05** | No module in `urlshortener.analytics..` may import `sqlalchemy`, `asyncpg`, or `alembic`. The Phase 1 consumer is a logging stub; analytics persistence arrives in Phase 2. | `test_analytics_persists_nothing_in_phase_1` | Phase 2 |

<!-- PHASE: Phase 1 MVP END -->

---

## 5. Rules deliberately NOT enforced in Phase 1

Documented so a later Architect run knows they were considered and skipped on purpose:

- **No keyword scan for `INSERT`/`UPDATE`/`DELETE` inside `redirection.infrastructure.persistence`.**
  N-08 constrains the *port surface*, which is the durable, reviewable guarantee; scanning adapter
  internals for SQL keywords is brittle and easily circumvented. The stronger control is
  operational: give the Redirection Engine a database role with read-only grants.
- **No `/metrics` or OpenTelemetry instrumentation rule** — Phase 2.
- **No rule on Kubernetes manifests, Helm values, or Terraform module layout** — Phases 2 and 5.
- **No coverage-threshold rule.** Test coverage is the Developer and QA agents' concern; the
  architecture suite checks structure, not thoroughness.
- **No rule forbidding `pydantic` in the domain.** The project's developer notes explicitly endorse
  Pydantic models as the immutable data-structure mechanism, so banning it would fight the standard.

---
*Generated by Architect Agent — scope: phase_1_mvp*
