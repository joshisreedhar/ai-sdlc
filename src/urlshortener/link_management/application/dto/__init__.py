"""Commands and read models crossing the application boundary.

DTOs here are transport-agnostic. HTTP request/response models belong in
``link_management.api.schemas`` and must not be reused as application DTOs
(architecture rule N-07).
"""
