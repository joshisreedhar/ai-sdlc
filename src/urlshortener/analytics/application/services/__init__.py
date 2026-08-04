"""Analytics use cases.

Class names in this package must end with ``Service``, ``Dispatcher`` or ``Handler``
(architecture rule N-03).

[PHASE 1 / P1-03 - DEVELOPER] ``logging_click_event_handler.py`` ->
``LoggingClickEventHandler`` implementing ``ClickEventHandler``.

STUB ONLY: emit one structured log line per event and return. No parsing, no enrichment,
no persistence, no aggregation - those are Phase 2 and are explicitly out of scope
(architecture rule P-05 forbids importing ``sqlalchemy`` anywhere in this context during
Phase 1).
"""
