"""Continual-learning GOVERNANCE (dependency-free).

This module encodes the RULES of the continual-learning pipeline — the guardrails, not a training
loop. It is the single place that answers "is it safe to capture / train / promote right now?" and
it refuses when a rule would be violated.

Non-negotiable rules enforced here:
  1. CAPTURE IS OPT-IN. Nothing is written to the outcome store unless NOVA_LEARNING_ENABLED=true.
     Default is false. (learning_enabled())
  2. NO ONLINE / PER-PATIENT TRAINING. Capture only records outcomes; models are trained OFFLINE
     from immutable snapshots, never updated live from a single patient. (assert_offline_training)
  3. A NOVA PREDICTION IS NEVER A LABEL. Capture stores the NOVA top concept separately from the
     label, and a row is training-eligible only once a clinician/coded/pathology label is attached
     (label_status == ADJUDICATED). (capture_record / training_eligible)
  4. DE-IDENTIFY AT CAPTURE. Direct identifiers are stripped and the patient id is pseudonymized
     before a record is built. (capture_record)
  5. NO SELF-MODIFYING PRODUCTION. Training produces a SHADOW model; promotion is an explicit,
     gated, human action in the registry. This module never promotes. (build_shadow_candidate)

Everything is pure/inspectable; the backend calls capture_record() only behind the env gate.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from learning.deidentify import audit_record, has_stable_secret, pseudonymize, strip_identifiers
from learning.labels import is_valid_label_source
from learning.schemas import LabelSource


LEARNING_ENABLED_ENV = "NOVA_LEARNING_ENABLED"


def learning_enabled() -> bool:
    """Continual-learning CAPTURE is OFF unless explicitly enabled. Default false."""
    return os.getenv(LEARNING_ENABLED_ENV, "false").strip().lower() == "true"


class LearningDisabledError(RuntimeError):
    pass


class OnlineTrainingForbiddenError(RuntimeError):
    pass


# Label statuses on an outcome-store row.
LABEL_PENDING = "PENDING_ADJUDICATION"
LABEL_ADJUDICATED = "ADJUDICATED"
LABEL_DISCARDED = "DISCARDED"


@dataclass(frozen=True)
class LearningCaseRecord:
    """One de-identified row destined for clinical_learning_cases. Note nova_top_concept_id and
    label_concept_id are SEPARATE fields — the NOVA prediction is captured for later comparison but
    is never itself the label."""

    learning_case_id: str
    patient_pseudonym: str
    encounter_time: str
    captured_at: str
    feature_snapshot: Dict
    candidate_concept_ids: List[str]
    nova_top_concept_id: Optional[str]
    label_concept_id: Optional[str]
    label_source: str
    label_status: str
    deid_stable: bool

    def as_row(self) -> dict:
        import json
        return {
            "learning_case_id": self.learning_case_id,
            "patient_pseudonym": self.patient_pseudonym,
            "encounter_time": self.encounter_time,
            "captured_at": self.captured_at,
            "feature_snapshot": json.dumps(self.feature_snapshot, ensure_ascii=False, sort_keys=True),
            "candidate_concept_ids": json.dumps(self.candidate_concept_ids, ensure_ascii=False),
            "nova_top_concept_id": self.nova_top_concept_id,
            "label_concept_id": self.label_concept_id,
            "label_source": self.label_source,
            "label_status": self.label_status,
            "deid_stable": self.deid_stable,
            "used_in_snapshot_id": None,
        }

    def training_eligible(self) -> bool:
        """A row may enter a training snapshot only when it has an ADJUDICATED, non-model label."""
        if self.label_status != LABEL_ADJUDICATED:
            return False
        if not self.label_concept_id:
            return False
        try:
            src = LabelSource(self.label_source)
        except ValueError:
            return False
        return is_valid_label_source(src)


def capture_record(
    *,
    raw_patient_record: Dict,
    encounter_time: str,
    feature_snapshot: Dict,
    candidate_concept_ids: Sequence[str],
    nova_top_concept_id: Optional[str],
    clinician_label_concept_id: Optional[str] = None,
    clinician_label_source: Optional[LabelSource] = None,
) -> LearningCaseRecord:
    """Build a de-identified outcome-store record. RAISES LearningDisabledError unless capture is
    enabled. The NOVA prediction is stored ONLY in nova_top_concept_id; it is never used as the
    label. A clinician label (if supplied at capture) must come from a valid, non-model source and
    is marked ADJUDICATED; otherwise the row is PENDING_ADJUDICATION with no label."""
    if not learning_enabled():
        raise LearningDisabledError(
            f"{LEARNING_ENABLED_ENV} is not true; continual-learning capture is disabled. "
            "No clinical outcome may be recorded."
        )

    patient_id = raw_patient_record.get("patient_id") or raw_patient_record.get("id")
    if patient_id is None:
        raise ValueError("raw_patient_record must include a patient_id / id to pseudonymize")

    # De-identify: strip direct identifiers, pseudonymize. feature_snapshot is caller-allow-listed
    # clinical signal only; we defensively strip identifier keys from it too.
    _ = strip_identifiers(raw_patient_record)
    clean_features = strip_identifiers(dict(feature_snapshot))

    label_concept_id: Optional[str] = None
    label_source_str = LabelSource.CLINICIAN_CONFIRMED.value
    label_status = LABEL_PENDING
    if clinician_label_concept_id and clinician_label_source is not None:
        if not is_valid_label_source(clinician_label_source):
            raise ValueError(
                f"clinician_label_source={clinician_label_source.value} is forbidden as a label "
                "(a NOVA prediction / LLM suggestion can never be a label)."
            )
        label_concept_id = clinician_label_concept_id
        label_source_str = clinician_label_source.value
        label_status = LABEL_ADJUDICATED

    return LearningCaseRecord(
        learning_case_id=str(uuid.uuid4()),
        patient_pseudonym=pseudonymize(str(patient_id)),
        encounter_time=str(encounter_time),
        captured_at=datetime.now(timezone.utc).isoformat(),
        feature_snapshot=clean_features,
        candidate_concept_ids=list(candidate_concept_ids),
        nova_top_concept_id=nova_top_concept_id,
        label_concept_id=label_concept_id,
        label_source=label_source_str,
        label_status=label_status,
        deid_stable=has_stable_secret(),
    )


def assert_offline_training(context: str = "") -> None:
    """Call at the top of any training routine to document + enforce that training is OFFLINE and
    batch, never triggered per-patient inline. (There is no online-training code path in this repo;
    this is a tripwire so one is never added silently.)"""
    if os.getenv("NOVA_ONLINE_TRAINING", "false").strip().lower() == "true":
        raise OnlineTrainingForbiddenError(
            "Online/per-patient training is forbidden. Models are trained offline from immutable "
            f"dataset snapshots only. context={context!r}"
        )


@dataclass
class GovernanceReport:
    capture_enabled: bool
    deid_stable: bool
    online_training_blocked: bool
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "capture_enabled": self.capture_enabled,
            "deid_stable": self.deid_stable,
            "online_training_blocked": self.online_training_blocked,
            "notes": list(self.notes),
        }


def governance_report() -> GovernanceReport:
    """A quick, PHI-free snapshot of the learning subsystem's governance posture for an ops surface."""
    notes: List[str] = []
    if not learning_enabled():
        notes.append(f"{LEARNING_ENABLED_ENV}=false (default): no clinical outcomes are being captured.")
    if learning_enabled() and not has_stable_secret():
        notes.append("Capture enabled but NOVA_DEID_SECRET unset: pseudonyms are per-run, "
                     "cross-run patient-level splitting will be unreliable. Set NOVA_DEID_SECRET.")
    return GovernanceReport(
        capture_enabled=learning_enabled(),
        deid_stable=has_stable_secret(),
        online_training_blocked=os.getenv("NOVA_ONLINE_TRAINING", "false").lower() != "true",
        notes=notes,
    )
