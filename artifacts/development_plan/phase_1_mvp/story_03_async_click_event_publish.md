# P1-03: Non-Blocking Click Event Publish

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** future analytics pipeline (and, by extension, the business stakeholders who will rely on click data),
- **I want to** have every redirect emit a click event to a message broker the moment it happens,
- **So that** click activity is never lost and can be processed for analytics later, without slowing down the redirect experience for end users.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- The product's core analytics promise (click metrics, device/referrer data, conversions) depends on capturing every click event from day one, even though the full processing pipeline (Celery workers, GeoIP, User-Agent parsing, analytics store) is not built until Phase 2.
- This story exists to de-risk that later work: by wiring up the publish side and a minimal stub consumer now, Phase 2 can focus purely on building the consumer/processing logic against an already-proven event contract.
- The specific message broker (Redis Streams/Pub-Sub vs. RabbitMQ) and exact event schema are open for the team to decide, but the event must carry enough raw data (short code, timestamp, and available request metadata such as IP and User-Agent) for Phase 2 to build device/geo/referrer analytics without re-instrumenting the Redirection Engine.
- The "stub consumer" here is intentionally minimal — e.g., a worker process that consumes and logs/discards events — just enough to prove the publish path works end-to-end. Real Celery-based processing arrives in Phase 2.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Click event published on successful redirect**
- **Given** a client requests a valid short URL and is redirected (per P1-02),
- **When** the redirect response is issued,
- **Then** a click event containing at least the short code and a timestamp is published to the message broker.

**Scenario 2: Publish failure does not break the redirect**
- **Given** the message broker is temporarily unavailable or the publish call fails,
- **When** a client requests a valid short URL,
- **Then** the redirect still succeeds and is returned to the client (the failure is logged, not surfaced to the user).

**Scenario 3: Redirect response is not delayed by publishing**
- **Given** a valid short code is requested,
- **When** the click event is published,
- **Then** the publish operation is fire-and-forget (non-blocking) relative to the HTTP response — the client receives the redirect without waiting for broker acknowledgment.

**Scenario 4: Stub consumer proves the event is deliverable**
- **Given** the stub consumer process is running and subscribed to the broker,
- **When** a click event is published by the Redirection Engine,
- **Then** the stub consumer receives and logs the event, demonstrating an unbroken publish-to-consume path.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Defining a minimal click-event schema; non-blocking publish call from the Redirection Engine on every successful redirect; a minimal stub consumer process that reads events off the broker and logs them (no parsing, enrichment, or persistence of analytics data).
- **Out of Scope:** User-Agent parsing, GeoIP resolution, writing to an analytics data store, aggregated metrics/dashboards, Celery worker infrastructure. These are the explicit focus of Phase 2: Cloud-Native Foundation & Async Analytics.
- **Upstream Dependencies:** Depends on the Redirection Engine (P1-02) existing as the trigger point for publishing; can be developed in parallel once the redirect endpoint's contract (where a successful redirect occurs) is agreed, and merged in as a thin addition to that endpoint.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A (backend/infrastructure story, no UI).
- **Technical Context:**
  - Per `markdowns/architecture_guidance.md` section 2.2, the Redirection Engine must "Publish click event to Message Broker (non-blocking)" and must not block the redirect response to process analytics.
  - Per section 4, Redis is designated to act as the message broker (in addition to caching and rate limiting) — favor Redis Streams or Pub/Sub to avoid introducing a second infrastructure dependency in this phase; RabbitMQ remains an option per section 2.3 if the team prefers to align directly with the Celery-based pipeline planned for Phase 2.
  - Suggested minimal event payload: `{"short_code": str, "timestamp": ISO8601, "ip": Optional[str], "user_agent": Optional[str], "referrer": Optional[str]}` — richer than what Phase 1 needs, but avoids a breaking schema change when Phase 2 builds the real consumer.
  - The stub consumer can be a small standalone script/container (not full Celery) whose only job is to prove messages flow; it will be replaced/extended by real Celery workers in Phase 2.
