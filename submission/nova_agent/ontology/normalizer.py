"""Text normalization for concept lookup (dependency-free).

Handles casing, punctuation, whitespace, and light multilingual folding so that "Acute Abdomen",
"acute-abdomen", and "  ACUTE  ABDOMEN " collapse to the same key. Korean/CJK text is passed
through unchanged (we do not transliterate), only whitespace/punctuation-normalized, so KR aliases
in the KB still match.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+", flags=re.UNICODE)


def normalize(text: str) -> str:
    """Lowercase, strip accents on Latin text, drop punctuation, collapse whitespace.

    CJK codepoints are preserved (unicodedata NFKC keeps them); we only remove punctuation and
    normalize spacing so that lexical matching is stable across input styles.
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text).strip().lower()
    # Remove Latin combining accents (é -> e) without touching CJK.
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


def tokens(text: str) -> List[str]:
    n = normalize(text)
    return [tok for tok in n.split(" ") if tok]
