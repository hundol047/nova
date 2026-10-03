"""Label provenance enforcement (dependency-free).

THE rule this module exists to enforce: a N.O.V.A. prediction (or an LLM suggestion) is NEVER a
training label. Only clinician-adjudicated / coded / pathology-confirmed outcomes are valid labels.
This is what prevents the model from learning to agree with itself (self-reinforcing error).

`validate_label_source` and `filter_valid_examples` are called by the dataset builder AND asserted
in tests, so a forbidden label can never silently enter a training set.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

from learning.schemas import FORBIDDEN_LABEL_SOURCES, LabelSource, TrainingExample


class ForbiddenLabelSourceError(ValueError):
    pass


def is_valid_label_source(source: LabelSource) -> bool:
    return source not in FORBIDDEN_LABEL_SOURCES


def validate_label_source(source: LabelSource) -> None:
    if not is_valid_label_source(source):
        raise ForbiddenLabelSourceError(
            f"label_source={source.value} is FORBIDDEN as a training label. A NOVA prediction or "
            f"LLM suggestion must never become a label (self-reinforcement). Use a clinician-"
            f"confirmed / coded / pathology-confirmed outcome."
        )


def filter_valid_examples(
    examples: Iterable[TrainingExample],
) -> Tuple[List[TrainingExample], List[TrainingExample]]:
    """Split into (kept, rejected). Rejected = forbidden label source. Never raises — the dataset
    builder logs the count and proceeds with only valid rows."""
    kept: List[TrainingExample] = []
    rejected: List[TrainingExample] = []
    for ex in examples:
        (kept if is_valid_label_source(ex.label_source) else rejected).append(ex)
    return kept, rejected
