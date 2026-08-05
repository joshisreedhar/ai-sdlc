# Developer Test Gap Analysis

**Phase ID:** phase_1_mvp
**Date:** 2026-08-05

## Executive Summary
The developer's unit and integration test suite for Phase 1 (P1-01 Link Creation API,
P1-02 Redirection Engine, P1-03 Async Click Event Publish, P1-04 Containerization & CI)
is exceptionally thorough and maps cleanly onto every acceptance-criteria scenario in
`artifacts/development_plan/phase_1_mvp/`. Every story's happy path, validation/error
path, and the specific edge cases called out in the stories (short-code collision
retry, concurrent-insert race, cache-degradation on Redis outage, publish-failure
swallowing, fire-and-forget ordering, 404 handling, idempotent schema via Alembic) are
exercised at the appropriate layer (unit tests with fakes for pure logic, integration
tests against real PostgreSQL/Redis for adapters and fully-wired apps). No business
logic discrepancies against `markdowns/REQUIREMENTS.md` were found. **No critical gaps
were identified; QA proceeded directly to Step 3.**

The one legitimate coverage gap is architectural rather than a defect in the
developer's tests: all existing "integration" tests for P1-01/02/03 exercise the
FastAPI apps in-process via `httpx.ASGITransport` (no real network hop, no separately
running processes). The only tests that treat the system as a true black box across a
network boundary are `tests/e2e/test_docker_compose_stack.py` (infra-level, opt-in,
scoped to P1-04's "does it start via compose" concern) and CI's `e2e` job that reuses
it. There was no black-box, application-level E2E suite validating the Phase 1-3 user
journeys (create -> redirect, unknown-code 404, click-event publish/consume) against
independently running services communicating over the network — which is the gap this
QA cycle exists to close (see Step 3).

## Identified Gaps

### 1. Missing Edge Cases
* **Story/Requirement:** None rising to "critical". Minor: P1-03 Scenario 2 ("publish
  failure does not break the redirect") is proven only at the unit level
  (`tests/unit/redirection/test_click_event_dispatcher.py` with a raising fake
  publisher). There is no integration/E2E test that kills the real Redis broker
  mid-run and confirms a live Redirection Engine still returns 302.
* **Missing Coverage:** A black-box scenario with the broker genuinely unreachable
  while PostgreSQL/cache remain up.
* **Risk:** Low. The unit test already proves the dispatcher swallows any exception
  type except `CancelledError`, and the same `ClickEventDispatcher` is used verbatim
  in the composition root, so the behavior is provable by construction. Simulating a
  mid-test broker outage reliably in an automated suite would add flakiness for
  limited additional assurance. Recommendation: acceptable to defer; not a blocker for
  Phase 1 sign-off.

### 2. Missing Error Handling
* No missing error-handling paths were found for the in-scope acceptance criteria.
  Invalid URL payloads, unknown short codes, exhausted short-code generation, and
  unique-constraint races are all covered with explicit assertions on status codes and
  side effects (e.g., "no record created" checks against the real database).

### 3. Business Logic Discrepancies
* None found. Scope boundaries (no custom aliases, no QR codes, no auth, no routing
  rules) are respected by both the implementation and the tests; nothing under test
  reaches into Phase 2+ functionality (confirmed by the 32 passing architecture/phase
  boundary rules in `tests/architecture/`).

## Recommendation
Proceed to E2E test implementation. The developer's tests do not need to be fixed
before E2E testing can reliably proceed — they are a solid foundation. QA implemented
black-box, multi-process E2E tests (real running Management API + Redirection Engine +
Click Consumer, real PostgreSQL/Redis, HTTP over the network) for the three critical
Phase 1 user journeys:
1. Create a link via the Management API, then successfully redirect through it via the
   Redirection Engine.
2. Redirecting an unknown short code returns 404 without a Location header.
3. A redirect publishes a click event that the stub consumer picks up and processes,
   without delaying the redirect response to the client.

See `tests/e2e/test_application_journeys.py`.
