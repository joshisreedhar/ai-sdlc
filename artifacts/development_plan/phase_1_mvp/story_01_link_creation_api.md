# P1-01: Link Creation API

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** user of the URL shortener,
- **I want to** submit a long URL and receive back a short, unique code,
- **So that** I can share a compact link that others can use instead of the original long URL.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- This is the entry point of the entire product: without the ability to create a link, there is nothing to redirect. It must exist before the Redirection Engine (P1-02) can be exercised end-to-end.
- Scope here is deliberately minimal: system-generated random short codes only. Custom aliases, custom domains, and QR code generation are explicitly future-phase features (Phase 4: Branding & Conversion Tracking) and are out of scope.
- The exact short-code generation strategy (e.g., base62 random string, length, collision-retry approach) is left to the development team to decide, provided uniqueness and reasonable brevity (recommend 6-8 characters) are guaranteed.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Successfully create a short link**
- **Given** the API is running and connected to PostgreSQL,
- **When** a client submits a valid long URL to the link-creation endpoint,
- **Then** the API responds with a unique short code and the full short URL, and the mapping (short code -> long URL) is persisted in PostgreSQL.

**Scenario 2: Reject an invalid URL**
- **Given** the API is running,
- **When** a client submits a payload that is not a well-formed absolute URL (e.g., missing scheme, malformed structure),
- **Then** the API responds with a 4xx validation error and no record is created.

**Scenario 3: Guarantee short code uniqueness**
- **Given** an existing short code already exists in PostgreSQL,
- **When** the generation logic produces a code that collides with an existing one,
- **Then** the system automatically retries generation until a unique code is produced, without ever returning a duplicate code to two different long URLs.

**Scenario 4: Idempotent service startup**
- **Given** a fresh environment with an empty database,
- **When** the API service starts up,
- **Then** the required `links` table/schema is available (via migration or startup bootstrap) before the first request is served.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** POST endpoint for link creation; Pydantic request/response validation; random short-code generation with collision handling; PostgreSQL persistence of `short_code -> long_url` (plus creation timestamp).
- **Out of Scope:** Custom aliases/custom domains, QR code generation, user authentication/ownership of links, rate limiting, link expiration, password protection, routing rules. These belong to later phases (2-6).
- **Upstream Dependencies:** None. This story can be built and deployed independently — it only requires a provisioned PostgreSQL instance.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A (API-only story, no UI in this phase).
- **Technical Context:**
  - Per `markdowns/architecture_guidance.md` section 2.1, this lives in the **API & Management Service**, built with FastAPI (async).
  - Persist to **PostgreSQL** (architecture guidance section 4): a `links` table storing at minimum `id`, `short_code` (unique, indexed), `long_url`, `created_at`.
  - Use Pydantic models for request/response validation per the "Agent Implementation Rules" (section 5): strict validation, OpenAPI-documented endpoint.
  - Suggested endpoint: `POST /links` accepting `{"long_url": "<string>"}`, returning `{"short_code": "<string>", "short_url": "<string>"}`.
  - Recommend a base62 (a-z, A-Z, 0-9) random string generator for short codes to keep them URL-safe and compact.
