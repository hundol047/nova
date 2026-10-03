"""Frozen research-only external case replay; no labels/options enter the agent.

All source case/exam/test information is presented up front as one text packet.
Requests for additional information receive unknown, never fabricated normals.
This is an adapter smoke evaluation, not the published DiagnosisArena protocol.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['NOVA_LLM_PROVIDER'] = 'mock'
from nova_agent.orchestrator import DoctorAgent
from scripts.run_large_simulation import runtime_digest


def normalize(text):
    return re.sub(r'\W+', '', (text or '').casefold())


def main():
    source = ROOT / 'research/external_evidence/target_cases_9.jsonl'
    out = ROOT / 'docs/evaluation/external_nine_2026_10_03'
    out.mkdir(parents=True, exist_ok=False)
    records = [json.loads(line)['original_record'] for line in source.read_text().splitlines()]
    # Strict allowlist: omit Final Diagnosis, Options and Right Option.
    packets = [{'id': str(r['id']), 'text': '\n\n'.join(
        f'{k}:\n{r[k]}' for k in ('Case Information', 'Physical Examination', 'Diagnostic Tests'))}
        for r in records]
    payload = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in packets)
    (out / 'inputs.jsonl').write_text(payload)
    before = runtime_digest(ROOT)
    metadata = {
        'scope': 'EXTERNAL_PUBLIC_RESEARCH_CASES_MOCK_RUNTIME_ADAPTER_EVALUATION',
        'provider': 'mock', 'training': False, 'clinical_validation': False,
        'independent_unseen_test': False, 'selection': 'previously inspected nine final-label term matches',
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'input_sha256': hashlib.sha256(payload.encode()).hexdigest(),
        'runtime_sha256': before,
        'runtime_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'input_policy': 'unmodified source clinical fields up front; no gold/options',
        'response_policy': 'Additional information is not available in the supplied case.',
        'scoring': 'normalized complete final diagnosis exact match; no synonym or component credit',
        'safety_metrics': 'NOT_SCORED: no expert triage labels',
        'terms': 'Research/model evaluation only; not clinical decision-making or medical diagnosis',
    }
    (out / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    predictions = []
    start = time.monotonic()
    with (out / 'predictions.jsonl').open('w') as stream:
        for packet in packets:
            agent = DoctorAgent()
            state = agent.new_case('external-' + packet['id'], packet['text'])
            trace = []
            for _ in range(state.max_turns):
                action, _, differential = agent.decide(state)
                trace.append({'action': action.model_dump(),
                              'top5': [d.diagnosis for d in differential[:5]],
                              'safety_conditions': [f.condition for f in state.red_flags]})
                agent.observe(state, action, '' if action.action_type == 'DIAGNOSE'
                              else metadata['response_policy'])
                if action.action_type == 'DIAGNOSE':
                    break
            result = {'id': packet['id'], 'final_diagnosis': state.final_diagnosis,
                      'turns': state.turn_count, 'real_llm_calls': state.llm_call_count,
                      'trace': trace}
            predictions.append(result)
            stream.write(json.dumps(result, ensure_ascii=False) + '\n'); stream.flush()
            print(json.dumps({k: result[k] for k in ('id', 'final_diagnosis', 'turns')}), flush=True)
    if runtime_digest(ROOT) != before:
        raise RuntimeError('Runtime changed during evaluation')
    # Score only after every prediction has been written.
    gold = {str(r['id']): r['Final Diagnosis'] for r in records}
    scores = [{'id': p['id'], 'gold': gold[p['id']], 'prediction': p['final_diagnosis'],
               'exact_match': bool(p['final_diagnosis']) and normalize(p['final_diagnosis']) == normalize(gold[p['id']])}
              for p in predictions]
    summary = {'cases': len(scores), 'exact_matches': sum(s['exact_match'] for s in scores),
               'real_llm_calls': sum(p['real_llm_calls'] for p in predictions),
               'elapsed_seconds': round(time.monotonic() - start, 2), 'results': scores}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
