# Developer Human Context

**Purpose:** this codebase was generated using an agentic SDLC (a set of
Claude Code subagents that play Technical Manager, Architect, Developer, and
QA). This document is my working reference for staying on top of what
actually got built, why, and how to reason about it — for code review,
onboarding, planning the next phase, or explaining the system to anyone else
who needs to work in it. It's a living document: append to "Changelog / open
questions" at the bottom as things change rather than rewriting history.

---

## 1. Two things this repo is, at once

1. **A product**: a URL shortener + click-analytics platform (think Bitly).
2. **A demonstration of an agentic SDLC**: `.claude/agents/` holds four agent
   definitions (`technical_manager`, `architect`, `developer`, `quality_agent`)
   plus an `orchestrator` that chains them. Each agent produces artifacts in
   `artifacts/`, and only the `developer`/`quality_agent` agents touch `src/`
   and `tests/`.

The short version: I directed an agentic pipeline — Technical Manager →
Architect → Developer → QA — seeded with my own requirements and
architecture guidance documents, and reviewed the resulting code and its
rationale. The rest of this doc is what lets me operate on that codebase with
full understanding, not just trust.

### Where each artifact type comes from

| Path | Produced by | Contents |
| --- | --- | --- |
| `markdowns/` | **Me (human input)** | `REQUIREMENTS.md` (product features I asked for), `architecture_guidance.md` (target stack/constraints I dictated), `developer_notes.md` (style/paradigm/commit rules I dictated) |
| `artifacts/development_plan/<phase>/` | Technical Manager agent | Phase summaries + user stories, phased as an MVP-first roadmap |
| `artifacts/architecture/` | Architect agent | `overall_architecture.md` (all 6 phases) + per-phase C4 diagrams and "ArchUnit" specs |
| `artifacts/qa/<phase>/` | QA agent | Test-gap analysis against the stories/requirements |
| `src/urlshortener/` | Developer agent (TDD) | The actual product code |
| `tests/architecture/` | Developer agent, spec'd by Architect | Executable structural rules (see §5) |
| `.claude/agents/` | **Me**, via prior sessions | The agent definitions/prompts/workflows themselves |

---

## 2. The product, in one paragraph

A user POSTs a long URL to the **Management API**, gets back a short code.
Visitors hit the **Redirection Engine** at that short code and get an HTTP
302 to the original URL, cache-first via Redis with a PostgreSQL fallback.
Every redirect fires an async "click event" onto a Redis Stream, consumed
(currently just logged) by a **Click Consumer** worker — this is the seam
Phase 2's real analytics pipeline will plug into. All three are separate
deployable processes built from one Python package.

## 3. What is actually built vs. only planned

**Only Phase 1 (MVP) has real code.** Phases 2–6 exist only as planning
artifacts (`artifacts/development_plan/phase_2..6/`) — no `phase_2..6`
architecture docs were even generated (`overall_architecture.md` §6 says "not
yet generated"), and there is zero corresponding code. When discussing or
planning against this repo, treat anything past Phase 1 as designed-for, not
built — the roadmap below is the reference, not the current state.

Roadmap (from `artifacts/architecture/overall_architecture.md`):

| Phase | Name | Delta |
| --- | --- | --- |
| **1 — built** | MVP — Core Redirection Loop | Management API, Redirection Engine, Postgres, Redis cache, click-event publish + stub consumer, containers + CI |
| 2 | Cloud-Native Foundation & Async Analytics | Celery workers, real analytics store, K8s/Helm, Prometheus/OTel, analytics query API |
| 3 | Security Controls & Routing Rules | Bot/IP filtering, password interstitial, expiration/access rules, geo/device routing |
| 4 | Branding & Conversion Tracking | Custom aliases/domains, QR codes, ad-pixel interstitial |
| 5 | Automation at Scale | Public REST API + API keys, rate limiting, bulk CSV, webhooks, Terraform |
| 6 | Link-in-Bio & Hardening | Bio pages, ArgoCD GitOps, Grafana dashboards, full tracing |

### Phase 1 stories (map to commits)

| Story | Commit | What it added |
| --- | --- | --- |
| P1-01 Link Creation API | `fe05e77` | Management API, `POST /links`, Postgres persistence |
| P1-02 Redirection Engine | `ca13b47` | Cache-first redirect engine |
| P1-03 Async click publish | `fdd88d5` | Redis Streams publish + stub consumer, fire-and-forget |
| — | `3790d20` | Bug fix: spurious `XREADGROUP` timeout (see §6) |
| P1-04 Containerization & CI | `d000c98` | Dockerfiles ×3, docker-compose, GitHub Actions CI |
| — | `32ece88` | Black-box multi-process E2E tests added by QA agent |

Full history is 12 commits, starting from framework scaffolding
(`83e9745` agents, `0bc9d07` development plan, `b7c481e` Phase 1 architecture)
through the above implementation commits.

---

## 4. Architecture — the shape to reason from

**Style:** modular monolith of bounded contexts, deployed as independently
scalable processes ("ports & adapters" per context). One installable package
(`urlshortener`), three composition roots (`apps/management_api`,
`apps/redirection_engine`, `apps/click_consumer`), one CI image-build pipeline.

```
src/urlshortener/
├── shared_kernel/   settings, structured logging, Clock, base errors — a dependency sink
├── contracts/       versioned cross-process schemas (ClickEvent) — standalone, no urlshortener deps
├── link_management/ WRITE side — Management API
├── redirection/      READ/hot path — Redirection Engine
├── analytics/        click ingestion — Click Consumer
└── apps/             composition roots (wiring only, no business logic)
```

Each bounded context is layered `api → application → domain`, with
`infrastructure` implementing `domain` ports and depending inward only.
Concrete adapters (SQLAlchemy repos, Redis clients) are built **only** in
`apps/*/container.py` and exposed via `app.state`; the `api` layer reads them
back typed as the domain/application abstraction. This is Dependency
Inversion, and it is enforced by tests, not convention (§5).

### Why the Redirection Engine is a separate process from day one

Splitting cost ~nothing in Phase 1 (one more Dockerfile + composition root),
but buys independent horizontal scaling later, an isolated blast radius for
Phase 3's middleware chain, and its own latency SLO. Merging two processes
later is a breaking deploy change; splitting now is free. — this is
`overall_architecture.md` §2.1 verbatim reasoning, worth keeping handy any
time someone questions why there are three services instead of one.

### The Redirect Pipeline — the extension point that matters most

`redirection/application/pipeline/redirect_pipeline.py` composes an ordered
list of `RedirectInterceptor`s around a terminal handler
(`LinkResolutionService.resolve`) at **construction time** (not per-request):

```
RedirectContext → [interceptor 1] → [interceptor 2] → ... → terminal handler → RedirectDecision
```

Phase 1 registers **zero** interceptors — the pipeline exists but is empty.
This is intentional: it's the seam Phase 3 fills with expiration/access
checks, a password gate, and geo/device routing, and Phase 4 fills with a
conversion-pixel interstitial, **without ever touching the router or the
resolution service**. It's Open/Closed applied to the highest-traffic, riskiest
code path in the system. `RedirectDecision` is a closed result hierarchy
(currently `RedirectToDestination` | `LinkNotFound`); the router match-cases
over it and treats an unmapped decision type as a hard failure
(`NotImplementedError`), not a silent 404 — so a future phase that adds a
decision subclass without updating the router fails loudly in tests, not in
prod.

An architecture rule (`P-04` in `archunit_specs.md`) statically forbids the
API router from importing `LinkResolutionService` directly — it must go
through `RedirectPipeline`, so nobody can accidentally bypass future
interceptors for a "quick fix." This matters for future work: any new
redirect-time behavior should be a new interceptor, not an edit to the router.

### Key architectural decisions (AD-1..AD-7), with the "why," from `overall_architecture.md` §5

| # | Decision | Rejected alternative | Why |
| --- | --- | --- | --- |
| AD-1 | Monorepo, one package, multiple composition roots | Separate repo per service | Shared `links` contract stays in one place; import boundaries are statically checkable |
| AD-2 | Ports & adapters per bounded context | Layered MVC over a shared ORM | Redirect path unit-testable with in-memory fakes; interceptors addable without touching adapters |
| AD-3 | Redis as both cache and broker in Phase 1 | RabbitMQ from the start | One infra dependency for MVP; `ClickEventPublisher` port makes swapping brokers a one-adapter change |
| AD-4 | Interceptor pipeline on redirect path | Growing `if` branches in the router | Router would otherwise become the highest-churn, highest-risk file |
| AD-5 | Versioned cache document, not a bare URL string | `SET short_code -> url` | Zero-downtime rollouts when Phase 3 enriches the cached payload |
| AD-6 | Partitioned PostgreSQL for analytics before ClickHouse | ClickHouse in Phase 2 | Defers operational cost until volume justifies it; repository port allows the swap later |
| AD-7 | Redirect **never** writes to PostgreSQL | Inline click-counter update on read | Protects the latency SLO; removes write contention from the hot path |

### Data model note worth remembering

`links` uses a surrogate `id` primary key, not `short_code` — because Phase 4
needs uniqueness scoped *per custom domain*, i.e. `(domain_id, short_code)`,
and that widening would break foreign keys if `short_code` were the PK.
`short_code` is `VARCHAR(64)` even though Phase 1 codes are 7 chars, because
Phase 4 custom aliases will be longer. This is a recurring theme: Phase 1
schema choices are made so later phases only ever add columns/tables, never
alter existing ones — good to keep in mind before making any schema change,
even an apparently small one.

---

## 5. Testing strategy — 4 layers, and why each exists

1. **`tests/unit/`** — pure logic against hand-written fakes (no DB/Redis).
   e.g. `LinkCreationService` tested with a fake repository to prove
   collision-retry logic without touching Postgres.
2. **`tests/integration/`** — real PostgreSQL + real Redis (via CI service
   containers / local Podman), but the FastAPI app is exercised in-process
   via `httpx.ASGITransport` — no real network hop, no separate processes.
3. **`tests/e2e/`** — genuinely separate processes over the network:
   `test_docker_compose_stack.py` (infra smoke: does the full containerized
   stack come up via `podman compose`/`docker compose`) and
   `test_application_journeys.py` (black-box product journeys: create→
   redirect, unknown-code 404, click publish→consume — spawns the three app
   processes itself against a reachable Postgres/Redis). The latter was
   added by the QA agent *after* reviewing developer tests and finding this
   was the one real coverage gap (see
   `artifacts/qa/phase_1_mvp/developer_test_gaps.md`). Marked
   `@pytest.mark.e2e`, run separately (`pytest -m e2e tests/e2e`).
   **Verified 2026-08-05**: both files pass independently; see §7 for a
   caveat about running them together locally.
4. **`tests/architecture/`** — a **from-scratch, AST-based ArchUnit
   equivalent** (`tests/architecture/_arch.py`), not a third-party library.
   Rationale documented in `artifacts/architecture/phase_1_mvp/archunit_specs.md`:
   no extra dependency, never imports application code (so a rule can't be
   defeated by an import-time side effect), and can express Python-specific
   rules a generic tool can't (e.g. "every class under `domain.ports` must be
   a `typing.Protocol`"). Four rule families, each worth knowing when
   touching that part of the code:
   - **Layering** (`test_layering.py`): domain → nothing above it; application
     can't see infrastructure/api/apps; domain/application can't import
     `fastapi`/`sqlalchemy`/`redis`/etc. at all (framework-free core).
   - **Dependencies** (`test_dependencies.py`): the three bounded contexts
     never import each other; `redirection` specifically can never import
     `link_management` (the structural form of "reads never touch the write
     side"); `shared_kernel`/`contracts` are dependency sinks; only
     `shared_kernel.config` may read `os.environ`.
   - **Naming conventions** (`test_naming_conventions.py`): ports must be
     `Protocol`s, no `Impl`/`IFoo` naming, service classes suffixed
     `Service`/`Dispatcher`/`Handler`, no `print()`, every function has a
     return annotation (mypy-strict, structurally), `datetime.now()` banned
     outside `shared_kernel.time` (must go through injected `Clock`), no
     `utils.py`/`helpers.py` junk-drawer modules.
   - **Phase boundaries** (`test_phase_boundaries.py`): stops Phase 1 from
     accidentally building Phase 2+ behavior — e.g. no `celery`/`geoip2`/
     `boto3`/etc. imports anywhere yet; the `redirection/api/middleware/`
     package must exist but be empty (Phase 3's reserved mount point); no
     `Interceptor` subclass may exist yet (Phase 1 ships the seam, not the
     rules). Each rule states which phase is expected to *deliberately*
     relax it — that's designed to be a reviewable diff when Phase 3+ work
     starts, not a surprise CI failure.

Everything above "passes vacuously on an empty package," so adding a new
package later can't accidentally break a Phase 1 rule — only violating a
stated constraint can.

QA's Phase 1 sign-off (`artifacts/qa/phase_1_mvp/developer_test_gaps.md`):
no critical gaps, no business-logic discrepancies vs. `REQUIREMENTS.md`; one
accepted, deliberately-not-tested edge case — a live Redis-broker outage
mid-request is proven only at the unit level (dispatcher swallows all
exceptions but `CancelledError`), not reproduced with a real broker kill in
an automated test, because that would add flakiness for limited extra
assurance.

---

## 6. A real bug worth remembering as a case study

Commit `3790d20`: while containerizing the click consumer (P1-04), running
it against a **real** Redis server (not the unit tests' fake client) surfaced
`redis.exceptions.TimeoutError` on `XREADGROUP`. Root cause: the subscriber's
server-side `BLOCK` duration (5000ms) sat exactly at redis-py's *client-side*
default `socket_timeout` (5s), so the client's own socket read raced the
server's block and threw a timeout instead of returning an empty batch on a
quiet stream. Fix: lowered `DEFAULT_BLOCK_MILLISECONDS` to 2000, and had the
click-consumer composition root build its Redis client with an explicit
`socket_timeout` derived from that block duration plus a safety margin,
documenting the constraint in both places. Good illustration of why
integration tests against a fake client aren't sufficient — this only showed
up against the real server, which is also why the E2E/integration split in
§5 exists.

---

## 7. Verification log — actually running the stack

I've now exercised the running system directly, not just read it
(2026-08-05):

- `pytest -m e2e tests/e2e/test_docker_compose_stack.py` — **passes**. Full
  `podman compose` build + up of all three services + Postgres + Redis +
  migration job, then a real HTTP round trip.
- `pytest -m e2e tests/e2e/test_application_journeys.py` — **passes** (4/4)
  once Postgres/Redis are reachable at `localhost:5432`/`6379` (either via
  `scripts/run_local.sh` or the compose stack). Confirms all three
  Phase-1 journeys against genuinely separate OS processes: create→redirect,
  unknown-code 404, and click publish→consume without blocking the redirect.
- Manual smoke test via `scripts/run_local.sh` + `curl`: `POST /links`
  returned `{"short_code":"P1SjNLb","short_url":"..."}`; `GET /P1SjNLb`
  returned `302 Found` with `cache-control: no-store` and no body; `GET
  /doesnotexist` returned `404`. Matches the documented behavior exactly.
- **Caveat found while doing this**: `test_docker_compose_stack.py` and
  `test_application_journeys.py` cannot both run in the *same* `pytest -m e2e
  tests/e2e` invocation if a `scripts/run_local.sh` dev stack (or the compose
  stack) is already holding host ports 5432/6379 — both e2e styles bind those
  same fixed ports, so whichever starts second fails/errors on "address
  already in use." Not a product bug; a local-environment ordering quirk.
  Workaround: stop whichever stack is running before switching between the
  two e2e styles, or run them in separate `pytest` invocations. CI doesn't
  hit this because each job starts with a clean environment.

---

## 8. Other implementation details worth being fluent in

- **Short code generation** (`Base62ShortCodeGenerator`): uses `secrets.choice`,
  not `random`, because short codes are public identifiers of private
  destinations — a predictable sequence would let someone enumerate other
  users' links. Length configurable via `Settings` (default 7, base62).
- **Collision handling lives in `LinkCreationService`, not the generator.**
  Deliberate separation: uniqueness is a property of the *repository*, not of
  a generated value — this lets Phase 4's custom-alias flow reuse the same
  retry/claim logic with no generator involved at all. The service retries up
  to `short_code_max_attempts` (default 5), distinguishing two collision
  reasons: `already_taken` (pre-check via `exists_by_short_code`) and
  `lost_insert_race` (a concurrent insert won between the check and the
  insert — the check-then-insert window is not atomic, and that's treated as
  a collision, not a caller error).
- **No negative caching.** The Redis cache never stores "not found." Reasoning
  in `link_resolution_service.py`: nothing can invalidate a cache entry yet
  (links are immutable pre-Phase-3), so caching a miss would make a
  just-created link unreachable for a full TTL if it was looked up (and
  cached as absent) microseconds before creation.
- **Cache failures degrade to latency, never correctness.** The `LinkCache`
  port contract guarantees adapters never raise; a Redis outage just means
  every request falls through to Postgres.
- **Click event dispatch is truly fire-and-forget.** `redirect_router.py`
  attaches `ClickEventDispatcher.dispatch` as a Starlette `BackgroundTask` on
  the `RedirectResponse` — Starlette runs it *after* the response bytes are
  already on the wire. The dispatcher itself catches every `BaseException`
  except `asyncio.CancelledError` and logs at WARNING; a broker outage costs
  one analytics event, never a redirect.
- **`Cache-Control: no-store` on every redirect.** Deliberately prevents a CDN
  or corporate proxy from serving the redirect itself, which would both
  suppress click events and hide any future per-visitor routing decisions
  (Phase 3+).
- **`ClickEvent` contract is forward-compatible on purpose**: `extra="ignore"`
  so a v1 consumer tolerates a v2 producer's extra fields; carries a
  `schema_version` int; every field Phase 2's real pipeline needs
  (`client_ip`, `user_agent`, `referrer`) is already populated in Phase 1 even
  though the stub consumer only logs them — so turning on real analytics
  later requires zero changes to the Redirection Engine.
- **Config discipline**: a single frozen `pydantic-settings` `Settings`,
  instantiated once per composition root and injected down; enforced
  structurally — only `shared_kernel/config` may touch `os.environ` (rule
  D-07).
- **Local dev has two paths**: `podman compose up -d --build` (matches CI/prod
  images exactly) or `scripts/run_local.sh` (Postgres+Redis in Podman,
  Management API + Redirection Engine run directly via `uvicorn`, no Click
  Consumer — for fast iteration without a rebuild). Podman was a deliberate
  choice in `markdowns/developer_notes.md` (no root-level Docker daemon
  requirement); docker compose works identically as a fallback.
- **CI (`ci.yml`) is three sequential jobs**: `test` (black/isort/ruff/mypy →
  alembic migrate → full pytest against real Postgres/Redis service
  containers) → `build-images` (matrix build of all 3 Dockerfiles) →
  `e2e` (the docker-compose round trip). No deploy automation yet — that's
  explicitly scoped to Phase 2 ("Cloud-Native Foundation") per a comment at
  the top of the workflow file.

---

## 9. Quick reference: reasoning about a request or a change

- **Request lifecycle.** POST `/links` → `LinkCreationService`
  (validate → generate code → check/insert with retry) → 201. GET
  `/{code}` → `RedirectContext` built from the request → `RedirectPipeline`
  (empty in Phase 1) → `LinkResolutionService` (Redis, then Postgres
  fallback + cache fill) → `RedirectResponse` with a `BackgroundTask` that
  fires the click event, response already sent by the time it runs.
- **Adding redirect-time behavior (password protection, geo-routing, etc.)**:
  it's a new `RedirectInterceptor` registered in the relevant phase's
  composition root — no router or resolution-service change needed.
- **Guarding against architectural drift**: the `tests/architecture/` suite
  is code, not a wiki page — it fails CI on a violation, so any refactor that
  crosses a bounded-context or layer boundary will be caught immediately.
- **Understanding how the code got here**: the agentic pipeline (Technical
  Manager → Architect → Developer → QA); `.claude/agents/*/AGENT.md` has the
  actual prompts/workflows if a specific agent's behavior needs explaining.
- **Scoping new work**: check §3 first — anything past Phase 1 is a design
  intent, not an implementation, and the per-phase story files under
  `artifacts/development_plan/` are the starting point for turning that
  intent into real work.

---

## Changelog / open questions

- **2026-08-05** — initial version, written after reviewing the full repo
  (commits `1201f51`..`32ece88`, all of `markdowns/`, `artifacts/`, and the
  Phase 1 `src/`/`tests/` tree).
- **2026-08-05** —Framing a general SDLC
  reference (this process — requirements/guidance in, agent pipeline,
  phased artifacts, architecture-as-tests . Also ran the system for real: both e2e test files pass
  independently (§7), and a manual create→redirect→404 smoke test via
  `scripts/run_local.sh` matched documented behavior exactly. Noted a
  local-only port-contention quirk between the two e2e test files (§7) —
  not a product defect, but worth remembering when running them back to
  back.
