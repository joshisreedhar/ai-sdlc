"""Outbound ports (``typing.Protocol``) owned by the link management domain.

Every class in this package must be a ``Protocol`` (architecture rule N-01). Concrete
adapters live in ``urlshortener.link_management.infrastructure`` and are wired in
``urlshortener.apps.management_api.container``.
"""
