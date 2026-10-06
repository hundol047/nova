"""Optional syndrome-relationship metadata (documentation/introspection layer, not a functional
gate): expresses how a handful of diagnoses in the knowledge base relate to each other clinically,
without touching the knowledge/diseases/*.json schema or files themselves.

Roles:
  localized_source  -- a diagnosis confined to one anatomical site/organ (e.g. pyelonephritis,
                        pneumonia, uncomplicated_cystitis, appendicitis).
  systemic_syndrome -- a diagnosis defined by a body-wide physiologic response, often triggered BY
                        a localized_source (e.g. sepsis, DKA, anaphylaxis).
  etiology          -- a cause (used loosely here; most entries in this small table are either
                        localized_source or systemic_syndrome, this role is left available for
                        future, more granular annotation without a schema change).

A localized_source and a systemic_syndrome diagnosis are NOT mutually exclusive -- both can (and
often should) remain in the same differential simultaneously (spec: pyelonephritis and sepsis can
coexist as one is the source and the other is the body's response to it). This module intentionally
does NOT encode any hardcoded escalation pair (no "pyelonephritis -> sepsis" rule) -- the actual
generalizable escalation mechanism lives in stop_policy.py, which keeps ANY `dangerous_if_missed`
diagnosis (systemic_syndrome or not) "actively unresolved" when the patient looks physiologically
severe (severity_evidence.severity_score) AND that diagnosis already has some of its own real
supporting evidence -- never gated on this role table, which exists purely so a future analysis or
reporting layer has a name for the relationship, not so behavior depends on it.
"""

from __future__ import annotations

from typing import Literal

SyndromeRole = Literal["localized_source", "systemic_syndrome"]

SYNDROME_ROLE: dict[str, SyndromeRole] = {
    "pyelonephritis": "localized_source",
    "uncomplicated_cystitis": "localized_source",
    "pneumonia": "localized_source",
    "appendicitis": "localized_source",
    "acute_abdomen": "localized_source",
    "acute_pancreatitis": "localized_source",
    "sepsis": "systemic_syndrome",
    "diabetic_ketoacidosis": "systemic_syndrome",
    "anaphylaxis": "systemic_syndrome",
}


def syndrome_role(diagnosis_id: str) -> "SyndromeRole | None":
    return SYNDROME_ROLE.get(diagnosis_id)


def supported_source_syndrome_pairs(differential):
    """Expose concurrently evidenced roles without declaring a causal diagnosis or boosting rank.

    The existing role table supports source/systemic coexistence only; it has no adjudicated
    cause/manifestation/complication edges. Those relationships remain unasserted.
    """
    sources = [d for d in differential if syndrome_role(d.diagnosis_id) == 'localized_source'
               and d.supporting_evidence]
    systemic = [d for d in differential if syndrome_role(d.diagnosis_id) == 'systemic_syndrome'
                and d.supporting_evidence]
    return [{'source_id': a.diagnosis_id, 'syndrome_id': b.diagnosis_id,
             'relationship': 'CONCURRENTLY_SUPPORTED_ROLES', 'causality': 'UNCONFIRMED',
             'source_evidence': list(a.supporting_evidence), 'syndrome_evidence': list(b.supporting_evidence)}
            for a in sources for b in systemic]
