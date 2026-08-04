"""Link Management bounded context - the WRITE side of links.

Deployed as the **Management API** (``urlshortener.apps.management_api``).

Phase 1 responsibility: create a link (random short code + destination URL) and persist it.
Later phases extend this context with custom aliases and domains (Phase 4), QR codes
(Phase 4), API keys and bulk creation (Phase 5).

This context must never import ``urlshortener.redirection`` or ``urlshortener.analytics``
(architecture rule D-01).
"""
