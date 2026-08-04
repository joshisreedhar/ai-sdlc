"""Application layer: use cases that orchestrate the domain.

May import ``domain``, ``shared_kernel`` and ``contracts`` only. No FastAPI, no
SQLAlchemy, no Redis (architecture rules L-02, L-05).

[PHASE 1 / P1-01 - DEVELOPER] Create here:
    dto/create_link_command.py       CreateLinkCommand
    dto/link_view.py                 LinkView (short_code, short_url)
    services/link_creation_service.py  LinkCreationService
"""
