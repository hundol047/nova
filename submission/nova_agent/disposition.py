"""Observed safety concerns, independent of the selected diagnosis and its rank.

No diagnostic scores, exclusions or fabricated tests. Existing vital red-flag
thresholds are reused. Pulse/blackout guard: NICE CG109 initial assessment and
1.1.4.3; the <50/>=150 thresholds are existing engineering triage bounds, not
ECG diagnoses. See docs/competition/ROUND_S_CLINICAL_PROVENANCE.md.
"""
from dataclasses import dataclass

from nova_agent.matching import feature_present_with_aliases


@dataclass(frozen=True)
class Disposition:
    urgent: bool
    reasons: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def as_metadata(self):
        return {"urgent": self.urgent, "reasons": list(self.reasons),
                "observed_evidence": list(self.evidence), "diagnostic_confirmation": False}


def symptomatic_rate_concern(state) -> list[str]:
    """An unexplained measured rate with cerebral/perfusion symptoms; never a subtype."""
    vitals = state.latest_vital_signs()
    if not vitals or vitals.heart_rate is None or not (vitals.heart_rate < 50 or vitals.heart_rate >= 150):
        return []
    texts = state.all_findings_text(include_context=False, include_family=False)
    symptoms = [p for p in ("syncope", "loss of consciousness", "lost consciousness", "blacked out", "blackout", "presyncope",
                            "lightheadedness", "dizziness", "nearly fainted", "almost passed out",
                            "의식을 잃", "실신", "쓰러졌", "어지러움")
                if feature_present_with_aliases(p, texts, scrub_negated_spans=True)]
    return [f"heart_rate={vitals.heart_rate}", *symptoms] if symptoms else []


def disposition_for(state, final, differential) -> Disposition:
    from nova_agent.knowledge.retrieval import vital_sign_red_flags
    from nova_agent.final_decision import support_problems
    reasons, evidence = [], []
    rate = symptomatic_rate_concern(state)
    if rate:
        reasons.append("unexplained_symptomatic_marked_rate")
        evidence.extend(rate)
    # Latest measured vitals only; a prior reading is not silently declared to
    # persist after a new measurement. No unknown/rejected EXAM can supply one.
    vitals = state.latest_vital_signs()
    if vitals:
        ops = {">=": lambda a,b:a>=b, "<=":lambda a,b:a<=b, ">":lambda a,b:a>b, "<":lambda a,b:a<b}
        for rule in vital_sign_red_flags():
            value = getattr(vitals, rule["field"], None)
            if value is not None and ops[rule["op"]](value, rule["value"]):
                reasons.append("observed_vital_red_flag:" + rule["field"])
                evidence.append(f"{rule['field']}={value}")
    selected = final.item if final is not None else (differential[0] if differential else None)
    if selected and (selected.dangerous_if_missed or selected.urgency in ("CRITICAL", "HIGH")):
        reasons.append("urgent_working_diagnosis:" + selected.diagnosis_id)
        evidence.extend(selected.supporting_evidence)
    # Mere safety membership or headache/nausea alone is not an urgent diagnosis.
    # Also retain a specifically supported dangerous alternative to a benign label.
    for item in differential[:5]:
        if item is selected or not item.dangerous_if_missed:
            continue
        if item.score > 0 and not support_problems(item, state, differential):
            reasons.append("supported_dangerous_alternative:" + item.diagnosis_id)
            evidence.extend(item.supporting_evidence)
    return Disposition(bool(reasons), tuple(dict.fromkeys(reasons)), tuple(dict.fromkeys(evidence)))
