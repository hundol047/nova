"""Read-only reproduction of failures discovered AFTER Round S runtime freeze.

This is an analysis probe, not a replacement scorer or a passing regression test.
Run with NOVA_LLM_PROVIDER=mock NOVA_COMPETITION_RETRIEVAL=1.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nova_agent.differential import DifferentialEngine
from nova_agent.documented_diagnosis import diagnosis_evidence_text, documented_diagnosis_ids
from nova_agent.matching import feature_present, feature_present_with_aliases
from nova_agent.state import PatientState


def main():
    examples = ['Passing urine stings.', 'I pass urine in small amounts.',
                'I am unable to pass urine.']
    matching = [{
        'text': text,
        'unable_direct': feature_present('unable to pass urine', [text], scrub_negated_spans=True),
        'unable_alias': feature_present_with_aliases('unable to pass urine', [text], scrub_negated_spans=True),
        'dysuria_alias': feature_present_with_aliases('dysuria', [text], scrub_negated_spans=True),
    } for text in examples]
    text = 'I have an itchy patch on my wrist. My father had an irregular heartbeat years ago.'
    state = PatientState(chief_complaint=text, preliminary_rules=True)
    ranked = DifferentialEngine().update(state)
    family = {
        'text': text,
        'diagnosis_filtered_text': diagnosis_evidence_text(text, allow_historical=False),
        'documented_ids': documented_diagnosis_ids([text]),
        'patient_findings': state.all_findings_text(include_family=False),
        'rank1_id': ranked[0].diagnosis_id,
        'rank1_support': ranked[0].supporting_evidence,
    }
    print(json.dumps({'matching': matching, 'family': family}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
