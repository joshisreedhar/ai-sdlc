"""Message broker adapters.

Class names must end with ``Publisher``, ``Subscriber`` or ``Consumer``
(architecture rule N-05).

[PHASE 1 / P1-03 - DEVELOPER] ``redis_stream_click_event_publisher.py`` ->
``RedisStreamClickEventPublisher`` implementing ``ClickEventPublisher``:

* ``XADD <settings.click_event_stream> MAXLEN ~ <settings.click_stream_max_len>``
  with the event JSON in a ``payload`` field;
* the stream name carries the schema version (``clicks.v1``) so Phase 2 can introduce an
  incompatible payload on a new stream without a coordinated deploy.
"""
