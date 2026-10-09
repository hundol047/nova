"""Round R audited failures become DEVELOPMENT regressions, not independent validation."""
import json
from pathlib import Path
import pytest
from nova_agent.documented_diagnosis import documented_diagnosis_ids, documented_diagnosis_mentions
from nova_agent.state import PatientState
from nova_agent.differential import DifferentialEngine
from nova_agent.final_decision import decide_final

CASES = json.loads((Path(__file__).resolve().parents[1]/'evaluation/assertion_regressions_round_r.json').read_text())['cases']
@pytest.mark.parametrize('case', CASES, ids=lambda c:c['id'])
def test_diagnosis_assertion_scope(case):
    assert set(documented_diagnosis_ids([case['text']])) == set(case['expected'])

@pytest.mark.parametrize('text', [
    'The referral letter says atrial fibrillation was excluded',
    '진단서에 atrial fibrillation 아니라고 적혀 있습니다',
    'My sister was diagnosed with atrial fibrillation; I have never had that diagnosis.',
    'The letter says atrial fibrillation cannot yet be excluded.',
])
def test_nonpositive_diagnosis_cannot_reenter_as_another_diseases_support(text,monkeypatch):
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL','1')
    from nova_agent.config import get_config
    get_config(reload=True)
    try:
        s=PatientState(case_id='scope',chief_complaint=text,preliminary_rules=True)
        diff=DifferentialEngine().update(s)
        assert not any('atrial fibrillation' in e.lower() or e=='documented diagnosis' for d in diff for e in d.supporting_evidence)
        assert decide_final(s,diff,'information_exhausted').undifferentiated
    finally: get_config(reload=True)

def test_all_repeated_mentions_retain_original_offsets():
    t='The note confirms pneumonia and excludes pneumonia after review.'
    ms=[m for m in documented_diagnosis_mentions([t]) if m.diagnosis_id=='pneumonia']
    assert len(ms)==2 and [m.assertion for m in ms]==['PRESENT','NEGATED']
    assert all(t[s:e]=='pneumonia' for s,e in [m.mention_span for m in ms])
