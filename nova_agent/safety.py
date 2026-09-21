"""Dangerous Diagnosis Safety Layer (spec section 5).

Makes sure a time-critical condition is never silently dropped just because it currently ranks
low in the differential. A critical condition is only ever flagged when it is already plausible
for this case -- relevant to the current chief complaint AND/OR already showing at least one
matching keyword/vital-sign trigger -- never as a blanket "test everything dangerous" reflex.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel

from nova_agent.chief_complaint import classify as classify_chief_complaint
from nova_agent.differential import DifferentialItem
from nova_agent.knowledge.retrieval import critical_condition_ids, disease_by_id, vital_sign_red_flags
from nova_agent.matching import feature_present
from nova_agent.state import PatientState, RedFlag

_OPS = {">=": lambda v, t: v >= t, "<=": lambda v, t: v <= t, ">": lambda v, t: v > t, "<": lambda v, t: v < t}


class SafetyFinding(BaseModel):
    diagnosis_id: str
    condition: str
    reason: str
    evidence: List[str]
    source: str  # 'symptom_keyword' | 'vital_sign'
    urgency: str = "CRITICAL"


class SafetyLayer:
    def assess(self, state: PatientState, differential: List[DifferentialItem]) -> List[SafetyFinding]:
        findings: List[SafetyFinding] = []
        tag = classify_chief_complaint(state.chief_complaint)
        differential_ids = {d.diagnosis_id for d in differential}
        findings_text = state.all_findings_text()

        for diagnosis_id in critical_condition_ids():
            entry = disease_by_id(diagnosis_id)
            if entry is None:
                continue
            relevant = tag in entry.get("chief_complaint_tags", []) or diagnosis_id in differential_ids
            if not relevant:
                continue
            matched_keywords = [kw for kw in entry.get("red_flag_keywords", []) if feature_present(kw, findings_text)]
            if matched_keywords:
                findings.append(SafetyFinding(
                    diagnosis_id=diagnosis_id, condition=entry["name"],
                    reason=f"Symptom findings overlap with red-flag features for {entry['name']}",
                    evidence=matched_keywords, source="symptom_keyword", urgency=entry.get("urgency", "CRITICAL"),
                ))

        for vitals in state.vital_signs:
            values = vitals.model_dump()
            for rule in vital_sign_red_flags():
                value = values.get(rule["field"])
                if value is None:
                    continue
                if _OPS[rule["op"]](value, rule["value"]):
                    for diagnosis_id in rule.get("suggests", []):
                        entry = disease_by_id(diagnosis_id)
                        if entry is None:
                            continue
                        if tag not in entry.get("chief_complaint_tags", []) and diagnosis_id not in differential_ids:
                            continue  # not relevant to this case -- do not raise a flag for it
                        findings.append(SafetyFinding(
                            diagnosis_id=diagnosis_id, condition=entry["name"],
                            reason=rule["reason"], evidence=[f"{rule['field']}={value}"],
                            source="vital_sign", urgency=entry.get("urgency", "CRITICAL"),
                        ))

        # Dedup (same diagnosis flagged by both a keyword and a vital sign) while keeping the
        # richer entry (more evidence).
        by_id: Dict[str, SafetyFinding] = {}
        for f in findings:
            existing = by_id.get(f.diagnosis_id)
            if existing is None or len(f.evidence) > len(existing.evidence):
                by_id[f.diagnosis_id] = f
            elif existing is not None:
                existing.evidence = list(dict.fromkeys(existing.evidence + f.evidence))

        result = sorted(by_id.values(), key=lambda f: f.condition)
        state.red_flags = [RedFlag(condition=f.condition, reason=f.reason, severity=f.urgency) for f in result]
        return result

    def safety_gain(self, diagnosis_id: str, findings: List[SafetyFinding]) -> float:
        """Boost magnitude used by action_selector.py's utility function: 1.0 if this diagnosis is
        currently flagged as a safety concern (still needs to be actively ruled out), else 0.0."""
        return 1.0 if any(f.diagnosis_id == diagnosis_id for f in findings) else 0.0
