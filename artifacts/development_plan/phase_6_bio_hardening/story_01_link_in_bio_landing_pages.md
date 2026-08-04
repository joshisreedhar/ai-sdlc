# PHASE6-01: Hosted Link-in-Bio Landing Pages

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** creator or social media user,
- **I want to** publish a single hosted landing page that lists all of my important short links behind one branded URL,
- **So that** I can share one link in my social media bio and drive my audience to any of my destinations without needing multiple separate links.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- Social platforms (Instagram, TikTok, X, etc.) allow only one clickable link in a user's bio. Competing shortener platforms address this with a hosted "link-in-bio" micro-page that aggregates multiple links.
- This is a net-new, user-facing surface built on top of the existing Link and QR Code capabilities delivered in earlier phases (MVP link creation, branding/custom domains from Phase 4).
- The exact visual editor, theming options, and page builder UX are open for negotiation with design; this story defines the functional contract (create/manage/publish a page and have it served publicly), not the final pixel-perfect UI.
- Per architecture guidance, Link-in-Bio pages are a responsibility of the API & Management Service, not the Redirection Engine, and must not add latency or risk to the core redirect path.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Create and publish a Link-in-Bio page**
- **Given** an authenticated user with at least one existing short link,
- **When** the user creates a Link-in-Bio page, adds one or more of their short links to it, sets a page title, and publishes it,
- **Then** the page is assigned a public URL (on the platform's domain or the user's connected custom domain) and returns HTTP 200 with the configured links rendered when visited by any unauthenticated visitor.

**Scenario 2: Visiting a Link-in-Bio page does not affect redirection engine SLAs**
- **Given** a published Link-in-Bio page containing multiple short links,
- **When** a visitor loads the page and then clicks one of the listed links,
- **Then** the page itself is served from the Management Service (cached/pre-rendered), and clicking a link triggers the normal Redirection Engine flow (cache-first lookup, routing rule evaluation, async click event) exactly as it would from any other referrer, with no added latency on the redirect hop.

**Scenario 3: Update and unpublish a page**
- **Given** a user with an existing published Link-in-Bio page,
- **When** the user edits the page (adds/removes/reorders links, changes title or theme) or unpublishes it,
- **Then** subsequent visits reflect the updated content immediately, and an unpublished page returns HTTP 404 to public visitors while remaining editable/republishable by the owner.

**Scenario 4: Basic branding consistency**
- **Given** a user who has already configured a custom domain or branded alias (Phase 4),
- **When** they publish a Link-in-Bio page,
- **Then** they are able to serve the page under that same custom domain (e.g., `brand.com/bio`) rather than only the platform's default domain.

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Data model and CRUD API for Link-in-Bio pages; public page rendering (server-rendered via Jinja2 template or a JSON API consumable by a lightweight frontend); associating existing short links to a page; publish/unpublish state; serving under an existing custom domain.
- **Out of Scope:** Rich drag-and-drop visual page builder, custom CSS/theme marketplace, analytics specific to page views (page-level view/click breakdown can be a follow-up story), A/B testing of page layouts.
- **Upstream Dependencies:** None required beyond capabilities already delivered (link creation from Phase 1, custom domains from Phase 4). This story can be developed and deployed independently of the other Phase 6 stories.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** None yet — a minimal default theme/template is acceptable for this story; visual design polish is negotiable and can be iterated on post-launch.
- **Technical Context:**
  - Per architecture guidance section 2.1, Link-in-Bio page serving belongs to the API & Management Service, implemented via Jinja2 templates or a JSON API, not the Redirection Engine.
  - New PostgreSQL table(s) for `bio_pages` (owner, slug/domain, title, theme, published flag) and `bio_page_links` (page_id, link_id, position, label) alongside existing Users/Links tables.
  - Reuse the existing custom-domain routing/config from Phase 4 rather than building new domain verification.
  - Page content should be cache-friendly (e.g., short TTL cache or CDN-fronted) since it is public, read-heavy, and changes infrequently relative to redirect traffic.
