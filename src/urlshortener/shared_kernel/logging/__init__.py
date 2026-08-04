"""Structured logging.

Phase 1 provides a minimal JSON-to-stdout formatter. Phase 6 hardens and standardises
the log schema for centralised collection (Fluentd/Logstash); the ``configure_logging`` /
``get_logger`` entry points are intended to stay stable across that change.
"""
