"""Dataclass schemas for the learning subsystem (dependency-free).

These describe the inputs/outputs of the ranker and the records that flow through the data
pipeline. No pydantic, no torch — plain dataclasses so the package imports and its non-training
logic runs anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class LabelSource(str, Enum):
    """WHERE a training label came from. Used to ENFORCE that a NOVA prediction is never a label."""

    CLINICIAN_CONFIRMED = "CLINICIAN_CONFIRMED"   # human-adjudicated final diagnosis (allowed)
    CODED_DISCHARGE_DX = "CODED_DISCHARGE_DX"     # coded discharge diagnosis (allowed)
    PATHOLOGY_CONFIRMED = "PATHOLOGY_CONFIRMED"   # gold-standard result (allowed)
    NOVA_PREDICTION = "NOVA_PREDICTION"           # FORBIDDEN as a label — self-reinforcing
    LLM_SUGGESTION = "LLM_SUGGESTION"             # FORBIDDEN as a label — unverified


# Label sources that may NEVER be used to train (would create a feedback loop / launder guesses).
FORBIDDEN_LABEL_SOURCES = frozenset({LabelSource.NOVA_PREDICTION, LabelSource.LLM_SUGGESTION})


@dataclass(frozen=True)
class CandidateFeature:
    """One candidate's features going into the ranker.

    `base_evidence_score` is whatever the deterministic engine already computed (clinical evidence),
    `retrieval_score` is the lexical/ontology match, `prior` is a prevalence prior. The ranker
    combines these; it does not invent evidence.
    """

    concept_id: str
    base_evidence_score: float = 0.0
    retrieval_score: float = 0.0
    prior: float = 0.0
    is_red_flag: bool = False
    is_critical: bool = False
    safety_excluded: bool = False          # set by the safety layer; ranker must respect it
    extra: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RankerInput:
    """A presentation encoded as features + its safety-vetted candidate list."""

    case_id: str
    feature_vector: List[float]
    candidates: List[CandidateFeature]


@dataclass(frozen=True)
class RankedCandidate:
    concept_id: str
    rank: int
    raw_score: float
    calibrated_score: Optional[float]   # None when no calibrator is fitted (honesty rule)
    is_red_flag: bool
    is_critical: bool

    def as_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "rank": self.rank,
            "raw_score": round(self.raw_score, 4),
            "calibrated_score": None if self.calibrated_score is None else round(self.calibrated_score, 4),
            "is_red_flag": self.is_red_flag,
            "is_critical": self.is_critical,
        }


@dataclass(frozen=True)
class RankerOutput:
    case_id: str
    ranked: List[RankedCandidate]
    ood_score: float                    # 0..1, higher = more out-of-distribution
    is_ood: bool
    calibrated: bool                    # whether calibrated_score fields are meaningful
    model_version: str
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "model_version": self.model_version,
            "ood_score": round(self.ood_score, 4),
            "is_ood": self.is_ood,
            "calibrated": self.calibrated,
            "notes": list(self.notes),
            "ranked": [r.as_dict() for r in self.ranked],
        }


@dataclass(frozen=True)
class TrainingExample:
    """One de-identified training row. `label_concept_id` MUST come from an allowed LabelSource."""

    example_id: str
    patient_pseudonym: str              # de-identified stable id for patient-level splitting
    encounter_time: str                 # ISO timestamp for temporal splitting
    feature_vector: List[float]
    candidate_concept_ids: List[str]
    label_concept_id: str
    label_source: LabelSource

    def as_dict(self) -> dict:
        return {
            "example_id": self.example_id,
            "patient_pseudonym": self.patient_pseudonym,
            "encounter_time": self.encounter_time,
            "feature_vector": self.feature_vector,
            "candidate_concept_ids": self.candidate_concept_ids,
            "label_concept_id": self.label_concept_id,
            "label_source": self.label_source.value,
        }
