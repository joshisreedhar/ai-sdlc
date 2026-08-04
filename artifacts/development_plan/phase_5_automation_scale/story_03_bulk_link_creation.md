# P5-03: Bulk Link Creation via Batch and CSV Endpoints

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As an** agency user launching a multi-channel campaign,
- **I want to** create hundreds of short links in a single API call or CSV upload,
- **So that** I don't have to submit each link individually and can launch campaigns in minutes instead of hours.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Single-link creation exists since Phase 1, but power users managing dozens or hundreds of destination URLs per campaign need a batch path — this is one of the explicit "Bulk Operations & API" requirements.
- This story builds directly on the public API and auth from P5-01, and should respect the same rate limits from P5-02 (a batch request may count as multiple units against the quota — exact accounting is negotiable with the team).
- The precise CSV column schema and maximum batch size are open for discussion; the goal is a predictable, partial-failure-safe bulk creation experience.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done". Use BDD (Behavior-Driven Development) Given/When/Then format when possible.*

**Scenario 1: Successful JSON batch creation**
- **Given** an authenticated API client with a valid API key
- **When** they `POST /api/v1/links/batch` with a JSON array of up to 500 link definitions (destination URL, optional custom alias)
- **Then** the system creates all valid links in one transaction and returns a `201` with the full list of created short links and their statuses

**Scenario 2: CSV upload creation**
- **Given** an authenticated API client
- **When** they `POST /api/v1/links/batch/csv` with a CSV file containing `destination_url` and optional `alias` columns
- **Then** the system parses the file, validates each row, and returns a per-row result summary (created / skipped / error with reason)

**Scenario 3: Partial validation failure is reported per-row, not fatal**
- **Given** a batch of 50 links where 3 rows have malformed URLs or duplicate aliases
- **When** the batch is submitted
- **Then** the 47 valid links are created successfully and the response lists the 3 failed rows with specific error messages, without rolling back the valid rows

**Scenario 4: Batch size limit enforced**
- **Given** a batch request exceeding the documented maximum size (e.g., 500 items)
- **When** it is submitted
- **Then** the API rejects the entire request with `422 Unprocessable Entity` and a clear message stating the limit, before any database writes occur

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** JSON batch endpoint, CSV upload endpoint, per-row validation and result reporting, alias de-duplication within a batch and against existing links.
- **Out of Scope:** Bulk edit/update or bulk delete of existing links, scheduled/recurring bulk imports, bulk QR code generation (remains one-at-a-time as delivered in earlier phases).
- **Upstream Dependencies:** Requires P5-01 (public API + API keys) for authentication. Benefits from P5-02 (rate limiting) being in place but can be developed and tested independently against a stub auth layer.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — API feature; CSV template file can be documented in the API reference rather than a UI mockup.
- **Technical Context:** Extends the API & Management Service (FastAPI) responsibility for "Bulk operations" called out explicitly in the architecture guidance. Use Pydantic models to validate each batch item per the "Agent Implementation Rules" (strict validation, OpenAPI standards). Persist rows within a single PostgreSQL transaction with per-row savepoints (or validate-then-insert in one pass) so partial failures don't require manual cleanup. Row-level errors should be returned synchronously for batches under the size cap; no async job queue is required for this story's scope.
