#!/usr/bin/env python3
"""Configure the chosen local research model and verify real responses (no mock pass).

Start Ollama and pull qwen3:4b-instruct first. This script does not install services,
train weights, change production defaults, or accept non-loopback endpoints.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def configure(profile):
    url = urlsplit(profile['base_url'])
    if url.scheme != 'http' or url.hostname not in {'localhost', '127.0.0.1', '::1'} or url.username or url.password or url.query or url.fragment or url.path.rstrip('/') != '/v1':
        raise ValueError('Local profile must use a loopback HTTP /v1 endpoint')
    if profile['provider'] != 'local' or not profile['model'].strip():
        raise ValueError('A named local model is required')
    values = {'NOVA_LLM_PROVIDER':'local', 'NOVA_LLM_MODEL':profile['model'],
              'NOVA_LLM_BASE_URL':profile['base_url'], 'NOVA_LLM_API_KEY':'',
              'NOVA_LLM_TEMPERATURE':str(profile['temperature']),
              'NOVA_LLM_MAX_TOKENS':str(profile['max_tokens']),
              'NOVA_LLM_TIMEOUT_SECONDS':str(profile['timeout_seconds']),
              'NOVA_LLM_MAX_RETRIES':str(profile['max_retries'])}
    os.environ.update(values)
    # Ensure local traffic does not leave through an inherited HTTP proxy.
    bypass = [s for s in os.environ.get('NO_PROXY', '').split(',') if s]
    os.environ['NO_PROXY'] = ','.join(dict.fromkeys([*bypass, 'localhost', '127.0.0.1', '::1']))
    os.environ['no_proxy'] = os.environ['NO_PROXY']
    from nova_agent.config import get_config
    return get_config(reload=True)


def verify(profile, smoke=False):
    configure(profile)
    from nova_agent.llm_client import get_llm_client
    client = get_llm_client()
    start = time.monotonic()
    ok, reason = client.preflight()
    report = {'provider':'local', 'model':profile['model'], 'base_url':profile['base_url'],
              'preflight_passed':ok, 'reason':reason, 'smoke_requested':smoke,
              'real_structured_turn_passed':False, 'clinical_accuracy':None,
              'training_performed':False, 'clinical_validation':False}
    if ok and smoke:
        from nova_agent.orchestrator import DoctorAgent
        agent = DoctorAgent(llm_client=client)
        state = agent.new_case('local_model_integration_only', 'chest pain', {'age':58, 'sex':'male'})
        action, output, _ = agent.decide(state)
        report.update(real_structured_turn_passed=(state.llm_success_count == 1 and
            state.llm_fallback_count == 0 and state.llm_failure_count == 0),
            llm_calls=state.llm_call_count, llm_successes=state.llm_success_count,
            llm_failures=state.llm_failure_count, fallback_count=state.llm_fallback_count,
            action_type=action.action_type)
    report['elapsed_seconds'] = round(time.monotonic() - start, 3)
    report['integration_passed'] = ok and (not smoke or report['real_structured_turn_passed'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default=str(ROOT/'config/nova_local_model.json'))
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--save-json', required=True)
    args = parser.parse_args()
    report = verify(json.loads(Path(args.profile).read_text()), args.smoke)
    Path(args.save_json).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if not report['integration_passed']: raise SystemExit(1)


if __name__ == '__main__': main()
