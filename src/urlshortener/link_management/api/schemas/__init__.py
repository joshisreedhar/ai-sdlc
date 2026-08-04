"""Pydantic request/response models.

Class names must end with ``Request`` or ``Response`` (architecture rule N-07).
These are transport types: never pass them into the application layer and never return
a domain object directly from a router.
"""
