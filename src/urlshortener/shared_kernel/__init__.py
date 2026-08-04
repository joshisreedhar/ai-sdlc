"""Shared kernel: cross-cutting primitives used by every bounded context.

This package is a *dependency sink*. It must never import a bounded context,
``urlshortener.contracts``, or ``urlshortener.apps`` (architecture rule D-02).

Anything placed here is, by definition, something every context is allowed to
depend on forever. Add sparingly.
"""
