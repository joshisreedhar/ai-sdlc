"""Configuration.

The only package in the codebase permitted to read ``os.environ`` / ``os.getenv``
(architecture rule D-07). Everything else receives an injected ``Settings`` instance.
"""
