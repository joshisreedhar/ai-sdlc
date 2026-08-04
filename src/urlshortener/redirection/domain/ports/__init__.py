"""Outbound ports owned by the redirection domain.

Every class here must be a ``Protocol`` (rule N-01).

Read/write separation (rule N-08): apart from cache fill (``LinkCache.put``) and event
emission (``ClickEventPublisher.publish``) - neither of which touches the system of record
- every method on these ports must be named ``get_*``, ``find_*``, ``exists_*``, ``list_*``
or ``count_*``. If you find yourself wanting ``save_``/``update_``/``delete_`` here, the
behaviour belongs in the Management API instead.
"""
