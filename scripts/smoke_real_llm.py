#!/usr/bin/env python3
"""Minimal configured competition probe, then ONE short synthetic development case.

No model/provider substitution; no blind data; no raw endpoint/credentials/response body logged.
A successful configured stub reports transport success, never official model-weight attestation.
"""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    from nova_agent.config import get_config
    from nova_agent.llm_client import CompetitionLLMClient
    from nova_agent.orchestrator import DoctorAgent
    from competition.adapter import NovaCompetitionAgent, RealLLMUnavailableError
    from competition.readiness import readiness_report
    cfg=get_config()
    if cfg.llm_provider=='mock':
        print('SKIPPED_REAL_LLM: explicit mock development mode');return 0
    if cfg.llm_provider!='competition':
        print('NOT READY: unsupported competition smoke provider');return 1
    client=CompetitionLLMClient();ok,_=client.preflight();report=readiness_report(client)
    report['short_case']='NOT VERIFIED'
    if not ok:
        print(json.dumps(report,sort_keys=True));return 1
    adapter=NovaCompetitionAgent(DoctorAgent(llm_client=client))
    obs={'case_id':'runtime_smoke','observation_type':'initial','chief_complaint':'A new cough over two days',
         'demographics':{'age':39,'sex':'female'},'max_turns':4}
    actions=[]
    try:
        for _ in range(4):
            action=adapter.act(obs);actions.append(action['action_type'])
            if action['action_type'] in {'DIAGNOSE','INSUFFICIENT_INFORMATION'}:break
            obs={'case_id':'runtime_smoke','observation_type':{'ASK':'ask_response','EXAM':'exam_result','TEST':'test_result'}[action['action_type']],
                 'content':'No additional symptoms.' if action['action_type']=='ASK' else 'Normal findings.'}
        state=adapter._states['runtime_smoke']
        passed=bool(actions and actions[-1] in {'DIAGNOSE','INSUFFICIENT_INFORMATION'} and state.real_llm_ever_succeeded is True)
        report.update(short_case='PASS' if passed else 'FAIL',actions=actions,
            calls=state.llm_call_count,successes=state.llm_success_count,failures=state.llm_failure_count,
            fallbacks=state.llm_fallback_count)
    except RealLLMUnavailableError:
        passed=False;report['short_case']='REAL_CALL_FAILED'
    print(json.dumps(report,sort_keys=True))
    return 0 if passed else 1
if __name__=='__main__':sys.exit(main())
