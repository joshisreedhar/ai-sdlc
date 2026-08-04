"""Redirection bounded context - the READ / hot path.

Deployed as the **Redirection Engine** (``urlshortener.apps.redirection_engine``).

This is the highest-traffic, most latency-sensitive code in the product. Two rules
dominate its design and are statically enforced:

1. **Read-only.** Nothing here may write to the system of record (architecture rules
   D-04, N-08). Click data leaves through the message broker, never through PostgreSQL.
2. **Never blocks on analytics.** The HTTP redirect is written before the click event is
   published (``markdowns/architecture_guidance.md`` section 2.2).

All future changes to *redirect behaviour* (Phase 3 security/routing, Phase 4 pixel
interstitials) enter through ``application/pipeline`` as new interceptors, or through
``api/middleware`` as new middleware - not by editing the router or the resolution service.
"""
