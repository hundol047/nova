import json
from pathlib import Path
import pytest
from scripts.local_model import configure, verify
from nova_agent import config

PROFILE=json.loads((Path(__file__).resolve().parents[1]/'config/nova_local_model.json').read_text())


@pytest.fixture(autouse=True)
def restore_config(monkeypatch):
    old=config._config
    # configure modifies only this explicit environment set; restore after each test.
    for k in ['NOVA_LLM_PROVIDER','NOVA_LLM_MODEL','NOVA_LLM_BASE_URL','NOVA_LLM_API_KEY',
              'NOVA_LLM_TEMPERATURE','NOVA_LLM_MAX_TOKENS','NOVA_LLM_TIMEOUT_SECONDS',
              'NOVA_LLM_MAX_RETRIES','NO_PROXY','no_proxy']:
        monkeypatch.setenv(k, __import__('os').environ.get(k,''))
    yield
    config._config=old


def test_chosen_profile_uses_local_model_without_credentials():
    cfg=configure(PROFILE)
    assert cfg.llm_provider=='local' and cfg.llm_model=='qwen3:4b-instruct'
    assert cfg.llm_api_key==''
    assert PROFILE['automatic_training_enabled'] is False


@pytest.mark.parametrize('url',['https://example.com/v1','http://0.0.0.0:11434/v1',
    'http://user:password@localhost:11434/v1','http://localhost:11434/v1?secret=x'])
def test_profile_refuses_nonlocal_or_credentialed_endpoints(url):
    with pytest.raises(ValueError):configure({**PROFILE,'base_url':url})


def test_unreachable_model_cannot_be_recorded_as_success(monkeypatch):
    import nova_agent.llm_client as llm
    class Unavailable:
        def preflight(self):return False,'connection refused'
    monkeypatch.setattr(llm,'get_llm_client',lambda:Unavailable())
    r=verify(PROFILE,smoke=True)
    assert not r['integration_passed'] and not r['real_structured_turn_passed']
    assert not r['training_performed'] and r['clinical_accuracy'] is None
