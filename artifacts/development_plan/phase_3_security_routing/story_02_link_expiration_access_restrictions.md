# PHASE3-02: Link Expiration & Access Restrictions

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** link owner running a time-boxed or limited-audience campaign,
- **I want to** set an expiration date and/or access limits on a short link,
- **So that** the link automatically stops working once it's no longer relevant or has been used as intended, without me having to manually delete or edit it.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Requirements call out "expiration dates, and access restrictions" as part of Security Controls alongside password protection.
- Two related but distinct constraints are in scope: (a) time-based expiration (link stops working after a specific date/time, or is only active within a scheduled window) and (b) usage-based access restriction (e.g., a maximum number of total clicks/redemptions).
- The exact set of restriction types (max clicks vs. max unique visitors vs. scheduled windows) is negotiable; the non-negotiable part is that an expired/restricted link must fail closed (never redirect) and communicate a clear reason to the visitor.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done". Use BDD (Behavior-Driven Development) Given/When/Then format when possible.*

**Scenario 1: Link accessed after its expiration date**
- **Given** a link has an expiration timestamp that is in the past
- **When** a visitor requests the short link
- **Then** the Redirection Engine returns an "expired link" page (HTTP 410 Gone or equivalent) instead of redirecting, and no destination URL is disclosed

**Scenario 2: Link accessed before its scheduled activation window**
- **Given** a link has a "not valid until" start timestamp that is in the future
- **When** a visitor requests the short link before that time
- **Then** the visitor sees a "not yet active" page and is not redirected

**Scenario 3: Link within its valid time window**
- **Given** a link has both a start and expiration timestamp, and the current time falls between them
- **When** a visitor requests the short link
- **Then** the redirect proceeds normally (subject to any other active security/routing rules)

**Scenario 4: Link reaches its maximum access count**
- **Given** a link is configured with a maximum number of allowed successful redirects (e.g., 100)
- **When** the configured maximum has already been reached
- **Then** subsequent requests receive a "link no longer available" page instead of a redirect, and the count is not incremented further

**Scenario 5: Owner updates or removes expiration/access settings**
- **Given** a link owner edits a link's expiration date or access limit via the Management API
- **When** the update is saved
- **Then** the new constraint is enforced on the very next redirect request (accounting for expected cache propagation delay documented by the team)

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Expiration timestamp and optional activation-window start timestamp on link metadata; maximum-access-count restriction with an atomic counter; enforcement logic in the Redirection Engine; distinct, clear fallback pages for "expired," "not yet active," and "limit reached" states; Management API support for setting/clearing these fields.
- **Out of Scope:** Password protection (Story 1), IP/bot filtering (Story 3), geo/device routing (Story 4), analytics reporting on why a link stopped serving traffic (can be a future enhancement).
- **Upstream Dependencies:** None — independent of Stories 1, 3, and 4; can be built, tested, and deployed on its own against the existing link schema.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** None provided; fallback pages can be simple static/templated responses distinguishing expired vs. not-yet-active vs. limit-reached.
- **Technical Context:**
  - Extends the Link Metadata table in PostgreSQL (per architecture guidance Section 4) with `expires_at`, `active_from`, and `max_access_count` columns, plus an access counter.
  - The access counter should be incremented atomically (e.g., via a Redis `INCR` on the cached link record or a PostgreSQL atomic update) to avoid race conditions under concurrent traffic, consistent with the cache-first Redis lookup pattern described for the Redirection Engine.
  - Expiration/window checks must happen in the Redirection Engine's routing-rule evaluation step, after the Redis cache lookup but before the redirect response is issued, per the architecture's separation of read logic from write/side-effect logic.
  - Click-event publishing to the async analytics pipeline should still fire (or fire a distinct "blocked" event) so expired/restricted attempts remain visible in reporting; must not block the response.
