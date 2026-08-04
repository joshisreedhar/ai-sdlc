# P1-02: Redirection Engine with Cache-First Lookup

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** visitor who clicks or navigates to a short link,
- **I want to** be instantly redirected to the original destination URL,
- **So that** the short link works exactly as expected, with minimal added latency.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- This is the second half of the core product loop (the first half being link creation, P1-01). Together they form the MVP's complete, demonstrable user journey.
- Architecture guidance mandates a cache-first lookup strategy: Redis first, PostgreSQL as fallback (and cache-fill) on a miss. The exact cache eviction policy, TTL, and warm-up strategy are left to the team to decide during implementation.
- Routing rules (geo-targeting, device-based redirects, password gates, expiration) are explicitly deferred to Phase 3; this story only needs a direct, unconditional redirect.
- Performance is a first-class concern here: this endpoint must remain fast even as the system scales, since it is the highest-traffic path in the whole product.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Redirect via cache hit**
- **Given** a short code's mapping already exists in Redis,
- **When** a client requests the short URL,
- **Then** the service reads the destination from Redis and issues an HTTP redirect (301/302) to the long URL without querying PostgreSQL.

**Scenario 2: Redirect via cache miss with fallback**
- **Given** a short code's mapping exists in PostgreSQL but is not present in Redis,
- **When** a client requests the short URL,
- **Then** the service looks up the mapping in PostgreSQL, issues the HTTP redirect to the long URL, and populates Redis with the mapping for subsequent requests.

**Scenario 3: Unknown short code**
- **Given** a short code that does not exist in either Redis or PostgreSQL,
- **When** a client requests that short URL,
- **Then** the service responds with a 404 Not Found and does not attempt a redirect.

**Scenario 4: Redirect latency is not blocked by side effects**
- **Given** a valid short code is requested,
- **When** the redirect response is generated,
- **Then** the HTTP redirect is returned to the client without waiting on any downstream analytics/event-publishing work (verified via P1-03's non-blocking publish).

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** GET endpoint that resolves a short code, Redis cache-first lookup, PostgreSQL fallback lookup, cache-fill on miss, HTTP redirect response, 404 handling for unknown codes.
- **Out of Scope:** Routing rules (geo, device, bot filtering), password-protected links, link expiration, conversion-tracking intermediary pages. These are addressed in Phases 3 and 4.
- **Upstream Dependencies:** Requires the `links` table/schema and persistence logic established in P1-01 (a link must exist in PostgreSQL to be resolvable). Can otherwise be developed in parallel with P1-01 against a shared schema contract, and tested independently using seeded data.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A (API-only story, no UI in this phase).
- **Technical Context:**
  - Per `markdowns/architecture_guidance.md` section 2.2, this is the **Redirection Engine**, a FastAPI service optimized for low latency, logically/deployably separate from the API & Management Service.
  - Lookup order: Redis (`short_hash -> long_url` cache, section 4) first; on miss, fall back to PostgreSQL and repopulate Redis.
  - Suggested endpoint: `GET /{short_code}` returning an HTTP 301/302 redirect with the `Location` header set to the long URL.
  - Per section 2.2's explicit Agent Instruction: "Do not block the redirect response to process analytics" — the click-event publish (P1-03) must be fire-and-forget relative to this endpoint.
  - Per section 5, redirection read logic must be strictly separated from write/analytics logic — avoid embedding analytics processing or DB writes for click tracking directly in this request path.
