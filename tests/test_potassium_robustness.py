import pytest
from evaluation.potassium_robustness import PROBES
from nova_agent.electrolyte_evidence import extract_potassium_mmol_l

@pytest.mark.parametrize('text,expected',PROBES)
def test_potassium_parser_rejects_ambiguous_or_unsupported_values(text,expected):
    assert extract_potassium_mmol_l(text)==expected


@pytest.mark.parametrize('text,expected',[
    ('potassium 6.8 mol/L',False),
    ('potassium 6.8 mEq/dL',False),
    ('potassium 6.8 mmol/L; potassium 4.2 mmol/L',False),
    ('potassium 6.8 mmol/L',True),
])
def test_only_valid_potassium_adds_confirmatory_diagnostic_support(text,expected):
    from nova_agent.state import PatientState
    from nova_agent.differential import _score_disease
    from nova_agent.knowledge.retrieval import disease_by_id
    state=PatientState();state.record_test('bmp',text)
    supporting=_score_disease(disease_by_id('severe_electrolyte_disorder'),state)[2]
    assert any(x.startswith('severe hyperkalemia (potassium') for x in supporting)==expected
