"""Composition roots - one subpackage per deployable process.

    management_api/     FastAPI app: POST /links            (image: urlshortener-management-api)
    redirection_engine/ FastAPI app: GET /{short_code}      (image: urlshortener-redirection-engine)
    click_consumer/     worker: consumes clicks.v1          (image: urlshortener-click-consumer)

This is the ONLY place in the codebase where concrete adapters may be constructed
(architecture rule L-06). Everything else depends on ports.

Nothing outside ``urlshortener.apps`` may import from it (rule D-06): these packages are
process entry points, not libraries.

Each service subpackage contains at most ``__init__.py``, ``main.py`` and ``container.py``
(rule N-13):

    container.py  builds ``Settings``, opens connections, constructs adapters and services,
                  and publishes them on ``app.state`` (or returns them to ``main``).
    main.py       creates the ASGI ``app`` / ``main()`` entry point, wires the lifespan,
                  mounts routers and middleware.
"""
