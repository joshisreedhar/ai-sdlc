# PHASE3-01: Password-Protected Links via Intermediary Auth Page

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** link owner running a gated or sensitive campaign,
- **I want to** require a password before visitors reach my destination URL,
- **So that** I can share links privately (embargoed content, internal resources, paid content) without exposing the destination to anyone who obtains the short link.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Today (post Phase 1-2), any visitor with a short link is redirected straight to the destination. Enterprise and marketing use cases identified in requirements need a gate.
- Architecture guidance's Security Constraint 2 is explicit: the Redirection Engine must never redirect a password-protected link directly to the destination — it must always serve an intermediary auth page first, and only proceed after the correct password is supplied.
- The "how" of session/token issuance after a correct password (cookie vs. signed query token vs. server-side session) is open for technical negotiation, but the destination URL must never be observable (in HTML, headers, or client-side JS) prior to successful authentication.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done". Use BDD (Behavior-Driven Development) Given/When/Then format when possible.*

**Scenario 1: Visiting a password-protected link with no credentials**
- **Given** a short link has password protection enabled
- **When** a visitor requests the short link with no prior valid access token
- **Then** the Redirection Engine responds with an intermediary auth page (HTTP 200) prompting for a password, and the response contains no reference to the destination URL

**Scenario 2: Submitting the correct password**
- **Given** a visitor is on the intermediary auth page for a password-protected link
- **When** they submit the correct password
- **Then** the system issues a short-lived, link-scoped access grant (e.g., signed cookie or token) and performs the redirect (301/302) to the actual destination URL

**Scenario 3: Submitting an incorrect password**
- **Given** a visitor is on the intermediary auth page
- **When** they submit an incorrect password
- **Then** the auth page is re-rendered with a generic error message, no redirect occurs, and the destination URL remains undisclosed; repeated failures are rate-limited per link/IP

**Scenario 4: Returning visitor with a valid access grant**
- **Given** a visitor previously authenticated successfully and holds a non-expired access grant for the link
- **When** they request the short link again within the grant's validity window
- **Then** they are redirected directly to the destination without re-entering the password

**Scenario 5: Link owner enables/disables password protection**
- **Given** a link owner has an existing link
- **When** they enable password protection and set a password (or disable it)
- **Then** subsequent redirect behavior reflects the new setting on the next request, and passwords are never stored or returned in plaintext via any API response

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Password field on link metadata (hashed at rest); intermediary auth page route in the Redirection Engine; password verification endpoint; short-lived access grant issuance and validation; rate limiting on password attempts; API support in the Management Service to set/update/remove a link's password.
- **Out of Scope:** Geo/device-based routing rules, expiration/access-restriction logic (covered in Story 2), IP/bot filtering middleware (covered in Story 3), multi-factor auth, SSO/enterprise identity integration.
- **Upstream Dependencies:** None — builds on the existing link storage schema and Redis-backed redirect lookup from Phases 1-2; does not require Stories 2-4 to ship independently.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** None provided; auth page can be a minimal server-rendered Jinja2 template per architecture guidance's Link-in-Bio page serving approach.
- **Technical Context:**
  - Directly implements Architecture Guidance Security Constraint 2: "Ensure password-protected links redirect to an intermediary auth page, not the destination."
  - Store password as a salted hash (e.g., bcrypt/argon2) on the Link record in PostgreSQL; never cache the plaintext or hash in a client-visible location.
  - The Redirection Engine's cache-first lookup (Redis `short_hash -> long_url`) must be extended so that a password-protected flag is checked before any redirect decision is made — the long URL should not be released to the response layer until the access grant is validated.
  - Access grant can be a signed, link-scoped cookie or token (e.g., JWT with short TTL) verified on subsequent requests without a database round-trip.
  - Rate limiting on password attempts can reuse the existing Redis-based API rate limiting infrastructure from the core architecture.
  - Must not block or slow down the redirect hot path for links that are NOT password-protected.
