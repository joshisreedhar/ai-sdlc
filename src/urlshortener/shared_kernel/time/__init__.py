"""Time abstraction.

The only package permitted to call ``datetime.now()`` / ``datetime.utcnow()``
(architecture rule N-12). Everything else depends on the ``Clock`` protocol so that
time-sensitive behaviour - notably the Phase 3 link-expiration rules - is testable
without patching global state.
"""
