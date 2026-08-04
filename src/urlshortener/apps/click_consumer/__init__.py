"""Click Consumer composition root (STUB in Phase 1).

Run: ``python -m urlshortener.apps.click_consumer.main``

[PHASE 1 / P1-03 + P1-04 - DEVELOPER] Create ``main.py`` with a ``main() -> None`` entry
point that: loads ``Settings``, calls ``configure_logging``, builds the Redis client,
constructs ``RedisStreamClickEventSubscriber`` and ``LoggingClickEventHandler``, and runs
``asyncio.run(subscriber.run(handler))`` with graceful SIGTERM handling (containers get
terminated, not killed).

No HTTP server, no port, no Celery. Phase 2 replaces this process with Celery workers
consuming the same ``clicks.v1`` stream and the same ``ClickEvent`` contract.
"""
