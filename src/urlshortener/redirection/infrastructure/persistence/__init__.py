"""READ-ONLY PostgreSQL adapters for the redirect path.

Class names must end with ``Repository`` (architecture rule N-05).

[PHASE 1 / P1-02 - DEVELOPER] ``sqlalchemy_link_read_repository.py`` ->
``SqlAlchemyLinkReadRepository`` implementing ``LinkReadRepository``.

Hard constraint: ``SELECT`` only. No ``INSERT``/``UPDATE``/``DELETE`` may ever appear in
this package. Where possible, give the Redirection Engine a database role with read-only
grants so the constraint is enforced by the database as well as by review.
"""
