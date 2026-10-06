"""Deterministic, dependency-free embedding primitive (feature hashing).

Maps a bag of string features into a fixed-dimension L2-normalized vector using the hashing trick
(signed hashing to reduce collision bias). No numpy/torch needed — pure stdlib — so the whole
retrieval path runs and is testable in any environment. A richer learned encoder (torch) can
replace these vectors later without changing the retrieval interface.

The embedding is DETERMINISTIC: the same feature bag always yields the same vector (stable index).
"""

from __future__ import annotations

import hashlib
import math
from typing import Dict, Iterable, List, Sequence

EMBED_DIM = 256
EMBEDDING_VERSION = "retr-embed.v1"


def _hash(token: str) -> int:
    return int(hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest(), 16)


def _sign(token: str) -> float:
    # A second, independent hash bit decides the sign -> reduces systematic collision bias.
    return 1.0 if (_hash("sign::" + token) & 1) else -1.0


def hash_embed(features: Iterable[str], weights: Dict[str, float] | None = None,
               dim: int = EMBED_DIM) -> List[float]:
    """Feature-hash a weighted bag of string features into an L2-normalized dim-vector."""
    vec = [0.0] * dim
    weights = weights or {}
    for feat in features:
        if not feat:
            continue
        f = feat.strip().lower()
        if not f:
            continue
        w = weights.get(feat, weights.get(f, 1.0))
        idx = _hash(f) % dim
        vec[idx] += w * _sign(f)
    # L2 normalize (so cosine == dot product).
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity of two equal-length vectors (both assumed L2-normalized -> dot product)."""
    n = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(n))
