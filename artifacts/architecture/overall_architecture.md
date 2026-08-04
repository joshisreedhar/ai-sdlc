# Overall C4 Architecture — URL Shortener & Analytics Platform

> **Scope of this document:** the *target* architecture spanning **all six phases** of the development
> plan. It exists to give every phase-scoped design a stable frame of reference so that no phase
> paints a later phase into a corner.
>
> **This document is NOT a build instruction.** Developer and QA agents must build only what is
> described in `./artifacts/architecture/<phase_name>/c4_architecture.md` for the phase they were
> assigned. Anything in this document that is not inside the current phase's artifacts is
> *future context only*.

| Item | Value |
| --- | --- |
| Target stack | Python 3.12, FastAPI, PostgreSQL, Redis, Celery |
| Packaging | OCI images (Docker/Podman), Kubernetes-native |
| Repository model | Single monorepo, single installable package (`src/urlshortener`), multiple deployable apps |
| Architectural style | Modular monolith of bounded contexts, deployed as separate processes (ports & adapters / hexagonal) |

---

## 0. Roadmap at a Glance

| Phase | Name | Architectural delta introduced |
| --- | --- | --- |
| 1 | MVP — Core Redirection Loop | Management API, Redirection Engine, PostgreSQL, Redis cache, click-event publish + stub consumer, containers + CI |
| 2 | Cloud-Native Foundation & Async Analytics | Celery workers, analytics store, K8s/Helm, Prometheus + OTel baseline, analytics query API |
| 3 | Security Controls & Routing Rules | Bot/IP filtering middleware, password interstitial, expiration/access rules, geo/device routing rules |
| 4 | Branding & Conversion Tracking | Custom aliases, custom domains, QR codes + object storage, pixel interstitial page |
| 5 | Automation at Scale | Public REST API + API keys, Redis rate limiting, bulk/CSV creation, webhooks/Zapier, Terraform/OpenTofu |
| 6 | Link-in-Bio & Production Hardening | Link-in-Bio pages, ArgoCD GitOps, Grafana dashboards, full tracing + structured logging |

### 0.1 Load-bearing invariants (true in every phase)

These are the non-negotiables that every phase-scoped design must preserve.

1. **The redirect hot path never blocks on analytics.** Click events are published fire-and-forget;
   the HTTP redirect is returned first.
2. **Read/write separation on the redirect path.** The Redirection Engine performs *reads only*
   against PostgreSQL. All mutation of link state happens in the Management API.
3. **Cache-first resolution.** Redis is authoritative-for-latency; PostgreSQL is authoritative-for-truth.
4. **Bounded contexts do not import each other.** They communicate through the shared
   `contracts` package (event/DTO schemas) or through the database, never through direct imports.
5. **Domain and application layers are framework-free.** No `fastapi`, `sqlalchemy`, `redis`, or
   `celery` imports below the infrastructure layer.
6. **Every service is a container.** No service may assume a local filesystem, a fixed hostname, or
   a non-injected configuration value.

---

## 1. Context

The platform serves four distinct human/system actors and depends on a small set of external systems.
Only a subset is live in any given phase (annotated below).

- **Link Creator / Marketer** — creates and manages links, QR codes, routing rules, and reads analytics.
  Enters in Phase 1 (creation only).
- **Visitor** — the anonymous end user who follows a short link. Enters in Phase 1. From Phase 3
  onward may be challenged (password page), blocked (bot filter), or routed (geo/device). From
  Phase 4 may traverse a pixel interstitial. From Phase 6 may land on a Link-in-Bio page.
- **Automation Client (Zapier / customer scripts)** — machine consumer of the public REST API.
  Enters in Phase 5.
- **Platform Operator (SRE)** — observes and operates the platform. Enters in Phase 2 (metrics),
  fully served in Phase 6 (dashboards, traces, GitOps).

External systems: **GeoIP database** (Phase 2 async, Phase 3 synchronous), **Object storage (S3-compatible)**
(Phase 4), **Ad platform pixels — Meta/Google/TikTok** (Phase 4), **Customer DNS** (Phase 4 domain
verification), **Webhook receivers** (Phase 5), **Cloud provider / Kubernetes** (Phase 2+),
**Observability backends — Prometheus/Grafana/OTel collector/log shipper** (Phase 2, 6).

```plantuml
@startuml C4_Context_Overall
!define C4P https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master
!include C4P/C4_Context.puml

title System Context — URL Shortener & Analytics Platform (all phases)

Person(creator, "Link Creator / Marketer", "Creates short links, QR codes, routing rules; reads analytics")
Person(visitor, "Visitor", "Follows a short link")
Person(operator, "Platform Operator (SRE)", "Operates and observes the platform")
System_Ext(automation, "Automation Client", "Zapier, CI jobs, customer scripts calling the public API [Phase 5]")

System_Boundary(sb, "URL Shortener & Analytics Platform") {
  System(platform, "URL Shortener Platform", "Creates short links, redirects visitors at low latency, and produces click analytics")
}

System_Ext(destination, "Destination Website", "The long URL the visitor is ultimately sent to")
System_Ext(geoip, "GeoIP Database", "MaxMind GeoLite2 or equivalent [Phase 2 async / Phase 3 sync]")
System_Ext(objstore, "Object Storage", "S3-compatible store for QR code images [Phase 4]")
System_Ext(pixels, "Ad Platform Pixels", "Meta / Google Ads / TikTok conversion pixels [Phase 4]")
System_Ext(dns, "Customer DNS", "TXT-record domain ownership verification [Phase 4]")
System_Ext(webhooks, "Customer Webhook Endpoints", "Outbound event delivery [Phase 5]")
System_Ext(obs, "Observability Backends", "Prometheus, Grafana, OTel collector, log shipper [Phase 2 & 6]")

Rel(creator, platform, "Creates and manages links", "HTTPS/JSON")
Rel(visitor, platform, "Requests short URL", "HTTPS")
Rel(platform, visitor, "HTTP 301/302 redirect (or interstitial page)", "HTTPS")
Rel(visitor, destination, "Lands on destination", "HTTPS")
Rel(automation, platform, "Bulk/programmatic link operations [Phase 5]", "HTTPS/JSON + API key")
Rel(platform, geoip, "Resolves IP to location [Phase 2+]")
Rel(platform, objstore, "Stores/serves QR images [Phase 4]")
Rel(visitor, pixels, "Fires conversion pixels from interstitial page [Phase 4]")
Rel(platform, dns, "Verifies TXT challenge [Phase 4]")
Rel(platform, webhooks, "Delivers link/click events [Phase 5]")
Rel(platform, obs, "Exposes /metrics, traces, JSON logs [Phase 2 & 6]")
Rel(operator, obs, "Monitors dashboards and traces")
@enduml
```

---

## 2. Containers

The platform is built as a **modular monolith of bounded contexts** packaged into **independently
deployable processes**. All processes share one Python package (`urlshortener`) and one image build
pipeline; they differ only in their entry point (composition root) and their scaling profile.

Rationale: the Redirection Engine has a fundamentally different scaling and latency profile from the
Management API, so it must scale independently — but the two share the `links` data model, so keeping
them in one repository/package with strict import boundaries (enforced by ArchUnit-equivalent tests)
avoids the distributed-monolith trap of duplicated or drifting schemas.

| Container | Introduced | Runtime | Responsibility |
| --- | --- | --- | --- |
| Management API | Phase 1 | FastAPI (`urlshortener.apps.management_api`) | Link creation & management, later: analytics queries, QR, domains, API keys, bulk, Link-in-Bio |
| Redirection Engine | Phase 1 | FastAPI (`urlshortener.apps.redirection_engine`) | Short-code resolution and redirect; later: filtering middleware, rule evaluation, interstitials |
| Click Consumer | Phase 1 (stub) → Phase 2 (Celery) | Python worker → Celery worker | Consumes click events; later: UA parsing, GeoIP, analytics persistence, webhook dispatch |
| PostgreSQL | Phase 1 | Managed/containerised | Links, and later users, routing rules, domains, API keys, analytics (partitioned) |
| Redis | Phase 1 | Managed/containerised | Link cache, message broker; later Celery broker, rate-limit counters, rule cache |
| Object Storage | Phase 4 | S3-compatible | QR code images |
| Ingress / Gateway | Phase 2 | K8s Ingress + cert-manager | TLS termination, host-based routing (incl. custom domains in Phase 4) |

```plantuml
@startuml C4_Container_Overall
!define C4P https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master
!include C4P/C4_Container.puml

title Container Diagram — URL Shortener & Analytics Platform (all phases)

Person(creator, "Link Creator / Marketer")
Person(visitor, "Visitor")
System_Ext(automation, "Automation Client", "[Phase 5]")

System_Boundary(sb, "URL Shortener & Analytics Platform") {
  Container(ingress, "Ingress / API Gateway", "K8s Ingress + cert-manager", "TLS termination, host & path routing, custom-domain routing [Phase 2 / Phase 4]")

  Container(api, "Management API", "Python, FastAPI", "Link CRUD, QR codes, domains, routing-rule config, analytics queries, public API, Link-in-Bio")
  Container(redirect, "Redirection Engine", "Python, FastAPI", "Cache-first short-code resolution, filtering, rule evaluation, redirect + click-event publish")
  Container(worker, "Click Consumer / Celery Workers", "Python, Celery", "Consumes click events; UA parsing, GeoIP enrichment, analytics persistence, webhook dispatch")

  ContainerDb(pg, "PostgreSQL", "PostgreSQL 16", "Links, users, routing rules, domains, API keys, analytics (partitioned)")
  ContainerDb(redis, "Redis", "Redis 7", "Link cache, message broker/stream, Celery broker, rate-limit counters")
  ContainerDb(objstore, "Object Storage", "S3-compatible", "QR code images [Phase 4]")
}

System_Ext(destination, "Destination Website")
System_Ext(geoip, "GeoIP Database")
System_Ext(obs, "Observability Backends")

Rel(creator, ingress, "Manages links", "HTTPS/JSON")
Rel(automation, ingress, "Public REST API [Phase 5]", "HTTPS/JSON")
Rel(visitor, ingress, "GET /{short_code}", "HTTPS")
Rel(ingress, api, "Routes management traffic", "HTTP")
Rel(ingress, redirect, "Routes redirect traffic", "HTTP")

Rel(api, pg, "Reads & writes link/config state", "asyncpg / SQLAlchemy")
Rel(api, redis, "Invalidates cache, rate limits [Phase 5]", "RESP")
Rel(api, objstore, "Stores QR images [Phase 4]", "S3 API")

Rel(redirect, redis, "Cache-first lookup; publishes click events", "RESP")
Rel(redirect, pg, "READ-ONLY fallback lookup", "asyncpg / SQLAlchemy")
Rel(redirect, visitor, "301/302 redirect or interstitial HTML", "HTTPS")
Rel(visitor, destination, "Follows Location header")

Rel(redis, worker, "Delivers click events", "Stream / Celery broker")
Rel(worker, pg, "Writes enriched analytics [Phase 2]", "SQL")
Rel(worker, geoip, "Resolves IP to location [Phase 2]")

Rel(api, obs, "/metrics, traces, JSON logs")
Rel(redirect, obs, "/metrics, traces, JSON logs")
Rel(worker, obs, "/metrics, traces, JSON logs")
@enduml
```

### 2.1 Why the Redirection Engine is a separate container from day one

Splitting it in Phase 1 costs almost nothing (one extra Dockerfile and composition root) but buys:
independent horizontal scaling in Phase 2; an isolated blast radius for the Phase 3 middleware chain;
and the ability to give the redirect path its own resource limits and latency SLO. Merging later
would be a breaking deployment change; splitting now is free.

---

## 3. Components

### 3.1 Package topology (target state)

```
src/urlshortener/
├── shared_kernel/       cross-cutting: settings, logging, clock, base errors
├── contracts/           versioned inter-process schemas (click events, later webhook events)
├── link_management/     BOUNDED CONTEXT — write side of links, domains, QR, API keys, bulk
├── redirection/         BOUNDED CONTEXT — read/hot path: resolve, filter, route, redirect
├── analytics/           BOUNDED CONTEXT — click ingestion, enrichment, query surface
└── apps/                composition roots (one per deployable process)
```

Each bounded context uses the same four-layer internal structure:

| Layer | May depend on | Contains |
| --- | --- | --- |
| `domain` | `shared_kernel`, `contracts`, stdlib, `pydantic` | Entities, value objects, domain errors, **ports (Protocols)** |
| `application` | `domain` (+ above) | Use-case services, orchestration, the redirect pipeline |
| `infrastructure` | `domain` (+ above) | Adapters: SQLAlchemy repositories, Redis cache, broker publishers/consumers, GeoIP, S3 |
| `api` | `application`, `domain` (+ above) | FastAPI routers, request/response schemas, middleware, dependency accessors |
| `apps` | everything | Composition roots: build concrete adapters, wire them, expose `app` / `main()` |

`api` **must not** import `infrastructure`. Concrete adapters are constructed only in `apps/*/container.py`
and published on `app.state`; `api/dependencies.py` reads them back typed as the *application/domain*
abstraction. This is what keeps the API layer testable with fakes and keeps the Dependency Inversion
Principle enforceable by a static test.

### 3.2 Component view

```plantuml
@startuml C4_Component_Overall
!define C4P https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master
!include C4P/C4_Component.puml

title Component Diagram — Redirection Engine & Management API (all phases)

ContainerDb(redis, "Redis", "Cache + broker")
ContainerDb(pg, "PostgreSQL", "System of record")

Container_Boundary(redirect, "Redirection Engine") {
  Component(mw, "Filtering Middleware Chain", "FastAPI middleware", "IP deny-list, bot signatures [Phase 3]")
  Component(router, "Redirect Router", "FastAPI router", "GET /{short_code}; builds RedirectContext, maps RedirectDecision to an HTTP response")
  Component(pipeline, "Redirect Pipeline", "Application", "Ordered interceptor chain terminating in link resolution — THE Phase 3+ extension point")
  Component(resolution, "Link Resolution Service", "Application", "Cache-first resolve: Redis -> PostgreSQL -> cache fill")
  Component(dispatcher, "Click Event Dispatcher", "Application", "Fire-and-forget publish; never raises into the request path")
  Component(rules, "Routing Rule Evaluator", "Application interceptor", "Expiration, access, geo, device precedence [Phase 3]")
  Component(cacheAdp, "Redis Link Cache", "Infrastructure", "Implements LinkCache port")
  Component(readRepo, "Link Read Repository", "Infrastructure", "READ-ONLY SQLAlchemy adapter, implements LinkReadRepository port")
  Component(pubAdp, "Click Event Publisher", "Infrastructure", "Redis Streams adapter, implements ClickEventPublisher port")
}

Container_Boundary(api, "Management API") {
  Component(linkRouter, "Link Router", "FastAPI router", "POST /links and later CRUD, aliases, domains, QR")
  Component(creation, "Link Creation Service", "Application", "Generates short code, enforces uniqueness, persists")
  Component(codeGen, "Short Code Generator", "Infrastructure", "Base62 random generator, implements ShortCodeGenerator port")
  Component(writeRepo, "Link Repository", "Infrastructure", "Read/write SQLAlchemy adapter, implements LinkRepository port")
  Component(analyticsQ, "Analytics Query Service", "Application", "Aggregated click metrics [Phase 2]")
}

Rel(mw, router, "passes allowed requests to")
Rel(router, pipeline, "execute(RedirectContext)")
Rel(pipeline, rules, "invokes registered interceptors [Phase 3]")
Rel(pipeline, resolution, "terminal handler")
Rel(resolution, cacheAdp, "get / put")
Rel(resolution, readRepo, "find_by_short_code (cache miss only)")
Rel(router, dispatcher, "schedules after response")
Rel(dispatcher, pubAdp, "publish(ClickEvent)")
Rel(cacheAdp, redis, "GET/SETEX")
Rel(pubAdp, redis, "XADD")
Rel(readRepo, pg, "SELECT only")

Rel(linkRouter, creation, "create_link(command)")
Rel(creation, codeGen, "generate()")
Rel(creation, writeRepo, "exists_by_short_code / add")
Rel(writeRepo, pg, "SELECT / INSERT / UPDATE")
Rel(analyticsQ, pg, "aggregate queries [Phase 2]")
@enduml
```

### 3.3 The Redirect Pipeline — the platform's primary extension point

Every future change to redirect *behaviour* (Phases 3 and 4) is an **addition of an interceptor**, not
a modification of the router or the resolution service. This is the Open/Closed Principle applied to
the hottest, riskiest code path in the product.

```
RedirectContext ──► [ interceptor 1 ] ──► [ interceptor 2 ] ──► ... ──► terminal handler ──► RedirectDecision
```

Planned interceptor registration order (established in Phase 3, kept stable thereafter):

| Order | Interceptor | Phase | Effect |
| --- | --- | --- | --- |
| — | IP/bot filtering (FastAPI *middleware*, ahead of the pipeline) | 3 | Rejects abusive traffic before any lookup |
| 1 | Expiration & access-restriction | 3 | May yield an "expired/restricted" decision |
| 2 | Password gate | 3 | May yield an "auth interstitial" decision |
| 3 | Geo/device routing | 3 | May override the destination URL |
| 4 | Conversion-pixel interstitial | 4 | May yield a "pixel interstitial page" decision |
| terminal | Link resolution | 1 | Cache-first lookup → destination or not-found |

`RedirectDecision` is a closed-for-modification, open-for-extension result hierarchy: Phase 1 ships
`RedirectToDestination` and `LinkNotFound`; later phases add `ServeInterstitial`, `AccessDenied`, and
`LinkExpired` as new subclasses. The router's decision→response mapping grows by adding branches,
never by changing existing ones.

### 3.4 Data model evolution

`links` is the one table that every phase touches. Phase 1 must therefore choose keys that later
phases can extend **additively**:

| Decision (Phase 1) | Why it matters later |
| --- | --- |
| Surrogate primary key (`id`), **not** `short_code` as PK | Phase 4 makes uniqueness *per custom domain*; the unique constraint can be widened to `(domain_id, short_code)` without rewriting foreign keys |
| `short_code` unique + indexed, `VARCHAR(64)` | Phase 4 custom aliases can be longer than the 6–8 char random codes |
| `created_at`/`updated_at` timestamptz | Baseline for every later audit/expiry feature |
| No `user_id` yet, but no assumption of a single owner | Phase 5 adds `owner_id` as a nullable FK, backfilled later |

Tables added later: `users`, `custom_domains`, `routing_rules`, `link_access_rules`, `api_keys`,
`webhook_subscriptions`, `bio_pages`, and the partitioned `click_events` / aggregate tables. All are
additive; none require altering Phase 1 columns.

### 3.5 Cache & event contract versioning

Two cross-process contracts must be versioned from Phase 1, because changing them later without a
version would cause silent production breakage during rolling deploys:

- **Cache entries** — key `link:v1:{short_code}`, value is a JSON document with a `schema_version`
  field, *not* a bare URL string. Phase 3 adds rule data to the cached document; the version prefix
  lets old and new pods coexist during a rollout.
- **Click events** — a `ClickEvent` schema carrying `schema_version`, `event_id`, `short_code`,
  `occurred_at`, `client_ip`, `user_agent`, `referrer`. Phase 1 populates all of these even though it
  consumes none of them, so Phase 2's real consumer needs no producer change.

---

## 4. Cross-Cutting Concerns (target state)

| Concern | Approach | First delivered |
| --- | --- | --- |
| Configuration | `pydantic-settings` `Settings` object, env-var driven, injected at the composition root; no module-level env reads | Phase 1 |
| Logging | Structured JSON to stdout | Phase 1 (baseline), Phase 6 (standardised + shipped) |
| Metrics | `/metrics` Prometheus endpoint per service | Phase 2 |
| Tracing | OpenTelemetry across FastAPI + Celery | Phase 2 (baseline), Phase 6 (full) |
| Health | `/healthz` (liveness) and `/readyz` (readiness incl. dependency checks) | Phase 1 shape, Phase 2 wired to K8s probes |
| Migrations | Alembic, one linear history for the whole package | Phase 1 |
| AuthN/AuthZ | API keys (Phase 5); no user auth in Phases 1–4 | Phase 5 |
| Rate limiting | Redis sliding window middleware | Phase 5 |

---

## 5. Key Architectural Decisions

| # | Decision | Alternatives rejected | Rationale |
| --- | --- | --- | --- |
| AD-1 | Monorepo, one package, multiple composition roots | Separate repos per service | Keeps the shared `links` contract in one place; import boundaries are statically enforceable instead of relying on API discipline |
| AD-2 | Ports & adapters per bounded context | Layered MVC over a shared ORM | Lets Phase 1 unit-test the redirect path with in-memory fakes and lets Phase 3 add interceptors without touching adapters |
| AD-3 | Redis as both cache and broker in Phase 1 | RabbitMQ from the start | Avoids a second infrastructure dependency for the MVP; the `ClickEventPublisher` port makes a later broker swap a one-adapter change |
| AD-4 | Interceptor pipeline on the redirect path | `if` branches in the router as features land | The router would otherwise become the highest-churn, highest-risk file in the system |
| AD-5 | Versioned cache document instead of raw URL string | `SET short_code -> url` | Enables zero-downtime rollouts when Phase 3 enriches the cached payload |
| AD-6 | PostgreSQL (partitioned) for analytics before ClickHouse | ClickHouse in Phase 2 | Defers operational cost until volume justifies it; the analytics repository port allows the swap |
| AD-7 | Redirect writes nothing to PostgreSQL, ever | Inline click counter update | Directly protects the latency SLO and removes write contention from the hot path |

---

## 6. Phase Boundary Index

| Phase | Architecture artifacts |
| --- | --- |
| phase_1_mvp | `./artifacts/architecture/phase_1_mvp/{c4_architecture,system_diagrams,archunit_specs}.md` |
| phase_2_cloud_native_analytics | *not yet generated* |
| phase_3_security_routing | *not yet generated* |
| phase_4_branding_conversion | *not yet generated* |
| phase_5_automation_scale | *not yet generated* |
| phase_6_bio_hardening | *not yet generated* |

---
*Generated by Architect Agent*
