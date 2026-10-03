"""Mechanism regressions with newly authored development inputs, not blind answers."""
import pytest
from nova_agent.multilingual_concepts import english_evidence_for
from nova_agent.state import PatientState
from nova_agent.differential import DifferentialEngine, DifferentialItem
from nova_agent.missing_info import MissingInformationAnalyzer
from nova_agent.resolution import is_resolved
import nova_agent.config as config

@pytest.fixture(autouse=True)
def fresh_config(monkeypatch):
    monkeypatch.setattr(config, '_config', None)


@pytest.mark.parametrize('text', ['두통이 아니에요','발열은 없습니다','嘔吐はありません','頭痛はない','下痢はなかった'])
def test_localized_denial_is_not_positive(text):
    assert english_evidence_for(text)==[]

@pytest.mark.parametrize('text,expected', [('두통이 있고 구토는 없어요', ['headache']),('頭痛があります。下痢はありません',['headache']),('복통은 없습니다. 구토는 있어요',['vomiting'])])
def test_denial_stays_with_its_own_symptom(text,expected):
    assert english_evidence_for(text)==expected


def test_bilingual_scoring_does_not_double_count():
    engine=DifferentialEngine()
    def scored(text):
        s=PatientState(case_id='dedup',chief_complaint=text)
        return {d.diagnosis_id:d.score for d in engine.update(s)}
    assert scored('복통 abdominal pain, 설사 diarrhea')==scored('abdominal pain, diarrhea')


def test_objective_exam_ends_false_zero_evidence_state():
    s=PatientState(case_id='objective',chief_complaint='I cannot explain what feels unusual.')
    engine=DifferentialEngine()
    assert all(d.fallback_candidate for d in engine.update(s))
    s.record_exam('lung_auscultation','tracheal deviation')
    d=engine.update(s)
    assert any(x.supporting_evidence for x in d)
    assert not any(x.fallback_candidate for x in d)


def test_new_evidence_can_reenter_differential(monkeypatch):
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL','1')
    s=PatientState(case_id='reentry',chief_complaint='dysuria')
    s.record_test('glucose_point_of_care','glucose 41 mg/dL')
    assert any(d.diagnosis_id=='hypoglycemia' and d.supporting_evidence for d in DifferentialEngine().update(s))


def test_action_focus_keeps_unresolved_critical_and_releases_resolved(monkeypatch):
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL','1')
    s=PatientState(case_id='focus',chief_complaint='chest pain')
    d=DifferentialEngine().update(s)
    critical=next(x for x in d if x.diagnosis_id=='acute_coronary_syndrome')
    leader=DifferentialItem(diagnosis='GERD',diagnosis_id='gerd',rank=1,score=4,score_ratio=.7,urgency='LOW',dangerous_if_missed=False,confidence_band='HIGH',supporting_evidence=['postprandial'])
    analyzer=MissingInformationAnalyzer()
    before=analyzer.analyze(s,[leader,critical],[])
    assert any('acute_coronary_syndrome' in x.disease_ids_discriminated for x in before)
    s.record_test('ecg','normal');s.record_test('troponin','negative')
    assert is_resolved(critical.diagnosis_id,[],s)
    after=analyzer.analyze(s,[leader,critical],[])
    assert not any('acute_coronary_syndrome' in x.disease_ids_discriminated for x in after)
    assert len([leader,critical])==2  # focus does not mutate the caller's safety differential


def test_candidate_drops_then_reenters_when_objective_evidence_changes(monkeypatch):
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL','1')
    s=PatientState(case_id='serial-observation',chief_complaint='headache')
    engine=DifferentialEngine()
    def ids():return {d.diagnosis_id for d in engine.update(s)}
    s.laboratory_tests['beta_hcg']='positive beta-hCG'
    assert 'ectopic_pregnancy' in ids()
    # A corrected/replaced external observation must be re-evaluated, not sticky forever.
    s.laboratory_tests['beta_hcg']='negative beta-hCG'
    assert 'ectopic_pregnancy' not in ids()
    s.laboratory_tests['beta_hcg']='positive beta-hCG'
    assert 'ectopic_pregnancy' in ids()
