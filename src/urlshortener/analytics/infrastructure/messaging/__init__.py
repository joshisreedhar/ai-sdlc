"""Broker adapters.

Class names must end with ``Publisher``, ``Subscriber`` or ``Consumer`` (rule N-05).

[PHASE 1 / P1-03 - DEVELOPER] ``redis_stream_click_event_subscriber.py`` ->
``RedisStreamClickEventSubscriber`` implementing ``ClickEventSubscriber``:

* create the consumer group idempotently (``XGROUP CREATE ... MKSTREAM``, tolerating
  ``BUSYGROUP``);
* ``XREADGROUP`` with a block timeout;
* parse the ``payload`` field into ``ClickEvent``;
* dispatch to the handler, then ``XACK``. Do not ack before the handler succeeds -
  at-least-once delivery is what makes the Phase 2 pipeline trustworthy.
"""
