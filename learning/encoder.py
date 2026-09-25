"""Clinical feature encoder.

Turns a structured presentation into a fixed-length numeric feature vector for the ranker. The
encoding is deterministic and dependency-free (no torch): torch is only needed to TRAIN the neural
ranker, not to featurize. Keeping the encoder torch-free means feature construction is testable and
reproducible anywhere, and identical between training and inference.

De-identification note: the encoder consumes only clinical signal (age bucket, vitals, symptom
flags, lab flags). It must never receive names, MRNs, dates of birth, or free-text identifiers —
that is the de-identification layer's job upstream (see deidentify.py).
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Sequence

# Fixed feature order. Appended-only to preserve backward compatibility of trained models; never
# reorder existing entries.
NUMERIC_FEATURES: List[str] = [
    "age_years",
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "respiratory_rate",
    "temperature_c",
    "spo2",
    "pain_score",
]

# Symptom/finding flags are hashed into a fixed-width bag-of-flags space so new flags don't change
# the vector length (stable model input dimension).
FLAG_SPACE = 64
FEATURE_DIM = len(NUMERIC_FEATURES) + FLAG_SPACE


def _flag_bucket(flag: str) -> int:
    h = hashlib.sha256(flag.strip().lower().encode("utf-8")).hexdigest()
    return int(h, 16) % FLAG_SPACE


def _norm_numeric(name: str, value: float) -> float:
    """Light, clinically-motivated scaling into roughly [0,1]-ish ranges. Not learned — just keeps
    magnitudes comparable so no single raw feature dominates a linear fallback ranker."""
    ranges = {
        "age_years": (0.0, 100.0),
        "heart_rate": (30.0, 200.0),
        "systolic_bp": (60.0, 220.0),
        "diastolic_bp": (30.0, 130.0),
        "respiratory_rate": (6.0, 40.0),
        "temperature_c": (33.0, 42.0),
        "spo2": (70.0, 100.0),
        "pain_score": (0.0, 10.0),
    }
    lo, hi = ranges.get(name, (0.0, 1.0))
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def encode(numeric: Dict[str, float], flags: Sequence[str]) -> List[float]:
    """Return a FEATURE_DIM-length vector. Missing numerics -> 0.0 (treated as 'unknown', not a
    clinically meaningful zero)."""
    vec = [0.0] * FEATURE_DIM
    for i, name in enumerate(NUMERIC_FEATURES):
        if name in numeric and numeric[name] is not None:
            vec[i] = _norm_numeric(name, float(numeric[name]))
    base = len(NUMERIC_FEATURES)
    for flag in flags:
        if not flag:
            continue
        vec[base + _flag_bucket(flag)] = 1.0
    return vec
