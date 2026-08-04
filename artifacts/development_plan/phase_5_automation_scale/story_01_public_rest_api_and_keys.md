# P5-01: Public REST API with API Key Management

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As an** agency owner managing many client campaigns,
- **I want to** generate and manage API keys and call a documented public REST API,
- **So that** I can integrate link creation and reporting into my own tools without using the web UI.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Phases 1-4 delivered link creation, security controls, and conversion tracking exclusively through the authenticated web application. Phase 5 opens the same core capabilities to programmatic consumers.
- This story establishes the API surface, versioning, and API-key-based authentication scheme that every other Phase 5 story (bulk creation, webhooks) will sit on top of.
- The "how" of key rotation UX (e.g., self-service portal page vs. CLI) is open for negotiation; the requirement is that keys can be created, listed, and revoked without engineering involvement.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done". Use BDD (Behavior-Driven Development) Given/When/Then format when possible.*

**Scenario 1: Generate a new API key**
- **Given** an authenticated account owner on the dashboard
- **When** they request a new API key with a label (e.g., "Zapier integration")
- **Then** the system generates a unique key, displays the plaintext value exactly once, and stores only a salted hash of it in PostgreSQL

**Scenario 2: Authenticate a public API request**
- **Given** a valid, non-revoked API key
- **When** a request is made to `POST /api/v1/links` with the key in the `Authorization: Bearer <key>` header
- **Then** the request is authenticated, scoped to the owning account, and processed like an equivalent authenticated web action

**Scenario 3: Reject invalid or revoked keys**
- **Given** an API key that has been revoked or does not exist
- **When** a request is made to any `/api/v1/*` endpoint using that key
- **Then** the API responds with `401 Unauthorized` and a machine-readable error body, and no data is returned

**Scenario 4: Revoke a key**
- **Given** an account owner viewing their list of API keys
- **When** they revoke a specific key
- **Then** subsequent requests using that key are rejected within the freshness window of the key cache (max 60 seconds)

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** API key generation/listing/revocation, `/api/v1` namespace and versioning convention, Bearer-token auth middleware, OpenAPI schema for existing link-creation and read endpoints exposed publicly.
- **Out of Scope:** OAuth2/third-party app marketplace, per-key granular scopes/permissions (all keys are account-wide in this phase), rate limiting (covered in P5-02).
- **Upstream Dependencies:** None — builds on the existing link and account models from Phase 1-4; independently deployable and demoable on its own.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — API-first feature, no new end-user UI beyond a simple key-management list/table in the existing dashboard.
- **Technical Context:** Implement as a FastAPI dependency/middleware per the architecture guidance's API & Management Service; add an `api_keys` table (id, account_id, key_hash, label, created_at, revoked_at) in PostgreSQL. Publish an OpenAPI 3.x document per the "Agent Implementation Rules" (Pydantic models, strict validation). Key hashing should use a standard algorithm (e.g., SHA-256 with per-key salt or a KDF); never log plaintext keys.
