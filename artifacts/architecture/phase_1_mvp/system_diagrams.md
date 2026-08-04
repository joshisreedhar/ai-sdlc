# System Diagrams — Phase 1: MVP (Core Redirection Loop)

**Phase ID:** `phase_1_mvp`
**Companion artifacts:** `./c4_architecture.md`, `./archunit_specs.md`

<!-- PHASE: Phase 1 MVP START -->

## 1. Module Dependency Diagrams

### 1.1 Top-level package dependencies

Dependencies are strictly unidirectional. `shared_kernel` and `contracts` are sinks (they import
nothing from the platform); `apps` is the only source that may reach every layer.

```plantuml
@startuml Module_TopLevel_Phase1
title Module Dependencies — Top Level (Phase 1)
skinparam packageStyle rectangle
skinparam linetype ortho

package "urlshortener.apps" as apps #LightYellow {
  component "management_api" as appApi
  component "redirection_engine" as appRed
  component "click_consumer" as appCon
}

package "urlshortener.link_management" as lm #LightBlue
package "urlshortener.redirection" as rd #LightBlue
package "urlshortener.analytics" as an #LightBlue

package "urlshortener.contracts" as ct #LightGreen {
  component "events.ClickEvent (v1)" as ce
}
package "urlshortener.shared_kernel" as sk #LightGreen {
  component "config.Settings" as cfg
  component "logging" as log
  component "time.Clock" as clk
  component "domain.errors" as err
}

appApi --> lm
appRed --> rd
appCon --> an

lm --> sk
rd --> sk
an --> sk
rd --> ct
an --> ct
apps --> sk
apps --> ct

note right of ct
  contracts/ is the ONLY thing shared between
  the producer (redirection) and the consumer
  (analytics). They must never import each other.
end note

note bottom of lm
  FORBIDDEN in every phase:
    link_management <-> redirection
    link_management <-> analytics
    redirection     <-> analytics
  Enforced by archunit rule D-01.
end note
@enduml
```

### 1.2 Layering inside a bounded context

Identical in `link_management`, `redirection`, and `analytics`. Note that `api` does **not** depend on
`infrastructure`: concrete adapters are constructed only in the composition root and handed to the API
layer as their abstract (application/domain) types.

```plantuml
@startuml Module_Layers_Phase1
title Module Dependencies — Layering within a Bounded Context (Phase 1)
skinparam packageStyle rectangle
skinparam linetype ortho

package "apps.<service> (composition root)" as root #LightYellow

package "api" as api #Wheat {
  component "routers" as routers
  component "schemas" as schemas
  component "dependencies" as deps
  component "middleware  <<empty in Phase 1>>" as mw
}

package "application" as app #LightCyan {
  component "services" as svc
  component "dto" as dto
  component "pipeline  <<redirection only>>" as pipe
}

package "domain" as dom #LightGreen {
  component "model / value_objects" as model
  component "ports  <<Protocol>>" as ports
  component "errors" as derr
}

package "infrastructure" as infra #Pink {
  component "persistence" as pers
  component "cache" as cache
  component "messaging" as msg
}

routers --> svc
routers --> schemas
routers --> deps
deps ..> svc : "returns application/domain types only"
mw ..> routers : "Phase 3 inserts here"

svc --> ports
svc --> model
pipe --> model
svc --> dto

pers ..|> ports : implements
cache ..|> ports : implements
msg ..|> ports : implements

root --> infra : "constructs concrete adapters"
root --> api : "mounts routers"
root --> app : "builds services, injects adapters"

note right of api
  api -X-> infrastructure
  (archunit rule L-04)
end note

note bottom of dom
  domain imports nothing from
  application / infrastructure / api / apps
  and no web/db framework
  (archunit rules L-01, L-05)
end note
@enduml
```

### 1.3 Redirection Engine internals — the Phase 3 extension seam

The single most important structural decision of Phase 1: the router talks to a **pipeline**, and the
pipeline holds an ordered — currently empty — list of interceptors. Phase 3 adds classes; it changes
no existing file except the composition root's interceptor list.

```plantuml
@startuml Module_RedirectPipeline_Phase1
title Module Dependencies — Redirect Pipeline Extension Seam
skinparam packageStyle rectangle
skinparam linetype ortho

package "redirection.api" #Wheat {
  component "redirect_router" as router
  package "middleware" as mw #WhiteSmoke {
    component "<<empty in Phase 1>>" as mwEmpty
  }
}

package "redirection.application" #LightCyan {
  package "pipeline" as pkgPipe {
    interface "RedirectInterceptor\n(Protocol)" as IInt
    component "RedirectPipeline" as Pipe
    component "RedirectHandler\n(type alias)" as Handler
  }
  package "services" as pkgSvc {
    component "LinkResolutionService\n<<terminal handler>>" as Resolve
    component "ClickEventDispatcher" as Disp
  }
}

package "redirection.domain" #LightGreen {
  component "RedirectContext" as Ctx
  component "RedirectDecision\n+ RedirectToDestination\n+ LinkNotFound" as Dec
  interface "LinkCache" as ILC
  interface "LinkReadRepository" as ILR
  interface "ClickEventPublisher" as ICP
}

package "redirection.infrastructure" #Pink {
  component "RedisLinkCache" as RLC
  component "SqlAlchemyLinkReadRepository" as SRR
  component "RedisStreamClickEventPublisher" as RCP
}

package "apps.redirection_engine" #LightYellow {
  component "container.py" as Cont
}

router --> Pipe : execute(ctx)
router --> Ctx
router --> Dec
router --> Disp
Pipe --> IInt : "ordered, EMPTY in Phase 1"
Pipe --> Handler
Handler ..> Resolve : "bound to"
Resolve --> ILC
Resolve --> ILR
Resolve --> Dec
Disp --> ICP
RLC ..|> ILC
SRR ..|> ILR
RCP ..|> ICP
Cont --> RLC
Cont --> SRR
Cont --> RCP
Cont --> Pipe : "RedirectPipeline(terminal=resolve, interceptors=())"

note right of IInt #LightYellow
  EVOLUTION PORT (Phase 3 / Phase 4)
  Future implementations plug in here
  with NO change to router, pipeline
  or resolution service:
    - ExpirationInterceptor        [P3]
    - PasswordGateInterceptor      [P3]
    - GeoDeviceRoutingInterceptor  [P3]
    - PixelInterstitialInterceptor [P4]
  DO NOT IMPLEMENT ANY OF THESE IN PHASE 1.
end note

note bottom of mw #LightYellow
  EVOLUTION PORT (Phase 3)
  IP deny-list and bot-signature
  middleware mount here, ahead of
  the pipeline. Package exists and
  stays EMPTY in Phase 1.
end note
@enduml
```

### 1.4 Click-event producer/consumer seam

```plantuml
@startuml Module_ClickEvent_Phase1
title Module Dependencies — Click Event Contract Seam
skinparam packageStyle rectangle

package "urlshortener.contracts.events" #LightGreen {
  component "ClickEvent  (schema_version = 1)" as CE
}

package "urlshortener.redirection" #LightBlue {
  component "ClickEventDispatcher" as D
  interface "ClickEventPublisher" as IP
  component "RedisStreamClickEventPublisher" as RP
}

package "urlshortener.analytics" #LightBlue {
  interface "ClickEventSubscriber" as IS
  interface "ClickEventHandler" as IH
  component "RedisStreamClickEventSubscriber" as RS
  component "LoggingClickEventHandler\n<<STUB — logs only>>" as LH
}

queue "Redis Stream\nclicks.v1" as Q

D --> IP
RP ..|> IP
RP --> CE
RP --> Q
Q --> RS
RS ..|> IS
LH ..|> IH
RS --> IH
RS --> CE

note bottom of LH #LightYellow
  EVOLUTION PORT (Phase 2)
  Phase 2 replaces LoggingClickEventHandler with
  a Celery-backed enrichment handler (UA parsing,
  GeoIP, analytics persistence) and may replace
  RedisStreamClickEventSubscriber with a Celery
  consumer. Neither the ClickEvent schema nor the
  Redirection Engine changes.
end note
@enduml
```

---

## 2. Sequence Diagrams

### 2.1 P1-01 — Create a short link (synchronous)

```plantuml
@startuml Seq_CreateLink_Phase1
title P1-01 — Create Short Link
autonumber

actor Creator
participant "LinkRouter\n(api.routers)" as R
participant "LinkCreationService\n(application)" as S
participant "Base62ShortCodeGenerator\n(infrastructure)" as G
participant "SqlAlchemyLinkRepository\n(infrastructure)" as Repo
database "PostgreSQL" as PG

Creator -> R : POST /links {"long_url": "..."}
activate R
R -> R : validate CreateLinkRequest (Pydantic)
note right of R
  Malformed / non-absolute URL ->
  422 returned here, nothing persisted.
  (AC Scenario 2)
end note
R -> S : create_link(CreateLinkCommand)
activate S
S -> S : DestinationUrl(long_url) invariant check

loop until unique, max settings.short_code_max_attempts
  S -> G : generate()
  activate G
  G --> S : ShortCode
  deactivate G
  S -> Repo : exists_by_short_code(code)
  activate Repo
  Repo -> PG : SELECT 1 FROM links WHERE short_code = ?
  PG --> Repo : row / none
  Repo --> S : bool
  deactivate Repo
end
note right of S
  AC Scenario 3: collision -> retry.
  The check-then-insert window is NOT atomic,
  so a UNIQUE violation on add() must also be
  caught and retried as a collision.
end note

S -> Repo : add(Link)
activate Repo
Repo -> PG : INSERT INTO links (...)
alt unique violation (concurrent insert)
  PG --> Repo : IntegrityError
  Repo --> S : raises
  S -> S : treat as collision, continue loop
else success
  PG --> Repo : committed
  Repo --> S : None
end
deactivate Repo
S --> R : LinkView(short_code, short_url)
deactivate S
R --> Creator : 201 {"short_code", "short_url"}
deactivate R

note over Creator, PG #LightYellow
  EVOLUTION (later phases, DO NOT BUILD NOW):
  - Phase 4 inserts an "alias supplied?" branch before generation
    and a domain-scoped uniqueness check.
  - Phase 5 inserts API-key authentication and rate limiting
    ahead of the router, plus a bulk/batch variant of this flow.
  - Phase 3 adds optional password/expiry fields on the command.
end note
@enduml
```

### 2.2 P1-02 + P1-03 — Redirect with cache hit (the hot path)

```plantuml
@startuml Seq_RedirectCacheHit_Phase1
title P1-02 / P1-03 — Redirect (Redis cache HIT) with non-blocking click publish
autonumber

actor Visitor
participant "RedirectRouter\n(api.routers)" as R
participant "RedirectPipeline\n(application.pipeline)" as P
participant "LinkResolutionService\n(application.services)" as S
participant "RedisLinkCache\n(infrastructure.cache)" as C
database "Redis" as REDIS
participant "ClickEventDispatcher\n(application.services)" as D
participant "RedisStreamClickEventPublisher\n(infrastructure.messaging)" as PUB

Visitor -> R : GET /{short_code}
activate R
note left of R #LightYellow
  EVOLUTION (Phase 3): IP / bot filtering
  middleware executes HERE, before the router,
  and may short-circuit with 403.
  Package redirection/api/middleware exists
  but is EMPTY in Phase 1.
end note

R -> R : build RedirectContext\n(short_code, client_ip, user_agent, referrer, Clock.now())
R -> P : execute(context)
activate P
note right of P #LightYellow
  EVOLUTION (Phase 3/4): interceptors run here,
  in registration order, before the terminal
  handler. Phase 1 registers ZERO interceptors,
  so execute() goes straight to the terminal handler.
end note
P -> S : resolve(context)   <<terminal handler>>
activate S
S -> C : get(short_code)
activate C
C -> REDIS : GET link:v1:{short_code}
REDIS --> C : CachedLink JSON
C --> S : CachedLink
deactivate C
S --> P : RedirectToDestination(url, 302)
deactivate S
note right of S
  AC Scenario 1: cache hit must NOT query PostgreSQL.
end note
P --> R : RedirectDecision
deactivate P

R -> R : map decision -> RedirectResponse(302,\n Location=url, Cache-Control=no-store)
R -> R : attach BackgroundTask(dispatcher.dispatch, context)
R --> Visitor : **302 Found** (response written)
deactivate R
note over R, Visitor
  AC P1-02/4 + P1-03/3: the response is
  written BEFORE any publish work begins.
  dispatch() must never be awaited inline.
end note

== after the response is sent ==
R -->> D : dispatch(context)   <<async, fire-and-forget>>
activate D
D -> D : build ClickEvent(schema_version=1, event_id, short_code,\n occurred_at, client_ip, user_agent, referrer)
D -> PUB : publish(event)
activate PUB
PUB -> REDIS : XADD clicks.v1 MAXLEN ~ N payload=<json>
alt broker unavailable / timeout
  REDIS --> PUB : error
  PUB --> D : raises
  D -> D : log WARNING, swallow
  note right of D
    AC P1-03/2: a publish failure must never
    affect the already-sent redirect.
  end note
else ok
  REDIS --> PUB : stream id
  PUB --> D : None
end
deactivate PUB
deactivate D
@enduml
```

### 2.3 P1-02 — Redirect with cache miss (PostgreSQL fallback + cache fill)

```plantuml
@startuml Seq_RedirectCacheMiss_Phase1
title P1-02 — Redirect (cache MISS -> PostgreSQL fallback -> cache fill) and 404 path
autonumber

actor Visitor
participant "RedirectRouter" as R
participant "RedirectPipeline" as P
participant "LinkResolutionService" as S
participant "RedisLinkCache" as C
participant "SqlAlchemyLinkReadRepository" as RR
database "Redis" as REDIS
database "PostgreSQL" as PG

Visitor -> R : GET /{short_code}
activate R
R -> P : execute(RedirectContext)
activate P
P -> S : resolve(context)
activate S

S -> C : get(short_code)
C -> REDIS : GET link:v1:{short_code}
REDIS --> C : (nil)
C --> S : None

S -> RR : find_by_short_code(short_code)
activate RR
RR -> PG : SELECT short_code, long_url FROM links WHERE short_code = ?
note right of RR
  READ ONLY. The Redirection Engine never issues
  INSERT/UPDATE/DELETE (archunit rule N-08).
end note

alt link exists
  PG --> RR : row
  RR --> S : ResolvedLink
  deactivate RR
  S -> C : put(CachedLink(v1, code, url), ttl=link_cache_ttl_seconds)
  C -> REDIS : SETEX link:v1:{short_code} ttl <json>
  note right of C
    AC Scenario 2: subsequent requests hit the cache.
    A Redis failure here is logged and ignored -
    the redirect still succeeds.
  end note
  S --> P : RedirectToDestination(url, 302)
  P --> R : decision
  R --> Visitor : 302 Found + Location
else link does not exist
  PG --> RR : no rows
  RR --> S : None
  S --> P : LinkNotFound(short_code)
  P --> R : decision
  R --> Visitor : 404 Not Found
  note right of R
    AC Scenario 3: no redirect attempted.
    Negative caching is deliberately NOT implemented
    in Phase 1 (no invalidation story exists yet).
  end note
end
deactivate S
deactivate P
deactivate R

note over Visitor, PG #LightYellow
  EVOLUTION (Phase 3): the cached document gains
  routing-rule / expiry / password fields. Because the
  cache value is a VERSIONED JSON document under the
  key prefix "link:v1:", Phase 3 can bump to "link:v2:"
  and roll out with zero downtime. Do NOT cache a bare
  URL string.
end note
@enduml
```

### 2.4 P1-03 — Stub consumer proves the publish→consume path

```plantuml
@startuml Seq_StubConsumer_Phase1
title P1-03 — Stub click-event consumer (proves deliverability only)
autonumber

participant "click_consumer\n(apps.click_consumer.main)" as M
participant "RedisStreamClickEventSubscriber\n(analytics.infrastructure.messaging)" as SUB
participant "LoggingClickEventHandler\n(analytics.application.services)" as H
database "Redis Stream clicks.v1" as REDIS

M -> M : configure_logging(settings.log_level)
M -> SUB : run(handler)
activate SUB
SUB -> REDIS : XGROUP CREATE clicks.v1 analytics $ MKSTREAM (idempotent)
loop forever
  SUB -> REDIS : XREADGROUP GROUP analytics <consumer> BLOCK n COUNT k
  REDIS --> SUB : [entries]
  loop each entry
    SUB -> SUB : parse payload -> ClickEvent (contracts.events)
    SUB -> H : handle(event)
    activate H
    H -> H : logger.info("click_event_received", extra={...})
    note right of H
      STUB ONLY. No User-Agent parsing,
      no GeoIP, no persistence, no aggregation.
      AC Scenario 4 is satisfied by the log line.
    end note
    H --> SUB : None
    deactivate H
    SUB -> REDIS : XACK clicks.v1 analytics <id>
  end
end
deactivate SUB

note over M, REDIS #LightYellow
  EVOLUTION (Phase 2): this whole process is replaced by
  Celery workers that consume the SAME clicks.v1 stream and
  the SAME ClickEvent schema, then enrich (UA parse, GeoIP)
  and persist to the analytics store. Keeping the handler
  behind the ClickEventHandler port means Phase 2 swaps one
  class, not the pipeline.
end note
@enduml
```

### 2.5 P1-04 — Local stack startup and CI pipeline

```plantuml
@startuml Seq_ContainerCI_Phase1
title P1-04 — Containerized local stack + CI
autonumber

actor Developer
participant "docker/podman compose" as CMP
participant "migrate (one-shot)" as MIG
participant "management_api" as API
participant "redirection_engine" as RED
participant "click_consumer" as CON
database "postgres" as PG
database "redis" as REDIS

Developer -> CMP : compose up
CMP -> PG : start (healthcheck: pg_isready)
CMP -> REDIS : start (healthcheck: redis-cli ping)
CMP -> MIG : run `alembic upgrade head`  (depends_on: postgres healthy)
MIG -> PG : CREATE TABLE links + unique index
note right of MIG
  AC P1-01/4: schema is guaranteed present
  before the first request is served.
end note
MIG --> CMP : exit 0
CMP -> API : start (depends_on: migrate completed_successfully)
CMP -> RED : start (depends_on: migrate completed_successfully)
CMP -> CON : start (depends_on: redis healthy)
Developer -> API : POST /links
Developer -> RED : GET /{short_code}
RED --> Developer : 302
note over Developer, CON
  AC P1-04/2: end-to-end create-then-redirect
  using only containerized services.
end note

== CI (push / pull_request) ==
participant "CI runner" as CI
CI -> CI : install deps (dev extras)
CI -> CI : black --check . && isort --check-only . && ruff check .
CI -> CI : mypy src tests
CI -> CI : pytest tests/architecture   <<ArchUnit-equivalent rules>>
CI -> CI : pytest tests/unit
CI -> CI : pytest tests/integration    <<services from compose>>
CI -> CI : build Dockerfile.management_api / .redirection_engine / .click_consumer
note right of CI
  AC P1-04/3 and /4: any failing step fails
  the pipeline. No deploy, no registry push,
  no GitOps in Phase 1.
end note
@enduml
```

<!-- PHASE: Phase 1 MVP END -->

---
*Generated by Architect Agent — scope: phase_1_mvp*
