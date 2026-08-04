# PH2-02: Asynchronous Click Event Ingestion & Enrichment Pipeline

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** link owner,
- **I want to** have every redirect click captured and enriched with device, browser, OS, and geographic location without slowing down the redirect itself,
- **So that** I can later see accurate, detailed traffic data for my links while my visitors still experience an instant redirect.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Per the architecture guidance, the Redirection Engine must never block the redirect response to process analytics — it only publishes a lightweight click event to the message broker (Redis/RabbitMQ) and returns the 301/302 immediately.
- This story covers the consumer side: Celery workers that pick up published click events, parse the User-Agent string (device/browser/OS), resolve the visitor's IP to a geographic location (GeoIP), and persist the enriched record to the analytics data store.
- The exact event payload schema, GeoIP library/dataset (e.g., MaxMind GeoLite2), and User-Agent parser (e.g., `user-agents` or `ua-parser`) are open for the team to select during implementation.
- This story assumes the Redirection Engine's "publish click event" side already exists or is trivial to add as part of this story if not covered elsewhere in Phase 1; if the publish side needs new work, include it here since the pipeline isn't testable end-to-end without it.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: A redirect produces an enriched analytics record**
- **Given** a valid short link exists and the async pipeline is running,
- **When** a visitor requests the short link (triggering a redirect),
- **Then** within a bounded delay (e.g., a few seconds) a corresponding row appears in the analytics store containing the link ID, timestamp, parsed device type, browser, OS, resolved country/city (best-effort), and referrer header if present.

**Scenario 2: Redirect latency is unaffected by analytics processing**
- **Given** the async pipeline is enabled,
- **When** the redirect endpoint's response time is measured under load,
- **Then** the p95 redirect latency shows no statistically meaningful increase compared to the same endpoint with the pipeline disabled, confirming the publish step is non-blocking (fire-and-forget or async enqueue).

**Scenario 3: Malformed or unresolvable data degrades gracefully**
- **Given** a click event with a missing/unparseable User-Agent string or an IP that cannot be geo-resolved (e.g., private/internal IP),
- **When** the Celery worker processes that event,
- **Then** the record is still persisted with the unresolvable fields set to a clear "unknown" value, and the failure is logged — the event is never silently dropped nor does it crash the worker.

**Scenario 4: Broker outage does not lose events indefinitely**
- **Given** the message broker or a Celery worker is temporarily unavailable,
- **When** it recovers,
- **Then** queued click events are processed once the worker reconnects (standard Celery/broker durability), and no click events are lost due to the outage.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Click event schema and publish call from the Redirection Engine (if not already present); Celery task definition for consuming events; User-Agent parsing; GeoIP resolution; write path into the analytics data store (schema/migration for the click events table).
- **Out of Scope:** Analytics query/reporting endpoints (covered in Story PH2-04); conversion/pixel tracking (Phase 4); bot/IP filtering logic (Phase 3 security controls) — this pipeline records raw clicks as-is.
- **Upstream Dependencies:** Redis (or chosen broker) is available as a Celery broker; Story PH2-01's Kubernetes deployment provides the runtime for Celery workers (this story can be developed and tested locally/docker-compose first and does not strictly require PH2-01 to be complete).

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — backend/data pipeline story.
- **Technical Context:** Per `architecture_guidance.md` sections 2.2–2.3, the Redirection Engine publishes to the message broker non-blockingly; Celery workers ingest, parse User-Agent (device/browser/OS), resolve IP-to-location via GeoIP, and write to the Analytics Data Store (PostgreSQL, partitioned, per section 4 — ClickHouse is a future option if volume requires it, not required for this story). The click event should carry at minimum: link ID/short code, timestamp, raw User-Agent, client IP, and referrer header, captured synchronously in the Redirection Engine but processed asynchronously here.
