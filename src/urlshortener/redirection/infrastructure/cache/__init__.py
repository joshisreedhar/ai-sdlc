"""Cache adapters. Class names must end with ``Cache`` (architecture rule N-05).

[PHASE 1 / P1-02 - DEVELOPER] ``redis_link_cache.py`` -> ``RedisLinkCache``
implementing ``LinkCache``:

* key: ``urlshortener.redirection.domain.model.cached_link.cache_key(short_code)``
* value: ``CachedLink.model_dump_json()``
* write with ``SETEX`` using ``settings.link_cache_ttl_seconds``
* connection/timeout errors are logged and swallowed - a cache outage must degrade to the
  PostgreSQL path, never fail the redirect.
"""
