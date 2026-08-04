# PHASE3-04: Geo-Targeting & Device-Based Routing Rules

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** marketer running a multi-region or multi-platform campaign,
- **I want to** configure a single short link to redirect visitors to different destination URLs based on their country/region and device type,
- **So that** I can serve localized landing pages or platform-specific experiences (e.g., App Store vs. Play Store) without creating and distributing separate links.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Requirements explicitly call for "geo-targeting, device-based redirects" under Routing Rules.
- A link owner defines an ordered set of rules (e.g., "if country = FR, go to X," "if device = mobile-iOS, go to Y"), plus a default/fallback destination when no rule matches.
- The exact rule precedence when both a geo rule and a device rule could apply to the same visitor is open for team negotiation during implementation (e.g., most-specific-match-wins vs. explicit owner-defined ordering), but the behavior must be deterministic and documented.
- GeoIP resolution and User-Agent parsing already exist in the Phase 2 async Analytics Pipeline for post-hoc analytics; this story requires a synchronous, low-latency equivalent (or a fast lookup path) usable at redirect time, since routing decisions cannot wait for the async pipeline.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done". Use BDD (Behavior-Driven Development) Given/When/Then format when possible.*

**Scenario 1: Visitor matches a configured geo rule**
- **Given** a link has a routing rule mapping country "DE" to destination URL B, with a default destination URL A
- **When** a visitor whose IP resolves to Germany requests the link
- **Then** they are redirected to destination URL B

**Scenario 2: Visitor matches a configured device rule**
- **Given** a link has a routing rule mapping device type "mobile-Android" to a Play Store URL, with a default destination
- **When** a visitor on an Android mobile browser requests the link
- **Then** they are redirected to the Play Store URL

**Scenario 3: Visitor matches no configured rule**
- **Given** a link has geo/device rules configured but the visitor's country and device don't match any rule
- **When** they request the link
- **Then** they are redirected to the link's default destination URL

**Scenario 4: Visitor matches both a geo and a device rule**
- **Given** a link has both a matching geo rule and a matching device rule for the same request
- **When** the routing engine evaluates the rules
- **Then** the documented precedence order is applied deterministically and the same visitor profile always yields the same destination

**Scenario 5: GeoIP or device lookup fails or is inconclusive**
- **Given** the visitor's IP cannot be resolved to a location, or the User-Agent cannot be parsed
- **When** the link has geo/device rules configured
- **Then** the system falls back to the default destination rather than failing the request

**Scenario 6: Owner configures/edits routing rules**
- **Given** a link owner creates, edits, or removes a geo/device routing rule via the Management API
- **When** the change is saved
- **Then** subsequent redirect requests reflect the updated rule set (within the documented cache propagation window)

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Routing Rules data model (country/region conditions, device-type conditions, ordered priority, default destination) in PostgreSQL; synchronous GeoIP and User-Agent based lookup usable within the redirect request path; rule evaluation logic in the Redirection Engine; Management API endpoints to create/update/delete rules per link.
- **Out of Scope:** Password protection (Story 1), expiration/access restrictions (Story 2), IP/bot filtering middleware (Story 3) — though this story's rule evaluation runs after those checks pass; A/B/split-testing style random routing (not requested); conversion pixel/retargeting logic (Phase 4).
- **Upstream Dependencies:** None required to build or ship independently, though in production request flow this story's rule evaluation executes after Story 3's bot/IP filtering has passed the request through.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** None provided; rule configuration UI/API contract to be defined by the team, but should mirror the existing link-editing API shape.
- **Technical Context:**
  - Directly implements the requirements' "geo-targeting, device-based redirects" and architecture guidance's directive that the Redirection Engine must "Evaluate Routing Rules (Geo-targeting, Device-based, Expiration, Password-gate)."
  - Routing Rules are stored in PostgreSQL per architecture guidance Section 4 ("Stores Users, Links..., Routing Rules"); consider caching a link's compiled rule set alongside its `short_hash -> long_url` Redis entry to avoid a DB round-trip per redirect.
  - Needs a fast, synchronous GeoIP lookup (e.g., embedded MaxMind GeoLite2 database queried in-process) distinct from the async pipeline's GeoIP resolution used for analytics, since redirect decisions must not block on the Celery/message-broker pipeline described in architecture guidance Section 2.3.
  - Device/browser detection at redirect time can reuse a lightweight User-Agent parsing library synchronously in the Redirection Engine; this is separate from (but should use consistent categorization logic to) the analytics pipeline's User-Agent parsing.
  - Per architecture guidance, the redirect response must still be issued without blocking on analytics; the click event (including which rule matched, if any) is published to the message broker for the async pipeline exactly as in the base redirect flow.
