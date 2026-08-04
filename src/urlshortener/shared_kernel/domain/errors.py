"""Base error types.

Every domain error in every bounded context must derive from ``DomainError`` so that
the API layer can map "expected business failure" to a 4xx response in one place,
while genuine defects keep bubbling up as 5xx.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all expected, business-rule-driven failures."""
