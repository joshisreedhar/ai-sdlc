# PHASE6-04: Distributed Tracing & Centralized Structured Logging

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** developer or on-call engineer debugging a production issue,
- **I want to** trace a single request end-to-end across the API, Redirection Engine, and Celery workers, and search centralized structured logs correlated to that trace,
- **So that** I can identify the root cause of latency bottlenecks or failures quickly, minimizing downtime impact on end users.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- The architecture guidance calls for OpenTelemetry-based distributed tracing (to avoid vendor lock-in) and centralized structured JSON logging to `stdout`/`stderr`, collected by Fluentd/Logstash — neither exists yet in the platform.
- Today, a request that flows from the redirect hop into the async analytics pipeline (Celery) cannot be followed end-to-end; diagnosing issues that span the sync/async boundary requires manually correlating disjoint logs.
- The specific backend for trace storage/visualization (e.g., Jaeger, Tempo, or a hosted OTel-compatible backend) and the log aggregation backend (e.g., ELK, Loki) are negotiable implementation choices; this story fixes the requirement that traces and logs are emitted in a vendor-neutral, correlated, centrally queryable form.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: End-to-end trace across sync and async boundary**
- **Given** a client makes a request to a short link,
- **When** the Redirection Engine handles the redirect and publishes a click event to the message broker, which is subsequently processed by a Celery worker,
- **Then** a single distributed trace (with one trace ID) spans the Redirection Engine's request handling and the Celery task that processes the resulting click event, viewable as connected spans in the tracing backend.

**Scenario 2: Structured JSON logs correlated to traces**
- **Given** any service (API, Redirection Engine, Celery worker) handling a request or task,
- **When** it emits log lines to `stdout`/`stderr`,
- **Then** each log line is a structured JSON object containing at minimum a timestamp, log level, service name, and the active trace ID/span ID (when one exists), enabling an engineer to pivot directly from a trace to its corresponding logs.

**Scenario 3: Logs are centrally collected and searchable**
- **Given** structured JSON logs are being emitted by all services across Dev, Staging, and Prod,
- **When** a log collection agent (Fluentd/Logstash) is deployed to each environment,
- **Then** logs from all pods are shipped to a centralized log store and are searchable/filterable by service, environment, log level, and trace ID within a few seconds of emission.

**Scenario 4: Latency bottleneck is identifiable from a trace**
- **Given** a redirect request that experiences elevated latency (e.g., a PostgreSQL fallback due to a cache miss),
- **When** an engineer inspects the corresponding trace,
- **Then** the trace shows distinct spans for the Redis lookup, the PostgreSQL fallback query, and the routing rule evaluation, with each span's duration visible, making the source of added latency immediately apparent.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** OpenTelemetry SDK instrumentation for FastAPI (API + Redirection Engine) and Celery, including context propagation across the message broker boundary; a shared structured JSON logging library/formatter used by all services; deployment of a log-shipping agent (Fluentd/Logstash) per environment; a minimal tracing backend deployment for viewing traces.
- **Out of Scope:** Long-term log/trace retention and cost optimization policy, log-based alerting rules, full APM-vendor evaluation/migration (a specific backend is chosen pragmatically for this story and can be revisited later since OTel keeps the instrumentation itself vendor-neutral).
- **Upstream Dependencies:** Requires the Kubernetes deployments from Phase 2 and benefits from, but does not strictly require, the metrics work in Story 03. Independent of Link-in-Bio and GitOps stories.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — this is a backend instrumentation and tooling story with no end-user UI.
- **Technical Context:**
  - Per architecture guidance section 3.3: "Integrate OpenTelemetry (OTel) into FastAPI and Celery to trace request paths and latency bottlenecks without vendor lock-in," and "Output centralized, structured JSON logging to `stdout`/`stderr` (collected by Fluentd/Logstash)."
  - Use `opentelemetry-instrumentation-fastapi` and `opentelemetry-instrumentation-celery` for auto-instrumentation, with manual span creation around the Redis cache-first lookup and PostgreSQL fallback in the Redirection Engine per architecture section 2.2.
  - Trace context must be propagated through the message broker (Redis/RabbitMQ) from the point the Redirection Engine publishes the click event to the point the Celery worker consumes it, so the async analytics pipeline (section 2.3) appears as a continuation of the same trace rather than a disconnected one.
  - Standardize on a single JSON log formatter (e.g., `python-json-logger` or `structlog`) applied consistently across the API, Redirection Engine, and Celery workers before wiring up log shipping, to avoid inconsistent schemas reaching the central store.
