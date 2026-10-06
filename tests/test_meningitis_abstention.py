"""Final naming guard is separate from considering a dangerous differential."""
import pytest
from nova_agent.differential import DifferentialEngine, has_required_diagnostic_context
from nova_agent.state import PatientState
from nova_agent.safety import SafetyLayer


def assess(state):
    candidates=DifferentialEngine().update(state)
    item=next((d for d in candidates if d.diagnosis_id=='meningitis'),None)
    # A meningitis label can only be authorized if meningitis is still in the differential at all; when
    # explicit denials push it out, no final label can be named (the property this test guards).
    return item is not None and has_required_diagnostic_context(item,state)


@pytest.mark.parametrize('text',['headache','headache and fever','headache; no neck stiffness; no photophobia'])
def test_nonspecific_symptoms_do_not_authorize_final_label(text):
    assert not assess(PatientState(case_id='sparse',chief_complaint=text))


@pytest.mark.parametrize('text',['headache and neck stiffness','headache and stiff neck','headache and 首が硬い','headache and 경부강직'])
def test_specific_current_meningeal_evidence_preserves_naming_path(text):
    assert assess(PatientState(case_id='specific',chief_complaint=text))


def test_history_does_not_replace_current_evidence():
    assert not assess(PatientState(case_id='history',chief_complaint='headache',family_history=['neck stiffness']))


def test_unknown_does_not_remove_urgent_safety_concerns():
    state=PatientState(case_id='urgent',chief_complaint='fever with headache')
    assert not assess(state)
    assert 'meningitis' in {f.diagnosis_id for f in SafetyLayer().assess(state,DifferentialEngine().update(state))}
