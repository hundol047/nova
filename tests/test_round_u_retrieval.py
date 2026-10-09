from unittest.mock import patch
from nova_agent import retrieval_pipeline as rp
from tests.test_reranker_topk_bound import _candidate


def test_separate_watch_cannot_replace_a_diagnostic_slot():
    retrieved = [_candidate(f'routine_{i}', score=.9) for i in range(30)]
    retrieved += [_candidate(f'danger_{i}', score=.05, dangerous=True) for i in range(40)]
    result = rp.lightweight_rerank(retrieved, rerank_top_k=25, safety_policy='separate')
    assert [c.concept.concept_id for c in result] == [f'routine_{i}' for i in range(25)]
    assert len(result.safety_watch) == 40
    assert len(result) + len(result.safety_watch) <= len(retrieved)
    assert all('safety_watch_not_diagnostic_rank' in c.reasons for c in result.safety_watch)
    assert all(not c.concept.dangerous for c in result)


def test_actual_production_pipeline_selects_separate_policy():
    retrieved = [_candidate(f'routine_{i}', score=.9) for i in range(25)]
    retrieved.append(_candidate('danger', score=.01, dangerous=True))
    with patch.object(rp, 'retrieve_high_recall', return_value=retrieved):
        result = rp.retrieve_and_rerank(object(), chief_complaint='Observed symptom')
    assert len(result) == 25 and len(result.safety_watch) == 1
    assert result[-1].concept.concept_id == 'routine_24'


def test_watch_can_reenter_when_new_evidence_moves_it_into_diagnostic_topk():
    crowd = [_candidate(f'routine_{i}', score=.9) for i in range(25)]
    initial = rp.lightweight_rerank(crowd + [_candidate('danger', score=.01, dangerous=True)],
                                   safety_policy='separate')
    assert 'danger' not in {c.concept.concept_id for c in initial}
    observed = _candidate('danger', score=1, dangerous=True, match_kind='exact')
    followup = rp.lightweight_rerank([observed] + crowd, safety_policy='separate')
    assert followup[0].concept.concept_id == 'danger'
    assert not followup.safety_watch


def test_watch_ids_are_not_positive_findings_or_diagnoses():
    from nova_agent.state import PatientState
    s = PatientState(chief_complaint='An unclear symptom', retrieval_safety_watch=['tier2:rare_emergency'])
    assert not any('rare_emergency' in t for t in s.all_findings_text())
