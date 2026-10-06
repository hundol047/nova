"""API input validation (spec: reject oversized payload / malformed content / control characters /
unexpected unicode / invalid action or identifiers; patient free text is clinical DATA, never
instructions to execute).

This is the API boundary layer -- it never tries to understand or block "prompt injection" as a
semantic concept (that is handled where the text actually reaches an LLM: see the "Security note"
paragraph nova_agent/llm_client.py's build_reasoning_prompt() prepends, which frames all patient
text as untrusted clinical data for the model itself). What this module does is the cheaper,
deterministic half: reject input that cannot possibly be legitimate clinical free text before it
gets anywhere near the reasoning pipeline.
"""

from __future__ import annotations

import re
import unicodedata

from production.errors import ValidationError

MAX_FREE_TEXT_LENGTH = 4000
MAX_FIELD_LENGTH = 500
MAX_LIST_ITEMS = 100

# C0/C1 control characters other than the ordinary whitespace ones (\t \n \r) a real clinical
# free-text answer could legitimately contain.
_DISALLOWED_CONTROL_CHARS = re.compile(
    "[" + "".join(chr(c) for c in range(0x00, 0x20) if chr(c) not in "\t\n\r") + chr(0x7F) + "]"
)
_VALID_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def validate_free_text(value: str, *, field_name: str, max_length: int = MAX_FREE_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    if len(value) > max_length:
        raise ValidationError(f"{field_name} exceeds the maximum length of {max_length} characters.")
    if _DISALLOWED_CONTROL_CHARS.search(value):
        raise ValidationError(f"{field_name} contains disallowed control characters.")
    # Reject unassigned/private-use/surrogate code points -- a well-formed clinical sentence in any
    # real language never needs them; their presence is a stronger signal of a malformed or
    # adversarial payload than of a legitimate free-text answer.
    for ch in value:
        category = unicodedata.category(ch)
        if category in ("Cs", "Co", "Cn"):
            raise ValidationError(f"{field_name} contains an unsupported unicode character category ({category}).")
    return value


def validate_identifier(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not _VALID_IDENTIFIER.match(value):
        raise ValidationError(
            f"{field_name} must be a non-empty identifier of at most 128 characters "
            "(letters, digits, '_', '.', ':', '-' only)."
        )
    return value


def validate_action_type(value: str) -> str:
    if value not in ("ASK", "EXAM", "TEST", "DIAGNOSE"):
        raise ValidationError(f"Unknown action_type {value!r}; must be one of ASK/EXAM/TEST/DIAGNOSE.")
    return value


def validate_list_length(items: list, *, field_name: str, max_items: int = MAX_LIST_ITEMS) -> list:
    if not isinstance(items, list):
        raise ValidationError(f"{field_name} must be a list.")
    if len(items) > max_items:
        raise ValidationError(f"{field_name} exceeds the maximum of {max_items} items.")
    return items
