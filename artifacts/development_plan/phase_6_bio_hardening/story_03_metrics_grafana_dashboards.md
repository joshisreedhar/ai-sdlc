# PHASE6-03: Production Metrics & Grafana Dashboards

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As an** on-call/site reliability engineer,
- **I want to** view real-time metrics for the API, Redirection Engine, and Celery workers on Grafana dashboards backed by Prometheus,
- **So that** I can detect performance degradation or failures quickly and protect the redirection service's low-latency SLA for end users.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- The architecture guidance requires every service to expose a `/metrics` endpoint for Prometheus scraping, with Grafana used for visualization — this has not yet been built in any prior phase.
- Without production metrics, the team is flying blind on the very latency and throughput guarantees the Redirection Engine was specifically architected to protect (async analytics, cache-first lookups).
- The exact set of dashboard panels and alert thresholds is negotiable and expected to evolve as real traffic patterns are observed; this story fixes the foundation (instrumentation + baseline dashboards), not the final tuned alerting policy.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Services expose scrapeable metrics**
- **Given** the API, Redirection Engine, and Celery worker deployments running in any environment,
- **When** Prometheus scrapes each service's `/metrics` endpoint,
- **Then** it successfully collects standard request metrics (request count, latency histograms, error rates) for the API and Redirection Engine, and task-level metrics (queue depth, task duration, success/failure counts) for Celery workers.

**Scenario 2: Redirection latency dashboard**
- **Given** Prometheus is collecting Redirection Engine metrics,
- **When** an engineer opens the Grafana "Redirection Performance" dashboard,
- **Then** it displays p50/p95/p99 redirect latency, requests-per-second, cache hit/miss ratio (Redis vs. PostgreSQL fallback), and error rate, each filterable by environment (Dev/Staging/Prod).

**Scenario 3: Analytics pipeline health dashboard**
- **Given** Prometheus is collecting Celery worker metrics,
- **When** an engineer opens the Grafana "Analytics Pipeline Health" dashboard,
- **Then** it displays click-event queue depth/backlog, task processing latency, and task failure rate, so a backlog in async analytics processing is visible before it causes data loss or delay.

**Scenario 4: Dashboards persisted as code**
- **Given** a dashboard has been created or modified in Grafana,
- **When** the change is finalized,
- **Then** the dashboard JSON definition is exported and stored in version control (provisioned via Grafana's dashboard-as-code mechanism) so dashboards are reproducible across environments and survive a Grafana instance rebuild.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Instrumenting API, Redirection Engine, and Celery workers with a Prometheus client library; deploying/configuring Prometheus to scrape all services across environments; standing up Grafana with two baseline dashboards (Redirection Performance, Analytics Pipeline Health) provisioned as code.
- **Out of Scope:** Alertmanager/PagerDuty integration and formal on-call alert routing (can follow once baseline metrics validate expected thresholds), business/product KPI dashboards (click counts, conversions — those are product analytics, not operability metrics), long-term metrics retention/cold storage strategy.
- **Upstream Dependencies:** Requires the Kubernetes deployments from Phase 2. Independent of Link-in-Bio and GitOps stories; can ship on its own. Complements Story 04 (tracing/logging) but does not require it — metrics can land first.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — use standard Grafana dashboard layouts; no custom visual design required.
- **Technical Context:**
  - Per architecture guidance section 3.3: "Expose `/metrics` endpoints for Prometheus scraping. Use Grafana for visualization."
  - FastAPI services: use `prometheus-fastapi-instrumentator` (or equivalent) to auto-expose request count/latency/error metrics; Celery: use `celery-prometheus-exporter` or custom signal-based instrumentation for task metrics.
  - Deploy Prometheus and Grafana via the existing Helm/Kustomize-managed Kubernetes environments (Phase 2), one Prometheus/Grafana pair per environment or a shared Prometheus with environment labels — decision to be finalized with the platform team.
  - Redis cache hit/miss ratio can be derived either from Redis's own exporter (`redis_exporter`) or from custom counters emitted by the Redirection Engine around its cache-first lookup logic.
