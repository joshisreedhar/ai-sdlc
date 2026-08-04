# PH2-03: Baseline Metrics & Distributed Tracing for the Async Path

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** platform operator/on-call engineer,
- **I want to** see Prometheus metrics and OpenTelemetry traces spanning the redirect → publish → Celery consume → persist path,
- **So that** I can detect latency regressions, queue backlogs, or failures in the new asynchronous analytics pipeline before they affect users, and pinpoint which service is responsible.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Phase 2 introduces real distributed complexity for the first time (multiple services, an async queue, K8s scheduling). Without baseline observability, operators are flying blind on the new failure modes this phase introduces (queue backlog, worker crash loops, GeoIP lookup latency, etc.).
- The architecture guidance calls for `/metrics` endpoints scraped by Prometheus and OpenTelemetry tracing across FastAPI and Celery. The specific metric names, trace attribute conventions, and whether Grafana dashboards are hand-built or auto-provisioned are open for the team to decide.
- This story is about establishing the baseline instrumentation and making it visible, not about building a full alerting/SLO program — that can be layered on in later phases as traffic and operational maturity grow.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Metrics endpoints are scrapeable**
- **Given** the API, Redirection Engine, and Celery workers are running in Kubernetes,
- **When** Prometheus scrapes their respective `/metrics` endpoints (or Celery's exporter sidecar),
- **Then** each target returns HTTP 200 with metrics including at minimum request count, request latency histogram, and error count for the two FastAPI services, and task count/duration/failure count for Celery.

**Scenario 2: A trace spans the full async path**
- **Given** OpenTelemetry instrumentation is enabled on the Redirection Engine and Celery workers,
- **When** a single redirect request triggers a click event that flows through the broker into a Celery task,
- **Then** a single trace (or explicitly linked parent/child spans) is visible in the tracing backend showing the redirect span, the publish span, and the Celery consume/process span with propagated context (e.g., via a trace ID carried in the event payload).

**Scenario 3: Dashboard reflects real traffic**
- **Given** Grafana is connected to the Prometheus data source,
- **When** an operator opens the provisioned dashboard for this phase,
- **Then** it displays live panels for redirect request rate/latency, Celery queue depth (or task throughput), and error rates, updating as traffic is generated.

**Scenario 4: A failure is observable, not silent**
- **Given** a Celery task fails (e.g., simulated by forcing a GeoIP lookup exception),
- **When** the failure occurs,
- **Then** the Celery failure-count metric increments and the corresponding trace span is marked as an error/exception, so the failure is visible in both metrics and tracing without needing to grep logs.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** `/metrics` instrumentation (e.g., `prometheus-fastapi-instrumentator` or equivalent) on API and Redirection Engine; a Celery Prometheus exporter; OpenTelemetry SDK setup and auto-instrumentation for FastAPI and Celery; trace context propagation across the broker boundary; one baseline Grafana dashboard; structured JSON logging to stdout per the architecture guidance.
- **Out of Scope:** Alerting rules/on-call paging (e.g., Alertmanager configuration); SLO definitions; log aggregation backend setup (Fluentd/Logstash infrastructure itself — only the JSON stdout format is this story's responsibility); tracing/metrics for later-phase features (routing rules, conversion pixels) that don't exist yet.
- **Upstream Dependencies:** Story PH2-01 (Kubernetes deployment) provides the environment where Prometheus scraping and OTel collector deployment are exercised; Story PH2-02's async pipeline provides the multi-hop path this story traces. Metrics/tracing code can be developed in parallel with both, using local docker-compose, and wired into the cluster once available.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — a starter Grafana dashboard JSON will be checked in; no custom UI design required.
- **Technical Context:** Per `architecture_guidance.md` section 3.3, expose `/metrics` for Prometheus and integrate OpenTelemetry into FastAPI and Celery for distributed tracing without vendor lock-in (use the OTel Collector as the export target, backend-agnostic). Structured JSON logs go to stdout/stderr for later collection by Fluentd/Logstash — this story only needs to emit that format, not stand up the collection stack.
