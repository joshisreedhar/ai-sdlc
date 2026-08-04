# C4 Architecture — Phase 1: MVP (Core Redirection Loop)

**Phase ID:** `phase_1_mvp`
**Stories covered:** P1-01 Link Creation API · P1-02 Redirection Engine · P1-03 Non-Blocking Click Event Publish · P1-04 Containerization & Basic CI
**Companion artifacts:** `./system_diagrams.md` (module + sequence diagrams), `./archunit_specs.md` (structural rules)
**Parent document:** `../overall_architecture.md` (all-phase target state — *context only, do not build from it*)

---

## How to read this document

| Marker | Meaning for the Developer Agent |
| --- | --- |
| `<!-- PHASE: Phase 1 MVP START -->` … `<!-- PHASE: Phase 1 MVP END -->` | **Build exactly this.** Everything inside these markers is in scope for Phase 1. |
| Section 5 "Future-Proofing" | **Create the named stub/interface/contract only.** Do not implement any behaviour attributed to a later phase. |
| Section 6 "Explicitly Out of Scope" | **Do not write this code.** If a story tempts you toward it, stop. |

---

<!-- PHASE: Phase 1 MVP START -->

## 1. Context

Phase 1 has exactly **two** live actors and **zero** external system integrations.

- **Link Creator** — a human or API client that submits a long URL and receives a short code
  (story P1-01). No authentication, no ownership, no quota in this phase.
- **Visitor** — anonymous; requests `GET /{short_code}` and is redirected to the destination
  (story P1-02). Every such redirect emits one click event (story P1-03).

There is no GeoIP, no object storage, no ad pixel, no DNS integration, and no operator-facing
observability stack in Phase 1. The only "external system" a visitor touches is the destination
website they are redirected to.

```plantuml
@startuml C4_Context_Phase1
!define C4P https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master
!include C4P/C4_Context.puml

title System Context — Phase 1 MVP (Core Redirection Loop)

Person(creator, "Link Creator", "Submits a long URL, receives a short code. Unauthenticated in Phase 1.")
Person(visitor, "Visitor", "Requests a short URL and expects an immediate redirect")

System_Boundary(sb, "URL Shortener Platform — Phase 1 MVP") {
  System(platform, "URL Shortener (MVP)", "Creates short codes and resolves them to destination URLs with a cache-first lookup, emitting a click event per redirect")
}

System_Ext(destination, "Destination Website", "The original long URL")

Rel(creator, platform, "POST /links {long_url}", "HTTP/JSON")
Rel(platform, creator, "201 {short_code, short_url}", "HTTP/JSON")
Rel(visitor, platform, "GET /{short_code}", "HTTP")
Rel(platform, visitor, "302 Location: <long_url>  (or 404)", "HTTP")
Rel(visitor, destination, "Follows the Location header", "HTTP")

note right of platform
  OUT OF SCOPE in Phase 1:
  authentication, custom aliases/domains,
  QR codes, routing rules, password gates,
  expiration, analytics queries, dashboards.
end note
@enduml
```

### 1.1 In-scope external interfaces (the complete Phase 1 API surface)

| Interface | Container | Contract |
| --- | --- | --- |
| `POST /links` | Management API | Request `{"long_url": "<absolute http(s) url>"}` → `201 {"short_code": "<str>", "short_url": "<str>"}`; `422` on invalid URL |
| `GET /healthz` | Management API, Redirection Engine | `200 {"status": "ok"}` — liveness, no dependency checks |
| `GET /readyz` | Management API, Redirection Engine | `200` when required dependencies answer, `503` otherwise |
| `GET /{short_code}` | Redirection Engine | `302` with `Location: <long_url>`, or `404` when unknown |

`GET /healthz` and `GET /readyz` are in Phase 1 scope. They are cheap now and are the exact probe
endpoints Phase 2's Kubernetes deployment will reference; adding them later would mean re-releasing
both images.

> **Redirect status code:** use **302 (Found)** in Phase 1. Reason: 301 is aggressively cached by
> browsers, which would make a Phase 3 destination/rule change or a Phase 1 bug fix invisible to
> returning visitors, and would suppress the click events the analytics pipeline depends on. The
> status code must be read from a single constant so a later phase can make it configurable.

---

## 2. Containers

Phase 1 delivers **three application processes** and **two infrastructure services**. All five run
together via the local compose file (story P1-04).

| # | Container | Image / entry point | Phase 1 responsibility |
| --- | --- | --- | --- |
| C1 | **Management API** | `uvicorn urlshortener.apps.management_api.main:app` | `POST /links`, health endpoints. Writes to PostgreSQL. |
| C2 | **Redirection Engine** | `uvicorn urlshortener.apps.redirection_engine.main:app` | `GET /{short_code}`, health endpoints. Reads Redis then PostgreSQL. Publishes click events. |
| C3 | **Click Consumer (stub)** | `python -m urlshortener.apps.click_consumer.main` | Reads click events off the broker and logs them. **No parsing, no enrichment, no persistence.** |
| C4 | **PostgreSQL** | `postgres:16-alpine` | `links` table. System of record. |
| C5 | **Redis** | `redis:7-alpine` | Link cache **and** click-event stream. Single instance, two logical uses. |

```plantuml
@startuml C4_Container_Phase1
!define C4P https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master
!include C4P/C4_Container.puml

title Container Diagram — Phase 1 MVP

Person(creator, "Link Creator")
Person(visitor, "Visitor")

System_Boundary(sb, "URL Shortener Platform — Phase 1") {
  Container(api, "Management API", "Python 3.12, FastAPI, uvicorn", "POST /links, /healthz, /readyz\nOCI image: urlshortener-management-api")
  Container(redirect, "Redirection Engine", "Python 3.12, FastAPI, uvicorn", "GET /{short_code}, /healthz, /readyz\nOCI image: urlshortener-redirection-engine")
  Container(consumer, "Click Consumer (STUB)", "Python 3.12, redis-py", "Reads the click-event stream and logs each event.\nReplaced by Celery workers in Phase 2.")

  ContainerDb(pg, "PostgreSQL", "PostgreSQL 16", "links(id, short_code UNIQUE, long_url, created_at, updated_at)")
  ContainerDb(redis, "Redis", "Redis 7", "Cache: link:v1:{short_code} -> CachedLink JSON (TTL)\nStream: clicks.v1")
}

System_Ext(destination, "Destination Website")

Rel(creator, api, "POST /links", "HTTP/JSON")
Rel(visitor, redirect, "GET /{short_code}", "HTTP")
Rel(redirect, visitor, "302 Location / 404", "HTTP")
Rel(visitor, destination, "Follows redirect", "HTTP")

Rel(api, pg, "INSERT link, SELECT for collision check", "SQLAlchemy async / asyncpg")
Rel(redirect, redis, "GET link:v1:{code}  /  SETEX on miss", "RESP")
Rel(redirect, pg, "SELECT long_url WHERE short_code = ?  (READ ONLY)", "SQLAlchemy async / asyncpg")
Rel_L(redirect, redis, "XADD clicks.v1  (after response, fire-and-forget)", "RESP")
Rel(consumer, redis, "XREADGROUP clicks.v1", "RESP")

note bottom of api
  Phase 1: the Management API does NOT
  write to Redis. Cache population happens
  only on a Redirection Engine cache miss.
  (Write-through / invalidation arrives when
  links become mutable in Phase 3+.)
end note
@enduml
```

### 2.1 Container-level rules (non-negotiable in Phase 1)

1. The Redirection Engine issues **SELECT statements only**. Any `INSERT`/`UPDATE`/`DELETE` in the
   redirection context is an architecture violation (see `archunit_specs.md`, rule D-04/N-08).
2. The Management API does **not** import anything from the `redirection` package, and vice versa.
3. The Click Consumer does **not** import from `link_management` or `redirection`; it depends only on
   `contracts` + `shared_kernel` + its own `analytics` package.
4. Every process reads its configuration from environment variables through the single
   `Settings` object. No `os.getenv` outside `shared_kernel/config`.

---

## 3. Components

### 3.1 Package structure to be populated in Phase 1

The Architect has already created the directory tree, the `__init__.py` files, the ports, the shared
contracts, and the redirect pipeline. Files marked **[DEV]** are yours to create in this phase.

```
src/urlshortener/
├── shared_kernel/
│   ├── config/settings.py           [DONE] Settings (pydantic-settings)
│   ├── logging/structured_logging.py[DONE] configure_logging(), get_logger()
│   ├── time/clock.py                [DONE] Clock protocol + SystemClock
│   └── domain/errors.py             [DONE] DomainError base
│
├── contracts/events/click_event.py  [DONE] ClickEvent v1 (producer/consumer contract)
│
├── link_management/                 BOUNDED CONTEXT — write side (Management API)
│   ├── domain/
│   │   ├── model/link.py            [DONE-shape] Link entity fields; [DEV] factory/invariants
│   │   ├── value_objects/short_code.py      [DONE-shape] [DEV] base62 + length invariant
│   │   ├── value_objects/destination_url.py [DONE-shape] [DEV] absolute-URL invariant
│   │   ├── errors.py                [DONE] ShortCodeGenerationExhausted, InvalidDestinationUrl
│   │   └── ports/
│   │       ├── link_repository.py   [DONE] LinkRepository Protocol
│   │       └── short_code_generator.py [DONE] ShortCodeGenerator Protocol
│   ├── application/
│   │   ├── dto/create_link_command.py [DEV]
│   │   ├── dto/link_view.py           [DEV]
│   │   └── services/link_creation_service.py [DEV]
│   ├── infrastructure/
│   │   ├── persistence/orm.py                    [DEV] SQLAlchemy declarative mapping for links
│   │   ├── persistence/engine.py                 [DEV] async engine/session factory
│   │   ├── persistence/sqlalchemy_link_repository.py [DEV]
│   │   └── shortcode/base62_short_code_generator.py  [DEV]
│   └── api/
│       ├── dependencies.py          [DEV] reads app.state, returns application types only
│       ├── schemas/link_schemas.py  [DEV] CreateLinkRequest / CreateLinkResponse
│       └── routers/link_router.py   [DEV] POST /links
│
├── redirection/                     BOUNDED CONTEXT — read/hot path (Redirection Engine)
│   ├── domain/
│   │   ├── model/redirect_context.py   [DONE] immutable request facts
│   │   ├── model/redirect_decision.py  [DONE] RedirectToDestination | LinkNotFound
│   │   ├── model/resolved_link.py      [DONE] short_code + destination_url
│   │   ├── model/cached_link.py        [DONE] versioned cache document
│   │   └── ports/{link_cache,link_read_repository,click_event_publisher}.py [DONE]
│   ├── application/
│   │   ├── pipeline/                [DONE] EXTENSION POINT — do not modify, only register into
│   │   ├── services/link_resolution_service.py  [DEV] cache-first resolve + cache fill
│   │   └── services/click_event_dispatcher.py   [DEV] fire-and-forget, never raises
│   ├── infrastructure/
│   │   ├── cache/redis_link_cache.py                       [DEV]
│   │   ├── persistence/sqlalchemy_link_read_repository.py  [DEV] SELECT only
│   │   └── messaging/redis_stream_click_event_publisher.py [DEV]
│   └── api/
│       ├── dependencies.py                  [DEV]
│       ├── middleware/                      [DONE-empty] Phase 3 lands here — leave empty
│       └── routers/redirect_router.py       [DEV] GET /{short_code}
│
├── analytics/                       BOUNDED CONTEXT — click ingestion (stub in Phase 1)
│   ├── domain/ports/{click_event_handler,click_event_subscriber}.py [DONE]
│   ├── application/services/logging_click_event_handler.py [DEV] logs the event, nothing else
│   └── infrastructure/messaging/redis_stream_click_event_subscriber.py [DEV]
│
└── apps/                            COMPOSITION ROOTS
    ├── management_api/{main.py,container.py}   [DEV]
    ├── redirection_engine/{main.py,container.py} [DEV]
    └── click_consumer/main.py                  [DEV]
```

```plantuml
@startuml C4_Component_Phase1
!define C4P https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master
!include C4P/C4_Component.puml

title Component Diagram — Phase 1 MVP (Management API + Redirection Engine + Stub Consumer)

Person(creator, "Link Creator")
Person(visitor, "Visitor")
ContainerDb(pg, "PostgreSQL")
ContainerDb(redis, "Redis", "cache + stream")

Container_Boundary(capi, "Management API") {
  Component(linkRouter, "LinkRouter", "api.routers.link_router", "POST /links; validates CreateLinkRequest, returns CreateLinkResponse")
  Component(creationSvc, "LinkCreationService", "application.services", "Generates a unique short code and persists the Link")
  Component(genPort, "ShortCodeGenerator", "domain.ports (Protocol)", "generate() -> ShortCode")
  Component(repoPort, "LinkRepository", "domain.ports (Protocol)", "exists_by_short_code(), add()")
  Component(genImpl, "Base62ShortCodeGenerator", "infrastructure.shortcode", "secrets-based base62 generator")
  Component(repoImpl, "SqlAlchemyLinkRepository", "infrastructure.persistence", "Implements LinkRepository")
  Component(apiRoot, "management_api container", "apps.management_api.container", "Builds adapters, publishes them on app.state")
}

Container_Boundary(cred, "Redirection Engine") {
  Component(redirRouter, "RedirectRouter", "api.routers.redirect_router", "GET /{short_code}; builds RedirectContext, maps RedirectDecision -> Response, schedules the click event")
  Component(pipe, "RedirectPipeline", "application.pipeline", "Runs zero interceptors in Phase 1, then the terminal handler")
  Component(resolveSvc, "LinkResolutionService", "application.services", "Redis -> PostgreSQL -> cache fill; returns a RedirectDecision")
  Component(dispatch, "ClickEventDispatcher", "application.services", "Builds a ClickEvent and publishes it without blocking")
  Component(cachePort, "LinkCache", "domain.ports (Protocol)", "get() / put()")
  Component(readPort, "LinkReadRepository", "domain.ports (Protocol)", "find_by_short_code()")
  Component(pubPort, "ClickEventPublisher", "domain.ports (Protocol)", "publish(ClickEvent)")
  Component(cacheImpl, "RedisLinkCache", "infrastructure.cache", "GET / SETEX of the versioned CachedLink document")
  Component(readImpl, "SqlAlchemyLinkReadRepository", "infrastructure.persistence", "SELECT only")
  Component(pubImpl, "RedisStreamClickEventPublisher", "infrastructure.messaging", "XADD clicks.v1")
  Component(redRoot, "redirection_engine container", "apps.redirection_engine.container", "Builds adapters; registers an EMPTY interceptor list")
}

Container_Boundary(ccon, "Click Consumer (stub)") {
  Component(sub, "RedisStreamClickEventSubscriber", "analytics.infrastructure.messaging", "XREADGROUP loop")
  Component(handler, "LoggingClickEventHandler", "analytics.application.services", "Logs the event as structured JSON and acks")
}

Rel(creator, linkRouter, "POST /links")
Rel(linkRouter, creationSvc, "create_link(CreateLinkCommand)")
Rel(creationSvc, genPort, "generate()")
Rel(creationSvc, repoPort, "exists_by_short_code() / add()")
Rel_U(genImpl, genPort, "implements")
Rel_U(repoImpl, repoPort, "implements")
Rel(repoImpl, pg, "INSERT / SELECT")
Rel(apiRoot, repoImpl, "constructs")
Rel(apiRoot, genImpl, "constructs")

Rel(visitor, redirRouter, "GET /{short_code}")
Rel(redirRouter, pipe, "execute(RedirectContext)")
Rel(pipe, resolveSvc, "terminal handler")
Rel(resolveSvc, cachePort, "get() then put() on miss")
Rel(resolveSvc, readPort, "find_by_short_code() on miss")
Rel(redirRouter, dispatch, "schedule after response")
Rel(dispatch, pubPort, "publish(ClickEvent)")
Rel_U(cacheImpl, cachePort, "implements")
Rel_U(readImpl, readPort, "implements")
Rel_U(pubImpl, pubPort, "implements")
Rel(cacheImpl, redis, "GET/SETEX")
Rel(readImpl, pg, "SELECT")
Rel(pubImpl, redis, "XADD")
Rel(redRoot, cacheImpl, "constructs")

Rel(sub, redis, "XREADGROUP")
Rel(sub, handler, "handle(ClickEvent)")
@enduml
```

### 3.2 Component contracts (authoritative for Phase 1)

#### Ports already created by the Architect — implement against these exactly

| Port | Module | Signature |
| --- | --- | --- |
| `LinkRepository` | `link_management.domain.ports.link_repository` | `async add(link: Link) -> None` · `async exists_by_short_code(short_code: ShortCode) -> bool` · `async find_by_short_code(short_code: ShortCode) -> Link \| None` |
| `ShortCodeGenerator` | `link_management.domain.ports.short_code_generator` | `generate() -> ShortCode` |
| `LinkCache` | `redirection.domain.ports.link_cache` | `async get(short_code: str) -> CachedLink \| None` · `async put(entry: CachedLink, ttl_seconds: int) -> None` |
| `LinkReadRepository` | `redirection.domain.ports.link_read_repository` | `async find_by_short_code(short_code: str) -> ResolvedLink \| None` |
| `ClickEventPublisher` | `redirection.domain.ports.click_event_publisher` | `async publish(event: ClickEvent) -> None` |
| `ClickEventHandler` | `analytics.domain.ports.click_event_handler` | `async handle(event: ClickEvent) -> None` |
| `ClickEventSubscriber` | `analytics.domain.ports.click_event_subscriber` | `async run(handler: ClickEventHandler) -> None` |

#### Behaviour to implement

**`LinkCreationService.create_link(command) -> LinkView`** (P1-01)
1. Validate the destination URL through `DestinationUrl` (absolute, scheme in `{http, https}`).
2. Loop at most `settings.short_code_max_attempts` (default 5): `generate()` → `exists_by_short_code()`;
   take the first free code. If all attempts collide, raise `ShortCodeGenerationExhausted`.
3. Persist via `LinkRepository.add()`. A `UNIQUE` violation from a concurrent insert must be caught
   and treated as a collision (retry), because the check-then-insert window is not atomic.
4. Return `short_code` and `short_url = f"{settings.short_url_base}/{short_code}"`.

**`LinkResolutionService.resolve(context) -> RedirectDecision`** (P1-02) — the pipeline's terminal handler
1. `cache.get(context.short_code)` → hit: return `RedirectToDestination`.
2. Miss: `read_repository.find_by_short_code(...)` → `None`: return `LinkNotFound`.
3. Found: `cache.put(CachedLink(...), ttl_seconds=settings.link_cache_ttl_seconds)` then return
   `RedirectToDestination`.
4. A Redis failure (connection error/timeout) on `get` or `put` must be logged and **degrade to the
   PostgreSQL path**, not fail the request.

**`ClickEventDispatcher.dispatch(context) -> None`** (P1-03)
- Builds a `ClickEvent` from the `RedirectContext` and calls `ClickEventPublisher.publish`.
- **Must catch `BaseException`-minus-`asyncio.CancelledError`, log at WARNING, and return normally.**
  A broker outage can never surface to the visitor.
- Must be invoked such that the redirect response is written **before** the publish completes:
  attach it as a `starlette.background.BackgroundTask` on the `RedirectResponse`, or schedule it with
  `asyncio.create_task` holding a strong reference. It must never be `await`ed inline before the
  response is returned. This is directly testable (P1-02 Scenario 4, P1-03 Scenario 3).

**Redirect router mapping** (P1-02)
| Decision | HTTP response |
| --- | --- |
| `RedirectToDestination` | `302` + `Location: <destination_url>` + `Cache-Control: no-store` |
| `LinkNotFound` | `404` |

`Cache-Control: no-store` on the redirect prevents intermediaries from swallowing future clicks —
important for the analytics promise and required before Phase 3 makes destinations dynamic.

### 3.3 Data model (Phase 1)

```sql
CREATE TABLE links (
    id          BIGSERIAL     PRIMARY KEY,
    short_code  VARCHAR(64)   NOT NULL,
    long_url    TEXT          NOT NULL,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_links_short_code ON links (short_code);
```

Constraints on this schema:
- `short_code` is **not** the primary key (Phase 4 needs per-domain uniqueness — see
  `../overall_architecture.md` §3.4).
- `VARCHAR(64)`, not `CHAR(7)` — Phase 4 custom aliases are longer than generated codes.
- Delivered as an **Alembic migration** (`alembic upgrade head`), run as a container start/CI step, not
  via `create_all()` at import time. This satisfies P1-01 Scenario 4 and is what Phase 2's K8s init
  container will call.

### 3.4 Redis key contract (Phase 1)

| Purpose | Key / stream | Value | TTL |
| --- | --- | --- | --- |
| Link cache | `link:v1:{short_code}` | `CachedLink` JSON (`schema_version`, `short_code`, `destination_url`) | `settings.link_cache_ttl_seconds` (default 3600) |
| Click events | Stream `clicks.v1`, consumer group `analytics` | `ClickEvent` JSON in field `payload` | stream `MAXLEN ~ settings.click_stream_max_len` |

Cache the JSON document, never a bare URL string — see AD-5 in the overall architecture.

### 3.5 Containerization & CI (P1-04)

| Artifact | Location | Requirement |
| --- | --- | --- |
| `deploy/docker/Dockerfile.management_api` | created in this phase | Multi-stage, non-root user, `python:3.12-slim` base, `HEALTHCHECK` hitting `/healthz` |
| `deploy/docker/Dockerfile.redirection_engine` | created in this phase | Same pattern; this image is the Phase 2 K8s Deployment artifact |
| `deploy/docker/Dockerfile.click_consumer` | created in this phase | No HTTP port; `python -m urlshortener.apps.click_consumer.main` |
| `docker-compose.yml` (repo root) | created in this phase | `postgres`, `redis`, `management_api`, `redirection_engine`, `click_consumer` + a migration step; must also run under `podman-compose` per `markdowns/developer_notes.md` §4 |
| `.github/workflows/ci.yml` | created in this phase | On push/PR: install → `black --check`, `isort --check-only`, `ruff check`, `mypy` → `pytest` (unit + **architecture** + integration) → build all three images. Must fail the job on any step failure. |

The three Dockerfiles share one build context (the repo root) and one package; they differ only in
the final `CMD`. Keep them near-identical so Phase 2's Helm chart can treat them uniformly.

<!-- PHASE: Phase 1 MVP END -->

---

## 4. Configuration Surface (Phase 1)

All settings live on `urlshortener.shared_kernel.config.settings.Settings`, prefix `URLSHORTENER_`.

| Setting | Env var | Default | Used by |
| --- | --- | --- | --- |
| `app_env` | `URLSHORTENER_APP_ENV` | `local` | all |
| `log_level` | `URLSHORTENER_LOG_LEVEL` | `INFO` | all |
| `database_url` | `URLSHORTENER_DATABASE_URL` | – (required) | API, Redirection |
| `redis_url` | `URLSHORTENER_REDIS_URL` | – (required) | Redirection, Consumer |
| `short_url_base` | `URLSHORTENER_SHORT_URL_BASE` | `http://localhost:8001` | API |
| `short_code_length` | `URLSHORTENER_SHORT_CODE_LENGTH` | `7` | API |
| `short_code_max_attempts` | `URLSHORTENER_SHORT_CODE_MAX_ATTEMPTS` | `5` | API |
| `link_cache_ttl_seconds` | `URLSHORTENER_LINK_CACHE_TTL_SECONDS` | `3600` | Redirection |
| `click_event_stream` | `URLSHORTENER_CLICK_EVENT_STREAM` | `clicks.v1` | Redirection, Consumer |
| `click_event_consumer_group` | `URLSHORTENER_CLICK_EVENT_CONSUMER_GROUP` | `analytics` | Consumer |
| `click_stream_max_len` | `URLSHORTENER_CLICK_STREAM_MAX_LEN` | `100000` | Redirection |

`Settings` is instantiated **once, in the composition root** (`apps/*/container.py`) and passed down.
No module-level `Settings()` singletons — that breaks test isolation and container config injection.

---

## 5. Future-Proofing: what to create now as a stub, and why

These items are **in Phase 1 scope as structure only**. The Architect has already created the ones
marked *created*. Do not add behaviour to them.

| # | Item | Status | Later phase it unblocks |
| --- | --- | --- | --- |
| F-1 | `redirection/application/pipeline/` — `RedirectInterceptor` Protocol, `RedirectHandler` alias, `RedirectPipeline` | **created** | **Phase 3**: expiration, password gate, geo/device routing register as interceptors; **Phase 4**: pixel interstitial. Phase 1 must wire the pipeline with an **empty interceptor list** — do not bypass it and call the resolution service directly from the router. |
| F-2 | `redirection/api/middleware/` — empty package | **created** | **Phase 3** IP/bot filtering middleware mounts here, ahead of the pipeline. Leave it empty in Phase 1. |
| F-3 | `RedirectDecision` abstract base with `RedirectToDestination` / `LinkNotFound` | **created** | **Phase 3/4** add `AccessDenied`, `LinkExpired`, `ServeInterstitial` as new subclasses. The router's mapping must be written as a dispatch over decision types so new branches are additive. |
| F-4 | `RedirectContext` carrying `client_ip`, `user_agent`, `referrer`, `requested_at` | **created** | **Phase 3** geo/device/bot rules read these fields; **Phase 2** analytics needs them on the event. Phase 1 must populate them even though it uses none of them. |
| F-5 | `CachedLink` versioned document + `link:v1:` key prefix | **created** | **Phase 3** enriches the cached payload with rules; the version prefix enables zero-downtime rollout. |
| F-6 | `ClickEvent` schema with `schema_version`, `event_id`, `client_ip`, `user_agent`, `referrer` | **created** | **Phase 2**'s real consumer needs no producer change. Phase 1 populates every field. |
| F-7 | `ClickEventPublisher` / `ClickEventSubscriber` ports | **created** | **Phase 2** swaps Redis Streams for a Celery/RabbitMQ adapter by writing one new class. |
| F-8 | `/healthz` and `/readyz` on both HTTP services | **[DEV] Phase 1** | **Phase 2** K8s liveness/readiness probes point at them unchanged. |
| F-9 | `Clock` protocol + `SystemClock` | **created** | Deterministic tests now; **Phase 3** expiration evaluation must be time-injectable, never `datetime.now()` inline. |
| F-10 | Alembic migration history | **[DEV] Phase 1** | Every later phase adds columns/tables additively on a linear history. |
| F-11 | Surrogate `id` PK on `links`, `short_code VARCHAR(64)` unique index | **[DEV] Phase 1** | **Phase 4** widens uniqueness to `(domain_id, short_code)` without touching foreign keys. |

### 5.1 Anti-corner-painting checklist for the Redirection Engine

Before you consider P1-02 done, verify all five:

- [ ] The router calls `RedirectPipeline.execute(...)`, **not** `LinkResolutionService.resolve(...)` directly.
- [ ] `RedirectPipeline` is constructed in `apps/redirection_engine/container.py` with an explicit,
      currently-empty, ordered interceptor sequence.
- [ ] `RedirectContext` is fully populated (IP from `X-Forwarded-For` first hop, falling back to the
      peer address; UA; referrer; timestamp from the injected `Clock`).
- [ ] The router maps decisions by type; there is no `if destination is None` special-casing that a new
      decision subclass would silently fall through.
- [ ] Nothing in `urlshortener.redirection` performs a write to PostgreSQL.

---

## 6. Explicitly Out of Scope for Phase 1

Do **not** write any of the following. They belong to later phases and their presence in Phase 1 will
be treated as a scope violation.

| Not now | Belongs to |
| --- | --- |
| Custom aliases, custom domains, QR codes, pixel interstitial pages | Phase 4 |
| Password protection, expiration, access restrictions, IP/bot filtering, geo/device routing | Phase 3 |
| Any `RedirectInterceptor` implementation | Phase 3 |
| User accounts, authentication, ownership, API keys, rate limiting, bulk creation, webhooks | Phase 5 |
| Celery, User-Agent parsing, GeoIP, analytics tables, analytics query endpoints, dashboards | Phase 2 |
| Kubernetes manifests, Helm/Kustomize, Terraform/OpenTofu, ArgoCD | Phase 2 / 5 / 6 |
| `/metrics`, Prometheus, OpenTelemetry instrumentation, Grafana | Phase 2 / 6 |
| Link-in-Bio pages | Phase 6 |
| Link update/delete endpoints, cache invalidation on update | Phase 3 (first mutation feature) |

Note on the last row: because Phase 1 links are immutable, **no cache-invalidation logic is needed**.
Do not build it. The TTL on the cache entry is sufficient and is deliberately the only staleness
control in this phase.

---

## 7. Definition of Done (architecture-level, Phase 1)

1. All four stories' acceptance criteria pass.
2. `pytest tests/architecture` passes — every rule in `./archunit_specs.md` is green.
3. `black --check`, `isort --check-only`, `ruff check`, and `mypy` pass on `src/` and `tests/`.
4. `docker compose up` (and `podman-compose up`) yields a working create-then-redirect round trip.
5. A redirect against a stopped Redis/broker still returns `302`.
6. Every item in §5.1 is checked.

---
*Generated by Architect Agent — scope: phase_1_mvp*
