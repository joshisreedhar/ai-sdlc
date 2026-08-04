"""Short-code generation adapters.

[PHASE 1 / P1-01 - DEVELOPER] Create ``base62_short_code_generator.py`` with
``Base62ShortCodeGenerator`` implementing ``ShortCodeGenerator``.

Use ``secrets.choice`` over ``BASE62_ALPHABET`` rather than ``random`` - short codes are
guessable-by-enumeration otherwise, which matters as soon as Phase 3 introduces
access-restricted links.
"""
