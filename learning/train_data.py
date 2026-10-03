"""Candidate ranker rows use recorded inference-time evidence, retrieval and prior.

No hash pseudo-features, label-derived scores or automatic feature padding. Legacy
snapshots remain readable but cannot train until real candidate signals are recorded.
Signals must be captured before outcome adjudication; schema checks cannot verify provenance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from learning.checkpoint import MODEL_INPUT_DIM, PER_CANDIDATE_EXTRA
from learning.encoder import FEATURE_DIM
from learning.schemas import TrainingExample


def candidate_rows(example: TrainingExample) -> Tuple[List[List[float]], int]:
    """Return (rows, label_index). rows[i] is the model input for candidate i; label_index is the
    position of label_concept_id within candidate_concept_ids. Raises if the label is absent."""
    fv = list(example.feature_vector)
    if len(fv) != FEATURE_DIM or any(type(v) not in (int, float) or not math.isfinite(v) for v in fv):
        raise ValueError("Invalid patient feature vector; explicit schema migration required")
    if len(set(example.candidate_concept_ids)) != len(example.candidate_concept_ids):
        raise ValueError("Duplicate candidate IDs")
    if set(example.candidate_signals) != set(example.candidate_concept_ids):
        raise ValueError("Recorded candidate signals required; hash pseudo-features are not training evidence")
    rows = []
    label_index = -1
    for i, cid in enumerate(example.candidate_concept_ids):
        signals = list(example.candidate_signals[cid])
        if len(signals) != PER_CANDIDATE_EXTRA or any(type(v) not in (int, float) or not math.isfinite(v) for v in signals):
            raise ValueError("Candidate signals must be finite [base_evidence, retrieval, prior]")
        rows.append(fv + signals)
        if cid == example.label_concept_id:
            label_index = i
    if label_index < 0:
        raise ValueError(f"example {example.example_id}: label not in candidate set")
    assert all(len(r) == MODEL_INPUT_DIM for r in rows)
    return rows, label_index


@dataclass
class RankingBatch:
    rows: List[List[float]]        # concatenated candidate rows across the batch
    group_sizes: List[int]         # number of candidates per example (for softmax grouping)
    label_indices: List[int]       # correct-candidate index within each group


def build_batch(examples: Sequence[TrainingExample]) -> RankingBatch:
    rows: List[List[float]] = []
    groups: List[int] = []
    labels: List[int] = []
    for ex in examples:
        r, li = candidate_rows(ex)
        if len(r) < 2:
            continue  # need >=2 candidates for a ranking loss
        rows.extend(r)
        groups.append(len(r))
        labels.append(li)
    return RankingBatch(rows=rows, group_sizes=groups, label_indices=labels)
