from nova_agent.differential import DifferentialItem
from nova_agent.disposition import _alternative_corroborated


def candidate(evidence,identifier='onto::tier2:bowel_obstruction'):
    return DifferentialItem(diagnosis_id=identifier,diagnosis='test alternative',rank=2,score=2,
        score_ratio=.5,supporting_evidence=evidence,dangerous_if_missed=True,urgency='HIGH',confidence_band='LOW')


def test_shared_symptom_does_not_alone_make_a_thin_alternative_an_emergency():
    assert not _alternative_corroborated(candidate(['colicky abdominal pain']))


def test_corroborating_feature_and_current_documentation_remain_visible():
    assert _alternative_corroborated(candidate(['colicky abdominal pain','abdominal distension']))
    assert _alternative_corroborated(candidate(['documented diagnosis']))


def test_deep_profile_emergency_discriminator_preserves_existing_path():
    assert _alternative_corroborated(candidate(['thunderclap headache'],'subarachnoid_hemorrhage'))


def test_negative_or_historical_feature_cannot_supply_corroboration():
    assert not _alternative_corroborated(candidate(['colicky abdominal pain','no fever','history of bowel obstruction']))


def test_objective_exam_discriminator_does_not_need_a_second_symptom():
    from nova_agent.state import PatientState
    s=PatientState();s.record_exam('cardiac_auscultation','A pericardial friction rub is heard.')
    assert _alternative_corroborated(candidate(['friction rub'],'onto::tier2:pericarditis'),s)


def test_unconfirmed_exam_does_not_supply_corroboration():
    from nova_agent.state import PatientState
    s=PatientState();s.record_exam('cardiac_auscultation','A friction rub cannot be confirmed.')
    assert not _alternative_corroborated(candidate(['friction rub'],'onto::tier2:pericarditis'),s)
