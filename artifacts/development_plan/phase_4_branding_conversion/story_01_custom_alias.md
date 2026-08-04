# P4-01: Custom Alias for Branded Short Links

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** marketing user creating short links,
- **I want to** specify a custom, human-readable alias when creating a short link,
- **So that** the resulting link is memorable and reinforces my brand instead of exposing a random hash.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Randomly generated short hashes work for the MVP redirection loop, but branded campaigns need recognizable, on-message links (e.g., `/summer-sale` instead of `/aX7fQ2`). This story adds an optional custom-alias field to link creation, layered on top of the Phase 1 link model and Phase 1 redirection lookup, without changing the core redirect performance characteristics.
- The "how" of collision handling (reservation, suggestion of alternatives, etc.) is open for team discussion; the acceptance criteria only fix the observable behavior.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Successful custom alias creation**
- **Given** I am creating a new short link on my account
- **When** I submit a destination URL along with a custom alias, e.g. `summer-sale`
- **Then** the system creates a link resolvable at `<domain>/summer-sale` and returns the full short URL in the API response

**Scenario 2: Alias collision rejected**
- **Given** the alias `summer-sale` already exists on my domain
- **When** I attempt to create another link using the same alias on the same domain
- **Then** the API returns `409 Conflict` with a clear error message and no new link is created

**Scenario 3: Alias validation**
- **Given** I submit an alias containing spaces, unicode control characters, or exceeding 64 characters
- **When** the request is processed
- **Then** the API rejects it with a `422` validation error describing the allowed pattern (alphanumeric, hyphen, underscore, 3-64 characters)

**Scenario 4: Redirection resolves custom alias**
- **Given** a link exists with custom alias `summer-sale` pointing to a destination URL
- **When** a visitor requests `<domain>/summer-sale`
- **Then** the Redirection Engine resolves the alias via the existing cache-first lookup and issues the correct 301/302 redirect

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Optional `alias` field on the link-creation/update API, per-domain uniqueness validation, alias format validation, redirection lookup by alias.
- **Out of Scope:** Custom domain provisioning (see P4-02), alias-specific analytics, premium/reserved alias marketplace, alias editing history.
- **Upstream Dependencies:** Phase 1 core redirection engine and link data model (link table, Redis cache-first lookup pattern).

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** None provided; alias input is a standard form field on the existing link-creation UI/API.
- **Technical Context:** Add a unique constraint on `(domain_id, alias)` in PostgreSQL; extend the Redis cache key pattern to `domain:alias -> destination` (currently `hash -> destination` per architecture guidance Section 2.2); extend the Pydantic `LinkCreate` request model with an optional `alias` field and validation regex.

---
