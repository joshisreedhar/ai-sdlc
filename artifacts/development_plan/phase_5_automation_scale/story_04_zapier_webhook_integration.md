# P5-04: Zapier and Outbound Webhook Integrations

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** marketing operations user,
- **I want to** trigger workflows in Zapier (or any tool via webhooks) whenever a link is created or receives a click,
- **So that** I can automatically log campaign activity into my CRM, spreadsheets, or notification channels without manual data entry.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- The requirements explicitly call for "integrations with platforms like Zapier" alongside REST API access; this story delivers the event-driven half of automation (as opposed to the request/response API in P5-01/P5-03).
- Rather than building a bespoke Zapier app immediately, this story focuses on a generic outbound webhook subscription mechanism that a Zapier "REST Hooks" integration (or any other tool) can subscribe to — the specific Zapier app packaging/certification can be negotiated as a fast-follow using this same webhook contract.
- Which events are supported first (link.created, link.clicked, conversion.tracked) is open for discussion, but click-volume events must not be allowed to overwhelm subscriber endpoints or the platform itself.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done". Use BDD (Behavior-Driven Development) Given/When/Then format when possible.*

**Scenario 1: Register a webhook subscription**
- **Given** an authenticated API client
- **When** they `POST /api/v1/webhooks` with a target URL and a list of event types (e.g., `link.created`)
- **Then** the subscription is stored and a shared signing secret is returned exactly once for verifying future payloads

**Scenario 2: Event delivery on link creation**
- **Given** an active webhook subscribed to `link.created`
- **When** a new link is created via the UI, API, or bulk batch endpoint
- **Then** a signed HTTP POST payload describing the event is delivered asynchronously to the subscriber's URL without delaying the original create request

**Scenario 3: Delivery retries on subscriber failure**
- **Given** a subscriber endpoint that returns a `5xx` error or times out
- **When** the platform attempts delivery
- **Then** the event is retried with exponential backoff up to a documented maximum attempt count, after which it is marked failed and visible in a delivery log

**Scenario 4: Payload signature verification**
- **Given** a webhook payload delivered to a subscriber
- **When** the subscriber computes an HMAC signature of the raw body using the shared secret
- **Then** it matches the signature provided in the `X-Signature` request header, allowing the subscriber to reject forged requests

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** Webhook subscription CRUD, async event dispatch for `link.created`, `link.clicked`, and `conversion.tracked` events, HMAC payload signing, retry/backoff with a delivery log.
- **Out of Scope:** Publishing an official Zapier app to the Zapier marketplace, inbound Zapier "actions" (e.g., Zapier creating links by calling back into our API — already covered by P5-01/P5-03), UI for building custom automation logic.
- **Upstream Dependencies:** None strictly required, but naturally follows P5-01 since subscriptions are managed via the same authenticated API surface; independently deployable behind a feature flag.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context, wireframes, or API contracts so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** N/A — backend/API feature; a simple webhook-management screen in the dashboard is a nice-to-have, not required for "Done."
- **Technical Context:** Per the architecture guidance, the Redirection Engine "must not block the redirect response to process analytics" — webhook dispatch for `link.clicked` must be published onto the existing Celery/Redis message broker used for click-event ingestion, not fired synchronously from the redirect path. A new `webhook_subscriptions` table in PostgreSQL stores target URL, event types, and hashed secret; a Celery task handles delivery, retry/backoff, and writes to a `webhook_deliveries` audit log table.
