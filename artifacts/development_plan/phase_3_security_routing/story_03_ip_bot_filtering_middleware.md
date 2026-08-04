# PHASE3-03: IP & Bot Filtering Middleware

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** link owner and platform operator,
- **I want to** automatically block known bots, scrapers, and specific IP addresses/ranges from following my short links,
- **So that** my destination site is protected from abusive automated traffic and my analytics reflect genuine human engagement.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Requirements list "traffic filters to block unwanted visitors or bots" under Routing Rules; architecture guidance's Security Constraint 1 mandates implementing IP and bot filtering middleware.
- This is platform-wide middleware (applies to all links) plus optional per-link IP allow/deny lists, distinct from the per-link password/expiration gates in Stories 1-2.
- The specific bot-detection technique (User-Agent signature matching, known-bot IP ranges, request-rate heuristics, third-party bot-detection service) is negotiable and can start simple (signature + IP list based) with room to evolve; the non-negotiable requirement is that filtering happens in middleware ahead of routing-rule evaluation and cache lookup where feasible, and never adds unacceptable latency to legitimate requests.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done". Use BDD (Behavior-Driven Development) Given/When/Then format when possible.*

**Scenario 1: Request from a known bot User-Agent**
- **Given** the platform maintains a list of known bot/crawler User-Agent signatures
- **When** a request's User-Agent matches a blocked signature
- **Then** the middleware rejects the request (e.g., HTTP 403) before any link lookup or redirect logic executes, and the event is logged as "blocked: bot"

**Scenario 2: Request from a platform-level denied IP or CIDR range**
- **Given** an IP address or CIDR range is on the platform-wide deny list
- **When** a request originates from that IP
- **Then** the middleware rejects the request before routing-rule evaluation, and the rejection is logged with the matching rule

**Scenario 3: Request against a link with a per-link IP allow list**
- **Given** a specific link has been configured to only permit a defined set of IPs/CIDR ranges
- **When** a visitor from outside that allow list requests the link
- **Then** the visitor receives a "not permitted" response and is not redirected

**Scenario 4: Legitimate human traffic is unaffected**
- **Given** a request has no matching bot signature and no matching IP deny rule
- **When** it reaches the Redirection Engine
- **Then** it proceeds through normal routing-rule evaluation and redirect logic with no measurable added latency beyond the filtering check itself

**Scenario 5: Filtering decisions are observable**
- **Given** the bot/IP filtering middleware has processed a batch of requests over a time window
- **When** an operator reviews platform logs/metrics
- **Then** blocked vs. allowed request counts and block reasons are visible (structured JSON logs and/or a Prometheus counter), enabling tuning of filter rules

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Platform-wide bot signature and IP deny-list middleware in the Redirection Engine; per-link IP allow/deny list configuration via the Management API; structured logging/metrics for filtering decisions; a maintainable, updatable rule source (config-driven or DB-backed list).
- **Out of Scope:** Password protection (Story 1), expiration/access restrictions (Story 2), geo-targeting/device-based destination routing (Story 4), advanced ML-based bot detection or third-party bot-detection service integration (future enhancement candidate).
- **Upstream Dependencies:** None — this is foundational middleware that other Phase 3 stories' redirect flows sit behind, but it can be developed, tested, and deployed independently using synthetic bot/IP test traffic.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** None provided; this is backend/infrastructure-facing with no end-user UI beyond the rejection response page.
- **Technical Context:**
  - Directly implements Architecture Guidance Security Constraint 1: "Implement IP and bot filtering middleware."
  - Should be implemented as FastAPI middleware in the Redirection Engine, executing before the Redis cache lookup and routing-rule evaluation steps, consistent with the architecture's directive to strictly separate read logic and keep the redirect path low-latency.
  - Platform-wide deny lists and bot signatures can be cached in Redis for fast lookup (mirroring the existing `short_hash -> long_url` caching pattern) to avoid a PostgreSQL round-trip per request.
  - Per-link IP allow/deny lists extend the Link Metadata / Routing Rules tables in PostgreSQL described in architecture guidance Section 4.
  - Blocked-request logging should follow the platform's structured JSON logging convention (stdout/stderr, collected by Fluentd/Logstash) and expose a `/metrics` counter for Prometheus, per the Observability & Telemetry guidance.
