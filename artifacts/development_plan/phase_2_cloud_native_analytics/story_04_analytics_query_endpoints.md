# PH2-04: Analytics Query Endpoints & Dashboard View

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** link owner,
- **I want to** query a link's total clicks, unique visitors, geographic breakdown, device/browser breakdown, and top referrers over a chosen time range,
- **So that** I can understand where my traffic comes from and how it engages with my link, and use that insight to optimize my campaigns.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Story PH2-02 gets enriched click data into the analytics store, but that data is worthless to a link owner until it can be queried. This story exposes that data through the API and a minimal presentation layer.
- The team can decide the exact response shape, whether unique visitors are computed via a distinct-IP count, hashed-IP/cookie approach, or a probabilistic counter (e.g., HyperLogLog) — the requirement is only that the number is a reasonable approximation of unique visitors, not perfect deduplication.
- "Dashboard" here can be interpreted as a simple server-rendered page, a JSON API consumed by a lightweight frontend, or both — whichever is fastest to validate the data pipeline end-to-end. Full dashboard UX polish is not the goal of this phase.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Aggregate click stats for a link**
- **Given** a link has recorded click events in the analytics store,
- **When** its owner calls `GET /links/{id}/analytics?range=7d` (or equivalent),
- **Then** the response includes total click count, unique visitor count, and the same time range's data broken down by day.

**Scenario 2: Geographic and device breakdown**
- **Given** a link has clicks from multiple countries and device types,
- **When** the owner requests the geography and device breakdown for that link,
- **Then** the response returns click counts grouped by country (and city where resolved) and grouped by device type/browser/OS, matching the enriched data written by the async pipeline.

**Scenario 3: Referrer breakdown**
- **Given** a link has clicks originating from different referrer sources (including direct/no-referrer traffic),
- **When** the owner requests the referrer breakdown,
- **Then** the response returns click counts grouped by referrer domain, with direct traffic clearly labeled as such rather than omitted.

**Scenario 4: No data yet is handled cleanly**
- **Given** a link exists but has received zero clicks,
- **When** its owner requests analytics for it,
- **Then** the API returns a valid response with zero counts and empty breakdowns (HTTP 200), not an error.

**Scenario 5: Access is scoped to the link owner**
- **Given** two different users each own a link,
- **When** user A requests analytics for user B's link,
- **Then** the API returns an authorization error (403/404) rather than exposing user B's data.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** REST endpoints for total clicks/unique visitors over time, geographic breakdown, device/browser breakdown, and referrer breakdown, scoped per link and per time range; a minimal dashboard view (server-rendered or simple JSON-driven page) rendering these stats.
- **Out of Scope:** Conversion/pixel tracking integration (Phase 4); exporting analytics data (CSV/API for third parties); real-time/streaming updates to the dashboard (polling or on-demand refresh is sufficient); advanced aggregation windows beyond day-level granularity.
- **Upstream Dependencies:** Story PH2-02 must be producing enriched click records in the analytics store for this story's queries to return meaningful data; can be developed against seeded/fixture data in parallel and integrated once PH2-02 lands.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — minimal dashboard; wireframes to be sketched during sprint planning if a UI beyond raw JSON is pursued.
- **Technical Context:** Queries run against the Analytics Data Store described in `architecture_guidance.md` section 4 (PostgreSQL, partitioned tables recommended for this phase's volume). Endpoints should follow the existing FastAPI/Pydantic conventions from Phase 1 (OpenAPI-documented, strict response models). Consider indexing the click events table on `(link_id, created_at)` to keep time-range aggregation queries performant as data grows.
