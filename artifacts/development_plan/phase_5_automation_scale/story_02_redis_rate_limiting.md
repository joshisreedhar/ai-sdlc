# P5-02: Redis-Based API Rate Limiting

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** platform operator,
- **I want to** enforce per-API-key rate limits on the public REST API,
- **So that** automated integrations cannot degrade redirection latency or exhaust shared infrastructure for other tenants.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Opening a public API (P5-01) without limits creates a real risk of abusive or buggy client scripts overwhelming the API & Management Service, which shares infrastructure with the latency-sensitive Redirection Engine.
- The architecture guidance already designates Redis as the component that "Handles API Rate Limiting," so this story wires that responsibility into the new public API rather than introducing new infrastructure.
- The exact limiter algorithm (fixed window, sliding window, or token bucket) and default thresholds per plan tier are negotiable with the team; the non-negotiable requirement is that limits are enforced consistently and communicated to clients via standard headers.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done". Use BDD (Behavior-Driven Development) Given/When/Then format when possible.*

**Scenario 1: Requests within limit succeed**
- **Given** an API key with a configured limit of 100 requests/minute
- **When** the client makes 100 requests within a rolling 60-second window
- **Then** all requests are processed normally and each response includes `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers

**Scenario 2: Requests exceeding limit are throttled**
- **Given** an API key that has already used its full quota for the current window
- **When** an additional request is made
- **Then** the API responds with `429 Too Many Requests`, a `Retry-After` header, and the request is not forwarded to downstream business logic

**Scenario 3: Limiter fails safe if Redis is unavailable**
- **Given** the Redis rate-limiting store is temporarily unreachable
- **When** a request is made to the public API
- **Then** the system applies a documented fallback policy (either fail-open with logging and alerting, or fail-closed with a `503`), per the agreed operational runbook, rather than crashing the request handler

**Scenario 4: Limits are isolated per API key**
- **Given** two different API keys belonging to two different accounts
- **When** one key's traffic exceeds its limit
- **Then** the other key's remaining quota and traffic are completely unaffected

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Redis-backed limiter middleware on the `/api/v1/*` namespace, per-key counters/keys with TTL-based expiry, standard rate-limit response headers, configurable limit per key/plan.
- **Out of Scope:** Billing/plan-tier management UI, IP-based (non-key) rate limiting for anonymous traffic (already covered by Phase 3 bot/IP filtering middleware), distributed limiter tuning for multi-region Redis clusters.
- **Upstream Dependencies:** Requires P5-01 (API keys) to exist so limiter keys can be scoped per API key; otherwise independently testable and deployable behind a feature flag.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — infrastructure/middleware feature, no end-user UI.
- **Technical Context:** Implement as FastAPI middleware using the existing Redis cluster described in the architecture guidance ("Cache & Message Broker: Redis... Handles API Rate Limiting"). Use atomic Redis operations (e.g., `INCR` + `EXPIRE`, or a Lua script for a sliding-window log) keyed as `ratelimit:{api_key_id}:{window}` to avoid race conditions under concurrent requests. Reuse the same Redis connection pool as the redirect cache/Celery broker rather than provisioning a separate instance, consistent with the "Cloud-Native Foundation" work from Phase 2.
