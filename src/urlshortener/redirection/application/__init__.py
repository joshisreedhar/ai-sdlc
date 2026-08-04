"""Application layer for the redirection context.

    pipeline/   the interceptor chain - THE extension seam for Phases 3 and 4
    services/   the terminal resolution use case and the click-event dispatcher

[PHASE 1 - DEVELOPER] Create in ``services/``:
    link_resolution_service.py   ``LinkResolutionService``  (P1-02, terminal handler)
    click_event_dispatcher.py    ``ClickEventDispatcher``   (P1-03, fire-and-forget)
"""
