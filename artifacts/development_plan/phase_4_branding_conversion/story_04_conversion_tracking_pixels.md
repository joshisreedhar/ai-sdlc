# P4-04: Conversion Tracking via Pixel Intermediary Page

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** paid-acquisition marketer,
- **I want to** have my short links fire my Meta/Google Ads/TikTok retargeting pixels before redirecting the visitor,
- **So that** I can attribute downstream conversions (signups, purchases) back to the campaign/ad that generated the click.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- This is the flagship capability of Phase 4: closing the attribution loop for paid acquisition. Per the architecture guidance's "Conversion Tracking Workflow" constraint, links with tracking pixels attached must serve an intermediary HTML page that fires the configured pixels before performing a JavaScript-based redirect. Links without configured pixels must be unaffected and continue to receive the direct, low-latency 301/302 redirect defined in Phase 1 — this story must not regress that hot path. The precise page implementation (server-rendered template vs. static asset with injected config) is open for negotiation.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Link without pixels redirects normally**
- **Given** a short link has no tracking pixels configured
- **When** a visitor clicks the link
- **Then** the Redirection Engine issues a standard 301/302 redirect directly to the destination, with no intermediary page and no added latency

**Scenario 2: Link with pixels serves the intermediary page**
- **Given** a short link has one or more tracking pixels configured (e.g., a Meta Pixel ID, a Google Ads conversion ID, a TikTok Pixel ID)
- **When** a visitor clicks the link
- **Then** the system serves an intermediary HTML page that loads and fires the configured pixel script(s), then performs a JavaScript-based redirect to the destination URL

**Scenario 3: Pixel configuration via API**
- **Given** I own a link
- **When** I attach one or more pixel configurations (provider, pixel ID, event name) to the link via the API
- **Then** subsequent clicks on that link are routed through the intermediary pixel page described in Scenario 2

**Scenario 4: No-JS fallback still redirects**
- **Given** a visitor has JavaScript disabled or blocked
- **When** they land on the intermediary pixel page
- **Then** a no-JS fallback (e.g., meta-refresh or a visible click-through link) still delivers them to the destination within a few seconds

**Scenario 5: Click analytics recorded exactly once**
- **Given** a visitor is routed through the pixel intermediary page
- **When** the page fires pixels and redirects
- **Then** the click event is published to the async analytics pipeline exactly once, with no double-counting caused by the intermediary page load

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Pixel configuration data model and API (attach/list/remove pixel configs per link), the intermediary HTML/JS page template, conditional routing in the Redirection Engine (pixel path vs. direct-redirect path), the no-JS fallback.
- **Out of Scope:** Server-side Conversion API (CAPI) integrations with Meta/Google/TikTok, cross-domain conversion deduplication, arbitrary custom pixel event/customization beyond a page-view/redirect event.
- **Upstream Dependencies:** Phase 1 core redirection engine and click-event publishing; Phase 2 async analytics pipeline (the click event must still be published exactly once regardless of path taken).

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** None provided; the intermediary page is minimal/functional (brief loading state) rather than a designed landing page.
- **Technical Context:** Per `architecture_guidance.md` Section 5, "Conversion Tracking Workflow" — intermediary HTML page must fire pixels before the JS-based redirect. Keep this path outside the hot 301/302 redirect loop so the Redirection Engine's low-latency guarantee (Section 2.2: do not block the redirect response to process analytics) is preserved for the majority of links that have no pixels configured. Pixel configs are stored in PostgreSQL keyed by `link_id`; the intermediary page can be server-rendered via Jinja2 (Section 2.1) with pixel snippets injected based on the configured providers; the click event publish call happens once, at the point the Redirection Engine decides to route to either path.

---
