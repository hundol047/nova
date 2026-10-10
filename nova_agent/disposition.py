"""Observed safety concerns, independent of the selected diagnosis and its rank.

No diagnostic scores, exclusions or fabricated tests. Existing vital red-flag
thresholds are reused. Pulse/blackout guard: NICE CG109 initial assessment and
1.1.4.3; the <50/>=150 thresholds are existing engineering triage bounds, not
ECG diagnoses. See docs/competition/ROUND_S_CLINICAL_PROVENANCE.md.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

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
    from nova_agent.vitals_parser import fast_pulse_threshold
    if not vitals or vitals.heart_rate is None or not (
            vitals.heart_rate < 50 or vitals.heart_rate >= fast_pulse_threshold(state.demographics.age)):
        return []
    texts = state.all_findings_text(include_context=False, include_family=False)
    # Round W: "collapsed" is reported transient loss of consciousness until shown otherwise (NICE CG109 1.1.1).
    symptoms = [p for p in ("syncope", "loss of consciousness", "lost consciousness", "blacked out", "blackout", "presyncope",
                            "collapsed", "collapse", "keeled over",
                            "lightheadedness", "dizziness", "nearly fainted", "almost passed out",
                            "의식을 잃", "실신", "쓰러졌", "어지러움")
                if feature_present_with_aliases(p, texts, scrub_negated_spans=True)]
    return [f"heart_rate={vitals.heart_rate}", *symptoms] if symptoms else []


def disposition_for(state, final, differential) -> Disposition:
    from nova_agent.vitals_parser import red_flag_rules_for_age
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
        for rule in red_flag_rules_for_age(state.demographics.age):
            value = getattr(vitals, rule["field"], None)
            if value is not None and ops[rule["op"]](value, rule["value"]):
                reasons.append("observed_vital_red_flag:" + rule["field"])
                evidence.append(f"{rule['field']}={value}")
    selected = final.item if final is not None else (differential[0] if differential else None)
    if selected and (selected.dangerous_if_missed or selected.urgency in ("CRITICAL", "HIGH")) \
            and not _sourced_non_emergency(selected):
        reasons.append("urgent_working_diagnosis:" + selected.diagnosis_id)
        evidence.extend(selected.supporting_evidence)
    # Mere safety membership or headache/nausea alone is not an urgent diagnosis.
    # Also retain a specifically supported dangerous alternative to a benign label.
    for item in differential[:5]:
        if (selected is not None and item.diagnosis_id == selected.diagnosis_id) or not item.dangerous_if_missed \
                or _sourced_non_emergency(item):
            continue
        if item.score > 0 and not support_problems(item, state, differential):
            if not _alternative_corroborated(item, state):
                continue
            reasons.append("supported_dangerous_alternative:" + item.diagnosis_id)
            evidence.extend(item.supporting_evidence)
    return Disposition(bool(reasons), tuple(dict.fromkeys(reasons)), tuple(dict.fromkeys(evidence)))


@lru_cache(maxsize=1)
def _non_emergency_tier2_ids() -> frozenset:
    """Tier-2 ids whose enrichment entry carries a sourced `disposition: non_emergency` (field provenance in
    knowledge/tier2_enrichment.json). Static KB metadata, never patient text."""
    path = Path(__file__).resolve().parent / "knowledge" / "tier2_enrichment.json"
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("entries", [])
    except (OSError, ValueError):
        return frozenset()
    return frozenset(e["id"] for e in entries if e.get("disposition") == "non_emergency"
                     and (e.get("provenance") or {}).get("disposition"))


def _sourced_non_emergency(item) -> bool:
    """Round V (NOVA_DISPOSITION_V2): the unverified Tier-2 catalog marks 945 of 1246 entries dangerous. Where a
    guideline places the condition itself in non-emergency care, that sourced entry no longer makes the plan urgent by
    its label alone; vital/rate red flags and supported dangerous alternatives are evaluated unchanged."""
    from nova_agent.config import get_config
    if not get_config().disposition_v2_enabled or not item.diagnosis_id.startswith("onto::tier2:"):
        return False
    return item.diagnosis_id.removeprefix("onto::tier2:") in _non_emergency_tier2_ids()


def _context_only(item) -> bool:
    """Round V (NOVA_DISPOSITION_V2): support made only of risk factors, antecedent context or a clinician's inference
    ("suspected infection source") is not an observed sign or symptom of the dangerous alternative itself."""
    from nova_agent.config import get_config
    if not get_config().disposition_v2_enabled:
        return False
    from nova_agent.differential import _INFERENCE_FEATURE, _entry_for_candidate_id, _strip_negative_prefix
    from nova_agent.final_decision import _antecedent_context, _risk_context
    entry = _entry_for_candidate_id(item.diagnosis_id) or {}
    risks = {str(x).lower() for x in entry.get("risk_factors", [])}
    positive = [p for p in item.supporting_evidence if _strip_negative_prefix(p) is None]
    return bool(positive) and all(p.lower() in risks or _risk_context(p) or _antecedent_context(p)
                                  or _INFERENCE_FEATURE.match(p) for p in positive)


def _alternative_corroborated(item, state=None) -> bool:
    """A shallow ontology alternative needs more than one shared symptom.

    This affects disposition only: the candidate remains in the differential
    and is never marked excluded. Selected urgent working diagnoses and actual
    vital/rate concerns are handled independently above. A current documented
    diagnosis, objective finding or explicit profile discriminator is retained.
    Engineering guard for thin metadata, not a calibrated clinical triage rule.
    """
    if _context_only(item):
        return False
    if not item.diagnosis_id.startswith('onto::'):
        return True
    from nova_agent.differential import _strip_negative_prefix, _entry_for_candidate_id
    from nova_agent.final_decision import _risk_context
    from nova_agent.matching import feature_present
    entry = _entry_for_candidate_id(item.diagnosis_id) or {}
    risks = {str(x).lower() for x in entry.get('risk_factors', [])}
    positive = {p for p in item.supporting_evidence
                if _strip_negative_prefix(p) is None and p.lower() not in risks and not _risk_context(p)}
    if 'documented diagnosis' in positive or len(positive) >= 2:
        return True
    discriminators = {str(x).lower() for field in ('confirmatory_findings','specific_features','red_flag_keywords')
                      for x in entry.get(field, [])}
    objective = state.objective_findings_text() if state is not None else []
    return any(p.lower() in discriminators or
               feature_present(p, objective, scrub_negated_spans=True, strict=True) for p in positive)
