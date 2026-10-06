import json
import pytest
from pydantic import ValidationError
from evaluation.model_comparison import CaseInput, load_inputs, run_agent, run_direct, sha, score_saved_predictions


def case(**kwargs):
    return CaseInput(case_id='c', family_id='f', split='development', initial='observed symptom',
                     data_type='SYNTHETIC_UNIT_TEST', **kwargs)


def save(tmp_path, cases):
    raw = ('\n'.join(c.model_dump_json() for c in cases) + '\n').encode()
    labels = ('\n'.join(json.dumps({'case_id': c.case_id, 'accepted_diagnoses': ['HIDDEN_GOLD']}) for c in cases) + '\n').encode()
    (tmp_path / 'inputs.jsonl').write_bytes(raw)
    (tmp_path / 'labels.jsonl').write_bytes(labels)
    (tmp_path / 'manifest.json').write_text(json.dumps({'input_sha256': sha(raw), 'label_sha256': sha(labels)}))


def test_direct_prompt_has_only_clinical_input():
    class Client:
        def _post_chat_completion(self, messages):
            assert 'HIDDEN_GOLD' not in messages[0]['content']
            assert 'recorded exam' in messages[0]['content']
            return '{"diagnosis":"unknown","candidates":[]}', {}
    result = run_direct(case(exams={'source_report': 'recorded exam'}), Client())
    assert result['successes'] == 1


def test_unreviewed_interactive_is_blocked_before_calling_client():
    assert 'blocked' in run_agent(case(), object(), True)


def test_gold_field_rejected_by_input_schema():
    with pytest.raises(ValidationError):
        case(ground_truth='HIDDEN_GOLD')


def test_manifest_detects_label_tampering(tmp_path):
    save(tmp_path, [case()])
    (tmp_path / 'labels.jsonl').write_text('changed')
    with pytest.raises(ValueError, match='Label hash'):
        load_inputs(tmp_path)


def test_family_cannot_cross_splits(tmp_path):
    other = case().model_copy(update={'case_id': 'other', 'initial': 'another text', 'split': 'holdout'})
    save(tmp_path, [case(), other])
    with pytest.raises(ValueError, match='Family leakage'):
        load_inputs(tmp_path)


def test_lexically_similar_cases_cannot_cross_splits(tmp_path):
    a = case().model_copy(update={'initial': ' '.join('token' + str(i) for i in range(60))})
    b = a.model_copy(update={'case_id': 'other', 'family_id': 'another', 'split': 'holdout', 'initial': a.initial + ' extra'})
    save(tmp_path, [a, b])
    with pytest.raises(ValueError, match='Near-duplicate'):
        load_inputs(tmp_path)


def test_fallback_correct_string_is_not_scored_as_real_model_success(tmp_path):
    save(tmp_path, [case()])
    result = score_saved_predictions(tmp_path, [
        {'case_id': 'c', 'mode': 'nova_full', 'prediction': 'HIDDEN_GOLD', 'successes': 1, 'fallbacks': 1},
        {'case_id': 'c', 'mode': 'nova_interactive', 'blocked': 'no mapping'}])
    assert result['modes']['nova_full']['exact_matches'] == 0
    assert result['modes']['nova_full']['top1_all_attempts'] == 0
    assert result['modes']['nova_interactive']['top1_all_attempts'] is None
