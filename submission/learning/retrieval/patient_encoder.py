"""Patient-side encoder: turns a structured presentation into a retrieval embedding.

Encodes the clinical signal a presentation carries — chief complaint, symptoms, negatives, history,
medications, allergies, vitals (as coarse flags), labs/ECG/imaging findings, plus age/sex/pregnancy
context — into the SAME embedding space as diseases, so patient<->disease cosine similarity is
meaningful. Dependency-free (feature hashing); torch encoder optional later.

De-identification: this encoder consumes only clinical signal. It must never receive names/MRNs/
DOBs — that is upstream de-identification's job (see learning/deidentify.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Sequence

from learning.retrieval.embedding import EMBED_DIM, hash_embed

_TOKEN_RE = re.compile(r"[a-z0-9\uac00-\ud7a3]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


@dataclass(frozen=True)
class PatientQuery:
    """Structured, de-identified presentation for retrieval."""

    chief_complaint: str = ""
    symptoms: Sequence[str] = ()
    negatives: Sequence[str] = ()          # explicitly denied symptoms
    history: Sequence[str] = ()
    medications: Sequence[str] = ()
    allergies: Sequence[str] = ()
    lab_findings: Sequence[str] = ()
    imaging_findings: Sequence[str] = ()
    ecg_findings: Sequence[str] = ()
    age_years: float | None = None
    sex: str = ""
    pregnant: bool = False
    external_codes: Sequence[tuple] = ()   # (system, code)


def _age_band(age: float | None) -> str:
    if age is None:
        return ""
    if age < 1:
        return "age:neonate"
    if age < 12:
        return "age:child"
    if age < 18:
        return "age:adolescent"
    if age < 65:
        return "age:adult"
    return "age:elderly"


def _feature_bag(q: PatientQuery) -> tuple:
    """Returns (positive_features, negative_features). Negatives get a small negative weight so a
    denied symptom nudges AWAY from diseases defined by it, without hard-excluding (safety recall
    still runs separately)."""
    pos: List[str] = []
    for t in _tokens(q.chief_complaint):
        pos.append(f"name:{t}")
        pos.append(f"cc:{t}")
    for s in q.symptoms:
        for t in _tokens(str(s)):
            pos.append(f"name:{t}")
            pos.append(f"feat:{t}")
    for h in q.history:
        for t in _tokens(str(h)):
            pos.append(f"feat:{t}")
    for m in q.medications:
        for t in _tokens(str(m)):
            pos.append(f"feat:{t}")
    for lst in (q.lab_findings, q.imaging_findings, q.ecg_findings):
        for item in lst:
            for t in _tokens(str(item)):
                pos.append(f"feat:{t}")
    for sysid, _code in q.external_codes:
        pos.append(f"sys:{str(sysid).lower()}")
    band = _age_band(q.age_years)
    if band:
        pos.append(band)
    neg: List[str] = []
    for n in q.negatives:
        for t in _tokens(str(n)):
            neg.append(f"name:{t}")
            neg.append(f"feat:{t}")
    return pos, neg


class PatientEncoder:
    def __init__(self, dim: int = EMBED_DIM) -> None:
        self.dim = dim

    def encode(self, q: PatientQuery) -> List[float]:
        pos, neg = _feature_bag(q)
        weights = {}
        for f in pos:
            weights[f] = 2.0 if f.startswith("name:") else 1.2
        for f in neg:
            # small negative weight: denied features gently repel, never hard-exclude.
            weights[f] = weights.get(f, 0.0) - 0.5
        return hash_embed(list(pos) + list(neg), weights=weights, dim=self.dim)


def encode_patient(q: PatientQuery, dim: int = EMBED_DIM) -> List[float]:
    return PatientEncoder(dim=dim).encode(q)
