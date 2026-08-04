"""Analytics bounded context - click ingestion and (from Phase 2) metrics.

Deployed as the **Click Consumer** (``urlshortener.apps.click_consumer``).

Phase 1 is deliberately a stub: it consumes ``ClickEvent`` messages off the broker and
logs them. There is no User-Agent parsing, no GeoIP resolution, no persistence and no
query surface - all of that is Phase 2. The stub exists to prove the publish-to-consume
path end to end (story P1-03, acceptance scenario 4) so that Phase 2 builds against an
already-working contract.

This context must not import ``redirection`` or ``link_management`` (rule D-01); it shares
only ``urlshortener.contracts``.
"""
