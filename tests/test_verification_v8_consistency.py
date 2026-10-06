import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v8_pointer_and_manifest_share_runtime():
    p=json.loads((ROOT/'artifacts/verification/CURRENT_RELEASE.json').read_text())
    v=json.loads((ROOT/'artifacts/verification/local-release-1046986-v8.json').read_text())
    m=json.loads((ROOT/'evaluation/blind_v17_manifest.json').read_text())
    assert v['schema']=='nova-verification-v8'
    assert v['current_blind_version']=='v17'
    assert v['verified_runtime_sha']==m['final_reasoning_sha']
    assert v['runtime_changed_after_freeze'] is False
    assert (ROOT/'artifacts/verification/local-release-659c7dc-v7.json').exists()
    if v['status']=='COMPLETED':
        assert v['blind_v17']['run_count']==1
        assert v['real_gpt_oss']['live_execution']=='NOT VERIFIED'
        assert v['official_api_status']=='NOT VERIFIED'
