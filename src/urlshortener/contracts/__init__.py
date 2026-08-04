"""Cross-process wire contracts.

Schemas in this package are shared between *separate deployable processes* (for example
the Redirection Engine produces a ``ClickEvent`` that the click consumer reads). They are
therefore the most change-sensitive code in the repository.

Rules:

* This package must not import any other ``urlshortener`` package (architecture rule D-03).
* Every schema carries an explicit ``schema_version``.
* Changes must be additive and optional. Removing or retyping a field requires a new
  version (a new stream/queue name and a new key prefix), never an in-place edit.
"""
