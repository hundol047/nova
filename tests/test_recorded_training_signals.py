"""Synthetic schema checks, not clinical labels or a clinical training dataset."""
from dataclasses import replace
import json
import pytest
from learning.encoder import FEATURE_DIM
from learning.schemas import TrainingExample, LabelSource
from learning.train_data import candidate_rows
from learning.dataset import build_snapshot, load_snapshot
from learning.train import main


def example():
    return TrainingExample('fixture', 'pseudonym', '2026-01-01', [0.0]*FEATURE_DIM,
        ['alpha','beta'], 'beta', LabelSource.CLINICIAN_CONFIRMED,
        {'alpha':[1.2,0.3,0.1], 'beta':[0.4,0.5,0.2]})


def test_training_rows_equal_recorded_inference_contract():
    e=example();rows,index=candidate_rows(e)
    assert rows == [e.feature_vector+e.candidate_signals[c] for c in e.candidate_concept_ids]
    assert index==1


def test_id_and_label_cannot_change_input_features():
    e=example();rows,_=candidate_rows(e)
    other,index=candidate_rows(replace(e, example_id='different',label_concept_id='alpha'))
    assert other==rows and index==0


@pytest.mark.parametrize('signals', [{}, {'alpha':[1,2,3]}, {'alpha':[1,2],'beta':[1,2,3]},
    {'alpha':[float('nan'),0,0],'beta':[1,2,3]}, {'alpha':[True,0,0],'beta':[1,2,3]}])
def test_invalid_or_missing_signals_fail_closed(signals):
    with pytest.raises(ValueError):candidate_rows(replace(example(),candidate_signals=signals))


def test_feature_schema_does_not_silently_pad():
    with pytest.raises(ValueError):candidate_rows(replace(example(),feature_vector=[]))


def test_snapshot_preserves_recorded_signals_and_detects_tampering(tmp_path):
    raw={'example_id':'fixture','patient_id':'fixture_patient','encounter_time':'2026-01-01',
         'candidate_ids':['alpha','beta'],'candidate_signals':example().candidate_signals,
         'label_source':'CLINICIAN_CONFIRMED','label_concept_id':'beta'}
    snap=build_snapshot([raw],tmp_path)
    assert load_snapshot(snap.path)[0].candidate_signals==raw['candidate_signals']
    snap.path.write_text(snap.path.read_text()+'\n')
    with pytest.raises(SystemExit, match='hash mismatch'):
        main(['--snapshot',str(snap.path)])


def test_training_without_manifest_is_rejected(tmp_path):
    path=tmp_path/'untracked.jsonl';path.write_text(json.dumps(example().as_dict()))
    with pytest.raises(SystemExit,match='manifest'):
        main(['--snapshot',str(path)])
