#!/usr/bin/env python3
"""Frozen information-availability stress protocol over 230 historical dev cases.

1,150 encounters = 230 base cases x FIVE substantive observation conditions.
NOT 1,150 independent medical vignettes, NOT a fresh blind set. No reference-only
imports. The SDK path, including arbitration, closing and SOAP, actually runs.
Doctor is scripted and offers no diagnostic answer: accuracy measures the engine
fallback, not gpt-oss-20b. Gold labels never enter runtime or Doctor messages.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / 'submission'))
os.environ['NOVA_LLM_PROVIDER'] = 'mock'
os.environ['NOVA_COMPETITION_RETRIEVAL'] = '1'
os.environ['NOVA_PRELIMINARY_RULES'] = '1'
MODES = ('complete', 'unscripted_unknown', 'exam_unavailable', 'history_unavailable', 'opening_disclosure')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def protocol():
    from scripts.evaluate_preliminary_benchmark import SUITES, _load
    cases = [c for s in SUITES for c in _load(s)]
    cases.sort(key=lambda c: hashlib.sha256(('clinical-quality-v36:' + c.case_id).encode()).hexdigest())
    counts = (int(len(cases)*.6), int(len(cases)*.8))
    rows = []
    for i, c in enumerate(cases):
        split = 'dev' if i < counts[0] else 'validation' if i < counts[1] else 'holdout'
        for mode in MODES:
            rows.append({'base': c.model_dump(), 'mode': mode, 'split': split,
                         'id': c.case_id + ':' + mode, 'base_hash': digest(c.model_dump())})
    return {'schema': 'clinical-quality-v36', 'label': 'LOCAL RUBRIC PROXY — NOT OFFICIAL SCORE',
            'historical_development_sources': True, 'independent_clinical_validation': False,
            'fresh_blind': False, 'base_cases': len(cases), 'encounters': len(rows),
            'split_counts': dict(Counter(r['split'] for r in rows)), 'modes': list(MODES),
            'interpretation': 'Grouped by base case before evaluation; historical case-author exposure remains. '
                              'All five variants stay together; no age/name/paraphrase multiplication.',
            'case_payload_sha256': digest(rows), 'cases': rows}


class ScriptedClient:
    timeout = 240
    def __init__(self, case, mode):
        self.case, self.mode = case, mode
        self.turns = 0; self.key = ''; self.kind = ''; self.events = []; self.store = {}
        self.record = {}; self.diagnosis = ''; self.disclosed = set()
        self.opening = case.chief_complaint
        if mode == 'opening_disclosure':
            for key in ('onset', 'medication', 'allergy', 'past_medical_history'):
                value = case.answers.get(key, '')
                # A bare denial needs its actual question context. Never append
                # an unqualified "No" to an unrelated chief complaint.
                from nova_agent.state import answer_kind
                if value and answer_kind(value) is None:
                    self.opening += '\n' + value
                    self.disclosed.add(key)

    def session(self):
        return {'initial': {'opening': self.opening, 'vital_signs': self.case.exam_results.get('vital_signs', '')},
                'turns_remaining': 50, 'deadline': (datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(),
                'available_actions': ['SAY','EXAM','DIAGNOSE']}

    def say(self, text, request_id):
        if request_id in self.store: return self.store[request_id]
        default = '잘 모르겠어요.' if self.mode in {'unscripted_unknown','history_unavailable'} else self.case.default_answer
        value = self.case.answers.get(self.key, default)
        if self.mode == 'history_unavailable' and self.key.partition(':')[0] in {'associated_symptoms','past_medical_history'}:
            value = '잘 모르겠어요.'
        if self.key in {'explanation','plan_explanation'}: value = '알겠습니다.'
        self.turns += 1
        self.events.append(('SAY', self.key, text, value))
        row = {'content': value, 'turn': self.turns, 'turns_remaining': 50-self.turns}
        self.store[request_id] = row
        return row

    def exam(self, text, request_id):
        if request_id in self.store: return self.store[request_id]
        self.turns += 1
        if self.mode == 'exam_unavailable':
            import nova_sdk
            self.events.append(('EXAM',self.key,text,'REJECTED'))
            raise nova_sdk.NovaError('EXAM_NOT_RECOGNIZED', 422)
        value = self.case.exam_results.get(self.key, self.case.default_exam_result)
        self.events.append(('EXAM',self.key,text,value))
        row = {'result': value, 'turn': self.turns, 'turns_remaining': 50-self.turns}
        self.store[request_id] = row
        return row

    def chat(self, messages, request_id, **kwargs):
        system = messages[0]['content']
        if '"questions"' in system:
            value = {'questions': [{'text':'현재 복용 중인 약이 있나요?','category':'medication'},
                                   {'text':'약물 알레르기가 있나요?','category':'allergy'}], 'differential':[], 'exams':[]}
        elif '바꿀 질문' in messages[-1]['content']:
            # Preserve the actual asked feature without a translation oracle.
            return {'choices':[{'message':{'content':messages[-1]['content'].split('바꿀 질문:')[-1].strip()}}]}
        else: value = {'primary_diagnosis':'undetermined','evidence':[], 'differential':[]}
        return {'choices':[{'message':{'content':json.dumps(value, ensure_ascii=False)}}]}

    def diagnose(self, note, diagnosis, request_id):
        self.record, self.diagnosis = note, diagnosis
        return {'status':'completed'}


def worker(row):
    from evaluation.cases import SyntheticCase
    from competition.nova_sdk_adapter import OfficialEncounter
    from nova_agent.diagnosis_normalizer import same_diagnosis
    from nova_agent.state import answer_kind
    from evaluation.clinical_label_identity import same_label
    case = SyntheticCase(**row['base'])
    client = ScriptedClient(case, row['mode'])
    e = OfficialEncounter(client, {}, sleep=lambda _:None, log=lambda _:None)
    # The deterministic patient uses the action key actually emitted by the
    # agent, as the legacy simulator does. It does not inspect candidate labels.
    for method in ('say','exam'):
        original = getattr(e, method)
        def wrapped(text, category, original=original):
            client.key = category
            return original(text, category)
        setattr(e, method, wrapped)
    started = time.monotonic()
    result = e.run()
    ddx = list(e.pstate.current_differential)
    correct = same_diagnosis(client.diagnosis, case.ground_truth_diagnosis)
    scored = case.scoring_expected and row['mode'] not in {'exam_unavailable','history_unavailable'}
    history = [x for x in client.events if x[0]=='SAY' and x[1] not in {'explanation','plan_explanation'}]
    actions = [(x[0], x[1]) for x in client.events]
    known_reask = sum(x[1] in client.disclosed for x in history)
    successful = sum(answer_kind(x[3]) != 'unknown' for x in history)
    required = set(case.answers)
    elicited = {x[1] for x in history if answer_kind(x[3]) != 'unknown'} | client.disclosed
    coverage = len(required & elicited)/len(required) if required else 1.0
    said = [t.text for t in e.turns if t.category in {'explanation','plan_explanation'} and t.ok]
    urgency = '응급' in client.record['P']['disposition']
    critical = case.critical
    rule_errors = sum(len(x[2])>30 for x in client.events) + int(client.turns>50) + bool(client.record['O']['tests'])
    next_step = bool(client.record['P']['tests'])
    interval = bool(re.search(r'즉시|\d+.*(?:주|일|개월)|수일',client.record['P']['follow_up']))
    spoken_interval = any(re.search(r'즉시|\d+.*(?:주|일|개월)', x) for x in said)
    duplicate = len(actions)-len(set(actions))  # closing excluded below
    qkeys = [x[1] for x in history]
    dangerous_primary=any(d.dangerous_if_missed and same_label(client.diagnosis,d.diagnosis) for d in ddx)
    return {'id':row['id'],'base_id':case.case_id,'split':row['split'],'mode':row['mode'],
            'scored':scored,'critical':critical,'top1':correct,
            'top3':correct or any(same_diagnosis(d.diagnosis,case.ground_truth_diagnosis) for d in ddx[:3]),
            'top5':correct or any(same_diagnosis(d.diagnosis,case.ground_truth_diagnosis) for d in ddx[:5]),
            'primary':client.diagnosis,'dangerous_primary':dangerous_primary,
            'differential_names':[d.diagnosis for d in ddx[:5]],'status':result['status'],'turns':client.turns,
            'asks':len(history),'exams':sum(x[0]=='EXAM' for x in client.events),
            'doctor_requests':e.stats.calls,'coverage_proxy':coverage,'answered_questions':successful,
            'duplicate_questions':len(qkeys)-len(set(qkeys)),'known_fact_reasks':known_reask,
            'disclosed_facts':len(client.disclosed),'urgent':urgency,'rule_errors':int(rule_errors),
            'plan_has_test':next_step,'plan_has_interval':interval,'spoken_has_interval':spoken_interval,
            'closing_turns':len(said),'education_records_actual_say':all(s in client.record['P']['education'] for s in said),
            'fixture_wall_seconds':time.monotonic()-started}


def summary(rows):
    n=len(rows); scored=[r for r in rows if r['scored']]; critical=[r for r in scored if r['critical']]
    rate=lambda rs,k:sum(bool(r[k]) for r in rs)/len(rs) if rs else None
    mean=lambda key:statistics.mean(r[key] for r in rows)
    turns=sorted(r['turns'] for r in rows)
    # Explicit process indicators only; NEVER convert into an official score.
    rubric={'information_gathering':25*mean('coverage_proxy'),
            'diagnostic_reasoning':15*rate(scored,'top1') if scored else None,
            'tests_followup':10*statistics.mean((r['plan_has_test']+r['plan_has_interval'])/2 for r in rows),
            'safety':15*statistics.mean(not r['rule_errors'] and (not r['critical'] or r['urgent']) for r in scored) if scored else None,
            'communication':15*statistics.mean((bool(r['closing_turns'])+r['spoken_has_interval']+r['education_records_actual_say'])/3 for r in rows),
            'efficiency':20*statistics.mean(r['turns']<=40 and r['doctor_requests']<=16 for r in rows)}
    rubric['total']=sum(v for v in rubric.values() if v is not None)
    return {'cases':n,'scored':len(scored),'rubric_process_proxy':rubric,
            'top1':rate(scored,'top1'),'top3':rate(scored,'top3'),'top5':rate(scored,'top5'),
            'critical_recall':rate(critical,'top1'),'critical_misses':sum(not r['top1'] for r in critical),
            'undertriage_proxy':sum(not r['urgent'] for r in critical),
            'overtriage_proxy':sum(r['urgent'] for r in scored if not r['critical']),
            'mean_turns':mean('turns'),'median_turns':statistics.median(turns),'p90_turns':turns[min(n-1,int(.9*n))],
            'mean_doctor_requests':mean('doctor_requests'),'mean_exams':mean('exams'),
            'duplicate_question_rate':sum(r['duplicate_questions'] for r in rows)/max(1,sum(r['asks'] for r in rows)),
            'known_fact_reask_rate':sum(r['known_fact_reasks'] for r in rows)/max(1,sum(r['asks'] for r in rows)),
            'dangerous_false_primary_rate':(sum(r.get('dangerous_primary',False) and not r['top1'] for r in scored)/len(scored)
                                            if scored and all('dangerous_primary' in r for r in scored) else None),
            'rule_errors':sum(r['rule_errors'] for r in rows),'real_tokens_latency_cost':None,
            'fixture_wall_seconds':sum(r['fixture_wall_seconds'] for r in rows)}


def rescore(result, data):
    """Display labels may be Korean (English); use the established evaluator.

    Recalculates solely from captured output, never changes a gold label or
    replays a patient. Kept explicit for audits of already captured traces.
    """
    from evaluation.clinical_label_identity import same_label
    expected={r['id']:r['base']['ground_truth_diagnosis'] for r in data['cases']}
    for r in result['cases']:
        r['top1']=same_label(r['primary'], expected[r['id']])
        names=r.get('differential_names')
        r['top3']=r['top1'] or (any(same_label(v,expected[r['id']]) for v in names[:3]) if names else r['top3'])
        r['top5']=r['top1'] or (any(same_label(v,expected[r['id']]) for v in names[:5]) if names else r['top5'])
    result['metrics']=summary(result['cases'])
    result['by_mode']={m:summary([r for r in result['cases'] if r['mode']==m]) for m in MODES
                       if any(r['mode']==m for r in result['cases'])}
    result['rescore_note']='Stable evaluation-only exact catalog identity handles bilingual display labels and duplicate catalog names; no gold label changes. Same comparator used for BEFORE and AFTER.'
    result['scorer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze');p.add_argument('--protocol');p.add_argument('--output')
    p.add_argument('--rescore',help='Recompute only label normalization and summary from captured output')
    p.add_argument('--split',choices=['dev','validation','holdout','all'],default='dev')
    p.add_argument('--workers',type=int,default=2);p.add_argument('--limit',type=int)
    a=p.parse_args()
    if a.freeze:
        path=Path(a.freeze)
        if path.exists(): raise SystemExit('Protocol already frozen; refusing overwrite')
        path.write_text(json.dumps(protocol(),ensure_ascii=False,indent=2)+'\n');return
    data=json.loads(Path(a.protocol).read_text())
    assert digest(data['cases'])==data['case_payload_sha256']
    if a.rescore:
        captured=json.loads(Path(a.rescore).read_text())
        Path(a.output).write_text(json.dumps(rescore(captured,data),ensure_ascii=False,indent=2)+'\n')
        return
    from scripts.runtime_identity import tracked_runtime_hashes
    runtime = tracked_runtime_hashes(ROOT)
    rows=[r for r in data['cases'] if a.split=='all' or r['split']==a.split]
    if a.limit: rows=rows[:a.limit]
    output=[];started=time.monotonic()
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for result in pool.map(worker, rows, chunksize=1):
            output.append(result)
            if len(output)%25==0: print(f'{len(output)}/{len(rows)} elapsed={time.monotonic()-started:.0f}s',flush=True)
    result={'label':data['label'],'protocol_sha256':hashlib.sha256(Path(a.protocol).read_bytes()).hexdigest(),
            'runtime_sha256':runtime,'runtime_unchanged_during_execution':runtime==tracked_runtime_hashes(ROOT),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'model':'SCRIPTED DOCTOR WITHOUT DIAGNOSTIC ANSWERS; not fixed real model',
            'limitations':['Historical development data, not independent/fresh blind validation',
                          'Coverage counts scripted answer categories, not clinician adjudicated information gain',
                          'Critical flag approximates triage; non-critical does not mean emergency referral is inappropriate',
                          'Efficiency uses disclosed thresholds, not the official efficiency rubric',
                          'SDK fake patient responds to agent action keys; no natural-language patient-model test',
                          'Information-withheld variants excluded from diagnostic accuracy'],
            'metrics':summary(output),'by_mode':{m:summary([r for r in output if r['mode']==m]) for m in MODES if any(r['mode']==m for r in output)},'cases':output}
    result=rescore(result,data)
    assert result['runtime_unchanged_during_execution'], 'Runtime changed during evaluation; discard mixed run'
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result['metrics'],ensure_ascii=False))


if __name__=='__main__':main()
