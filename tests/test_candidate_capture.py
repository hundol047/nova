import json
import shutil
import zipfile
from pathlib import Path
import pytest
from scripts.human_sample_capture import verify_runtime

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(params=['v42','v43','v44','v45','v46','v47','v48'])
def candidate(tmp_path,request):
    version=request.param
    out=tmp_path/'artifacts/releases';out.mkdir(parents=True)
    for ext in ['publication.json','submission.zip']:
        shutil.copy2(ROOT/'artifacts/releases'/('nova-'+version+'-'+ext),out/('nova-'+version+'-'+ext))
    with zipfile.ZipFile(out/('nova-'+version+'-submission.zip')) as z:
        z.extractall(tmp_path/'submission')
    for folder in ['competition','nova_agent']:
        shutil.copytree(tmp_path/'submission'/folder,tmp_path/folder)
    return tmp_path,version

def test_candidate_identity_is_explicitly_not_full_suite(candidate):
    root,version=candidate
    result=verify_runtime(root,candidate=version)
    assert result['candidate']==version
    if version in {'v42','v43','v44','v45'}:
        assert 'not a new full-suite' in result['validation_scope']
    else:
        assert result['validation_scope']
        assert result['candidate_zip_sha256']

@pytest.mark.parametrize('kind',['source','staging','extra','archive'])
def test_changed_candidate_is_rejected(candidate,kind):
    root,version=candidate
    paths={'source':'competition/nova_sdk_adapter.py','staging':'submission/run.py',
           'extra':'submission/unexpected.txt','archive':f'artifacts/releases/nova-{version}-submission.zip'}
    with (root/paths[kind]).open('ab') as f:f.write(b'\n# changed\n')
    with pytest.raises(SystemExit):verify_runtime(root,candidate=version)
