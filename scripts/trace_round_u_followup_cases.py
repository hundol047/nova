#!/usr/bin/env python3
"""Round U follow-up: per-case stage trace under the PRELIMINARY rules (SAY / EXAM / DIAGNOSE, no TEST).

Runs one development case through the submission adapter path (NovaCompetitionAgent(preliminary=True), mock
LLM, competition retrieval) exactly like evaluation/preliminary_driver.run_episode, and records for every turn:
whether the labelled diagnosis was retrieved (Top150), in the diagnostic Top25 rerank, in the active
differential, its support/contradictions, the action candidates the selector generated, the selected action,
and at the end the final-decision reasons, disposition-relevant SOAP plan and observed facts. The truth label is
used only AFTER each decision to locate the labelled candidate; it is never passed to the agent.

    python scripts/trace_round_u_followup_cases.py --cases Fresh05,ValP_10 --output artifacts/.../traces.json
"""
import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('NOVA_LLM_PROVIDER', 'mock')
os.environ.setdefault('NOVA_COMPETITION_RETRIEVAL', '1')

SOURCES = [('evaluation.validation_cases_round_p', 'VALIDATION_CASES_ROUND_P'),
           ('evaluation.generalization_dev_cases_round_m', 'ROUND_M_CASES'),
           ('evaluation.generalization_dev_cases_round_j', 'ROUND_J_CASES'),
           ('evaluation.generalization_dev_cases_round_i', 'ROUND_I_CASES'),
           ('evaluation.preliminary_dev_cases', 'PRELIM_KO_CASES'),
           ('evaluation.cases', 'CASES'),
           ('evaluation.dev_cases_round_q', 'DEV_CASES_ROUND_Q')]
JSON_SOURCES = sorted(str(p) for p in (ROOT / 'evaluation').glob('frozen_validation_round_*.json')) + \
    [str(ROOT / 'evaluation/acceptance_regressions_round_r.json')]


def find_case(case_id, extra_json=()):
    import importlib
    from evaluation.cases import SyntheticCase
    for module, var in SOURCES:
        for c in getattr(importlib.import_module(module), var):
            if c.case_id == case_id:
                return c, []
    for path in [*JSON_SOURCES, *extra_json]:
        try:
            rows = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            continue
        for raw in rows if isinstance(rows, list) else []:
            if raw.get('case_id') == case_id:
                raw = {k: v for k, v in raw.items() if k not in ('audit_expect', 'round_s_expect')}
                reject = raw.pop('audit_rejected_exams', [])
                return SyntheticCase(**raw), reject
    raise KeyError(case_id)


def trace(case_id, extra_json=(), unscripted_unknown=False):
    from nova_agent.config import get_config
    get_config(reload=True)
    from competition.adapter import NovaCompetitionAgent
    from evaluation.preliminary_driver import Environment, run_episode
    from nova_agent.diagnosis_normalizer import same_diagnosis
    from nova_agent.llm_client import MockLLMClient
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent import retrieval_pipeline as rp
    from nova_agent import missing_info as mi
    from nova_agent.final_decision import support_problems
    case, reject = find_case(case_id, extra_json)
    agent = NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()), preliminary=True)
    truth = case.ground_truth_diagnosis
    turns = []
    decide = agent.agent.decide
    orig_retrieve, orig_rerank, orig_analyze = rp.retrieve_high_recall, rp.lightweight_rerank, mi.MissingInformationAnalyzer.analyze

    def is_truth(cid, name=''):
        return same_diagnosis(cid, truth) or (name and same_diagnosis(name, truth))

    def traced(state):
        cap = {'retrieved': [], 'reranked': [], 'watch': [], 'actions': []}

        def retrieve(*a, **kw):
            r = orig_retrieve(*a, **kw)
            cap['retrieved'] = [(h.concept.concept_id, h.concept.canonical_name) for h in r]
            return r

        def rerank(*a, **kw):
            r = orig_rerank(*a, **kw)
            cap['reranked'] = [(h.concept.concept_id, h.concept.canonical_name) for h in r]
            cap['watch'] = [(h.concept.concept_id, h.concept.canonical_name) for h in getattr(r, 'safety_watch', ())]
            return r

        def analyze(self, *a, **kw):
            r = orig_analyze(self, *a, **kw)
            cap['actions'] = [dict(type=x.action_type, key=x.key, priority=round(getattr(x, 'priority', 0) or 0, 3),
                                   discriminates=list(getattr(x, 'disease_ids_discriminated', []) or [])[:6]) for x in r][:12]
            return r

        with patch.object(rp, 'retrieve_high_recall', retrieve), patch.object(rp, 'lightweight_rerank', rerank), \
                patch.object(mi.MissingInformationAnalyzer, 'analyze', analyze):
            action, scored, diff = decide(state)
        rrank = next((i for i, (c, n) in enumerate(cap['retrieved'], 1) if is_truth(c.removeprefix('core:'), n)), None)
        krank = next((i for i, (c, n) in enumerate(cap['reranked'], 1) if is_truth(c.removeprefix('core:'), n)), None)
        arank = next((i for i, d in enumerate(diff, 1) if is_truth(d.diagnosis_id, d.diagnosis)), None)
        top = [dict(id=d.diagnosis_id, name=d.diagnosis, score=round(d.score, 3), dangerous=d.dangerous_if_missed,
                    support=list(d.supporting_evidence), against=list(d.contradictory_evidence), missing=list(d.missing_discriminative_evidence)[:6],
                    problems=support_problems(d, state, diff)) for d in diff[:6]]
        tr = next((d for d in diff if is_truth(d.diagnosis_id, d.diagnosis)), None)
        turns.append(dict(turn=state.turn_count + 1, action=dict(type=action.action_type, key=action.key,
                                                                    text=getattr(action, 'question', None) or getattr(action, 'text', None)),
                          retrieval_ran=bool(cap['retrieved']), truth_top150=rrank, truth_rerank_top25=krank,
                          truth_in_safety_watch=any(is_truth(c.removeprefix('core:'), n) for c, n in cap['watch']),
                          truth_active_rank=arank,
                          truth_support=list(tr.supporting_evidence) if tr else None,
                          truth_problems=support_problems(tr, state, diff) if tr else None,
                          top=top, candidate_actions=cap['actions'],
                          completion_reason=getattr(state, 'completion_reason', None)))
        return action, scored, diff

    with patch.object(agent.agent, 'decide', traced):
        ep = run_episode(case, agent=agent, env=Environment(unsupported_exams=frozenset(reject), unscripted_unknown=unscripted_unknown))
    final = ep.wire[-1]
    md = final.get('metadata') or {}
    state = agent.agent.state if hasattr(agent.agent, 'state') else None
    first = next((t for t in turns if t['retrieval_ran']), {})
    return dict(case_id=case.case_id, truth=truth, critical=getattr(case, 'critical', None), scored=case.scoring_expected,
                chief_complaint=case.chief_complaint, scripted_answers=case.answers, scripted_exams=case.exam_results,
                result=ep.result, primary_key=md.get('key'), final_decision=md.get('final_decision'),
                soap=final.get('soap'), wire_actions=[(w.get('action_type'), w.get('key') or (w.get('text') or '')[:60])
                                                     for w in ep.wire],
                chief_only=dict(top150=first.get('truth_top150'), rerank_top25=first.get('truth_rerank_top25'),
                                active=first.get('truth_active_rank')),
                final_stage=dict(top150=turns[-1]['truth_top150'], rerank_top25=turns[-1]['truth_rerank_top25'],
                                 active=turns[-1]['truth_active_rank'], support=turns[-1]['truth_support'],
                                 problems=turns[-1]['truth_problems']),
                turns=turns)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cases', required=True)
    p.add_argument('--extra-json', action='append', default=[])
    p.add_argument('--output', required=True)
    p.add_argument('--unscripted-unknown', action='store_true')
    a = p.parse_args()
    out = [trace(c, a.extra_json, a.unscripted_unknown) for c in a.cases.split(',')]
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str) + '\n')
    for r in out:
        print(r['case_id'], 'truth', r['truth'], '->', r['primary_key'], 'top1' if r['result'].get('top1') else 'WRONG',
              'chief', r['chief_only'], 'final', {k: v for k, v in r['final_stage'].items() if k != 'support'},
              'I=', r['result'].get('interactions'))


if __name__ == '__main__':
    main()
