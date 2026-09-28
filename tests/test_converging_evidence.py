"""Round-C generalization hardening: differential.py's `_score_disease` now caps how much
cumulative credit STACKED, individually low-value `typical_features` matches can contribute
(`_TYPICAL_FEATURE_CONTRIBUTION_CAP`, two confirmatory findings' worth) -- so simple keyword
counting (many generic symptom words matched for one diagnosis) cannot mathematically outweigh a
single decisive confirmatory/objective finding for a different, more dangerous candidate. The cap
only ever reduces the POSITIVE ranking contribution; it never softens a real contradiction penalty,
and every matched/missing phrase still appears in full in supporting_evidence/
missing_discriminative_evidence -- only the numeric score saturates.

Uses synthetic, self-contained disease entries (not real KB diagnoses, not blind-case wording) so
the exact feature counts driving the cap are fully controlled and verifiable."""

from __future__ import annotations

from nova_agent.differential import CONFIRMATORY_WEIGHT, _TYPICAL_FEATURE_CONTRIBUTION_CAP, _score_disease
from nova_agent.state import PatientState


def _many_generic_entry():
    return {
        "id": "synthetic_many_generic_matches", "name": "Synthetic Many Generic Matches",
        "typical_features": ["fatigue", "malaise", "poor appetite", "mild nausea", "body aches",
                              "low energy", "trouble sleeping", "occasional headache"],
        "risk_factors": [], "confirmatory_findings": [],
    }


def _one_confirmatory_entry():
    return {
        "id": "synthetic_one_confirmatory_finding", "name": "Synthetic One Confirmatory Finding",
        "typical_features": [], "risk_factors": [], "confirmatory_findings": ["diagnostic marker positive"],
    }


def test_typical_feature_cap_engages_when_many_generic_features_all_match():
    state = PatientState(case_id="converge_cap", chief_complaint="feeling generally unwell")
    state.symptoms = ["fatigue", "malaise", "poor appetite", "mild nausea", "body aches",
                       "low energy", "trouble sleeping", "occasional headache"]
    score, _max_possible, supporting, _contra, _missing = _score_disease(_many_generic_entry(), state)
    # All 8 generic features matched (visible in full for clinician review)...
    assert len(supporting) == 8
    # ...but the numeric ranking contribution is capped, not the raw ~9-10 an uncapped sum would give.
    assert score <= _TYPICAL_FEATURE_CONTRIBUTION_CAP + 1e-9


def test_confirmatory_finding_still_outranks_capped_generic_stack():
    """The core converging-evidence guarantee: a diagnosis with ONE decisive confirmatory finding
    must outrank a diagnosis whose only evidence is many stacked generic symptom-word matches."""
    generic_state = PatientState(case_id="converge_generic", chief_complaint="feeling generally unwell")
    generic_state.symptoms = ["fatigue", "malaise", "poor appetite", "mild nausea", "body aches",
                               "low energy", "trouble sleeping", "occasional headache"]
    generic_score, *_ = _score_disease(_many_generic_entry(), generic_state)

    confirmatory_state = PatientState(case_id="converge_confirmatory", chief_complaint="feeling unwell")
    confirmatory_state.laboratory_tests["marker"] = "diagnostic marker positive"
    confirmatory_score, *_ = _score_disease(_one_confirmatory_entry(), confirmatory_state)

    assert confirmatory_score >= generic_score, (
        f"one confirmatory finding ({confirmatory_score}) should not be outweighed by "
        f"{len(_many_generic_entry()['typical_features'])} stacked generic matches ({generic_score})"
    )


def test_cap_never_softens_a_real_contradiction_penalty():
    """Negative control: the cap only bounds the POSITIVE side. A diagnosis whose typical_features
    are mostly explicitly denied must still be penalized in full, uncapped."""
    entry = {
        "id": "synthetic_mostly_denied", "name": "Synthetic Mostly Denied",
        "typical_features": ["fever", "neck stiffness", "photophobia", "rash", "headache"],
        "risk_factors": [], "confirmatory_findings": [],
    }
    state = PatientState(case_id="converge_denied", chief_complaint="mild headache")
    state.symptoms = ["mild headache"]
    state.pertinent_negatives = ["fever", "neck stiffness", "photophobia", "rash"]
    score, _max_possible, _supporting, contradictory, _missing = _score_disease(entry, state)
    assert len(contradictory) == 4
    assert score < 0, "four explicit denials of a disease's own typical_features must net negative"
