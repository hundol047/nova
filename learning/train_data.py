"""Training-data adaptation for the candidate ranker (dependency-free).

Converts TrainingExamples into the per-candidate rows the model scores, plus the index of the
correct (labelled) candidate within each candidate set. This is the SAME per-candidate row layout
TorchRanker._candidate_row uses at inference (feature_vector + [base_evidence, retrieval, prior]),
so training and inference agree on the input contract.

Because the immutable snapshot stores only candidate_concept_ids + label_concept_id (not per-
candidate evidence scores), we derive deterministic, leakage-free per-candidate signals here:
  - retrieval_score : 1.0 for the labelled candidate is NOT used (that would leak the label);
                      instead a stable hash-based pseudo-feature keeps candidates distinguishable
                      without encoding the answer. Real deployments replace this with the actual
                      engine-computed base_evidence/retrieval/prior captured alongside the outcome.
The point of this module is a correct, runnable TRAINING CONTRACT; feature richness improves as the
outcome store captures real per-candidate evidence (see docs/learning/DATA_GOVERNANCE.md).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from learning.checkpoint import MODEL_INPUT_DIM, PER_CANDIDATE_EXTRA
from learning.encoder import FEATURE_DIM
from learning.schemas import TrainingExample


def _pseudo_candidate_signal(example_id: str, concept_id: str) -> List[float]:
    """Deterministic, label-free per-candidate signal of length PER_CANDIDATE_EXTRA in [0,1].

    Derived only from (example_id, concept_id) so it is stable and does NOT encode which candidate
    is correct. Stands in for the real base_evidence/retrieval/prior captured at inference time."""
    out = []
    for salt in range(PER_CANDIDATE_EXTRA):
        h = hashlib.sha256(f"{salt}|{example_id}|{concept_id}".encode("utf-8")).hexdigest()
        out.append((int(h[:8], 16) % 1000) / 1000.0)
    return out


def candidate_rows(example: TrainingExample) -> Tuple[List[List[float]], int]:
    """Return (rows, label_index). rows[i] is the model input for candidate i; label_index is the
    position of label_concept_id within candidate_concept_ids. Raises if the label is absent."""
    fv = list(example.feature_vector)
    if len(fv) != FEATURE_DIM:
        # Pad/truncate defensively so a snapshot from a slightly different encoder version still
        # yields the fixed model input dim (mismatch is separately caught by checkpoint guard).
        fv = (fv + [0.0] * FEATURE_DIM)[:FEATURE_DIM]
    rows = []
    label_index = -1
    for i, cid in enumerate(example.candidate_concept_ids):
        rows.append(fv + _pseudo_candidate_signal(example.example_id, cid))
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
