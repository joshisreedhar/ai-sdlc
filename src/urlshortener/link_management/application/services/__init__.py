"""Use-case services.

Class names in this package must end with ``Service`` or ``Dispatcher``
(architecture rule N-03).

[PHASE 1 / P1-01 - DEVELOPER] ``LinkCreationService`` goes here. Its dependencies
(``LinkRepository``, ``ShortCodeGenerator``, ``Clock``, ``Settings``) are constructor
arguments typed against the *ports*, never against concrete adapters.
"""
