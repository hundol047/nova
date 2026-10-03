"""Dataset splitting: patient-level AND temporal (dependency-free).

Two leakage risks the naive random split invites:
  1. Patient leakage: the same patient appearing in train and test inflates metrics. We split by
     `patient_pseudonym` so a patient is wholly in one fold.
  2. Temporal leakage: training on the future to predict the past. We support a temporal split by
     `encounter_time` so the test set is strictly later than train.

The temporal split takes precedence when requested; patient-level integrity is preserved by pushing
a patient entirely to whichever side its EARLIEST encounter falls (never straddling the cutoff).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from learning.schemas import TrainingExample


@dataclass(frozen=True)
class SplitResult:
    train: List[TrainingExample]
    test: List[TrainingExample]
    strategy: str
    train_patients: int
    test_patients: int

    def patient_overlap(self) -> set:
        tr = {e.patient_pseudonym for e in self.train}
        te = {e.patient_pseudonym for e in self.test}
        return tr & te


def patient_level_split(examples: Sequence[TrainingExample], test_frac: float = 0.2) -> SplitResult:
    """Deterministic patient-level split (hash of pseudonym -> stable bucketing)."""
    import hashlib

    def bucket(p: str) -> float:
        h = hashlib.sha256(p.encode("utf-8")).hexdigest()
        return (int(h[:8], 16) % 10000) / 10000.0

    train, test = [], []
    for e in examples:
        (test if bucket(e.patient_pseudonym) < test_frac else train).append(e)
    return SplitResult(
        train=train, test=test, strategy="patient_level",
        train_patients=len({e.patient_pseudonym for e in train}),
        test_patients=len({e.patient_pseudonym for e in test}),
    )


def temporal_split(examples: Sequence[TrainingExample], cutoff_iso: str) -> SplitResult:
    """Split so test encounters are strictly at/after cutoff, keeping each patient on one side by
    their earliest encounter time."""
    earliest: Dict[str, str] = {}
    for e in examples:
        cur = earliest.get(e.patient_pseudonym)
        if cur is None or e.encounter_time < cur:
            earliest[e.patient_pseudonym] = e.encounter_time
    train, test = [], []
    for e in examples:
        if earliest[e.patient_pseudonym] >= cutoff_iso:
            test.append(e)
        else:
            train.append(e)
    return SplitResult(
        train=train, test=test, strategy=f"temporal>={cutoff_iso}",
        train_patients=len({e.patient_pseudonym for e in train}),
        test_patients=len({e.patient_pseudonym for e in test}),
    )
