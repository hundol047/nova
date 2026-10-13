import json
import shutil
import zipfile
from pathlib import Path
import pytest
from scripts.human_sample_capture import verify_runtime

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def candidate(tmp_path):
    out=tmp_path/'artifacts/releases';out.mkdir(parents=True)
    for ext in ['publication.json','submission.zip']:
        shutil.copy2(ROOT/'artifacts/releases'/('nova-v42-'+ext),out/('nova-v42-'+ext))
    with zipfile.ZipFile(out/'nova-v42-submission.zip') as z:
        z.extractall(tmp_path/'submission')
    for folder in ['competition','nova_agent']:
        shutil.copytree(tmp_path/'submission'/folder,tmp_path/folder)
    return tmp_path

def test_candidate_identity_is_explicitly_not_full_suite(candidate):
    result=verify_runtime(candidate,candidate='v42')
    assert result['candidate']=='v42'
    assert 'not a new full-suite' in result['validation_scope']

@pytest.mark.parametrize('kind',['source','staging','extra','archive'])
def test_changed_candidate_is_rejected(candidate,kind):
    paths={'source':'competition/nova_sdk_adapter.py','staging':'submission/run.py',
           'extra':'submission/unexpected.txt','archive':'artifacts/releases/nova-v42-submission.zip'}
    with (candidate/paths[kind]).open('ab') as f:f.write(b'\n# changed\n')
    with pytest.raises(SystemExit):verify_runtime(candidate,candidate='v42')
