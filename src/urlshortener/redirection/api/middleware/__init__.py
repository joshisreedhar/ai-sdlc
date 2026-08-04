"""RESERVED - Phase 3 IP & bot filtering middleware mounts here.

This package must stay EMPTY throughout Phase 1 (architecture rule P-01); the
architecture test suite fails if any module other than ``__init__.py`` appears here.

Why it exists now: ``markdowns/architecture_guidance.md`` Security Constraint 1 requires
IP and bot filtering to execute *before* cache lookup and rule evaluation. Reserving the
mount point ahead of the router - rather than discovering the need later - is what keeps
Phase 3 from having to restructure the request path.

Phase 3 will add (DO NOT ADD NOW):
    bot_signature_middleware.py
    ip_filter_middleware.py
"""
