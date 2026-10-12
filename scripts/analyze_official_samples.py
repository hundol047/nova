#!/usr/bin/env python3
"""Credential-free analysis. Clinical quality requires explicit human annotations.

No public reference diagnoses enter inference. Raw responses are read locally;
outputs contain analytical counts/enums, never dialogue, keys or session IDs.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.official_result_tools import LABEL, distribution, safe_files, redact

CATEGORIES=dict(zip('ABCDEFGHIJKLM',[
 'useful new discriminator','duplicate/redundant','clinically irrelevant','malformed','hallucinated fact',
 'unsafe recommendation','overly broad question','invalid EXAM','supported diagnosis correction',
 'unsupported diagnosis override','useful guideline use','prompt-injection susceptibility','empty/truncated']))
# Post-encounter analysis only. Topic checks are not clinical adjudication.
ACCEPTANCE={
 'C01':{'drug_name':r'zolpidem|졸피뎀|수면제','dose':r'\d+\s*(?:mg|밀리그램|알|정)',
 'frequency':r'daily|nightly|times|하루|매일|회|번','duration':r'years?|months?|년|개월',
 'tolerance_escalation':r'toleran|increas|escalat|내성|증량','withdrawal_dependence':r'withdraw|depend|금단|의존',
 'daytime_impairment':r'daytime|sleepy|drows|낮|졸|기억'},
 'C03':{'longitudinal_growth':r'growth|height|성장|키','growth_velocity':r'velocity|per year|속도|일년에|연간',
 'nutrition':r'nutrit|diet|eat|영양|식사','birth_history':r'birth|born|출생|태어',
 'family_height':r'family|mother|father|가족|부모|어머니|아버지','parental_puberty':r'pubert|사춘기',
 'chronic_symptoms':r'chronic|diarrhea|fatigue|만성|설사|피로','pubertal_context':r'pubert|tanner|사춘기|이차성징',
 'physical_exam':r'EXAM'},
 'C10':{'weight_change':r'weight|체중','appetite':r'appetite|식욕','heat_intolerance':r'heat|더위',
 'sweating':r'sweat|땀','palpitations':r'palpitat|두근','tremor':r'tremor|shak|떨',
 'bowel_changes':r'bowel|stool|diarrhea|배변|설사','menstrual_if_relevant':r'menstru|period|월경|생리',
 'thyroid_exam':r'thyroid|갑상','eye_signs':r'eye|눈|안구','neuro_if_relevant':r'neuro|reflex|신경|반사'}}
REFERENCE={ 'C01':r'sedative|hypnotic use|수면제.*의존', 'C03':r'constitutional.*growth|체질성.*성장',
            'C10':r'graves|그레이브스' }
UNKNOWN=re.compile(r'not sure|unknown|don.t know|모르|미확인|잘 몰라',re.I)


def parsed(text):
    if not isinstance(text,str):return None
    try:
        value=json.loads(text.strip().removeprefix('```json').removesuffix('```'))
        return value if isinstance(value,dict) else None
    except ValueError:return None


def analyze(rows, annotations=None):
    annotations=annotations or {};quality=[];samples=[];latency=[];exam=[];identities=[];grounding=[]
    for row in rows:
        case=row.get('case') if row.get('case') in ACCEPTANCE else 'UNMAPPED'
        events=row.get('events',[]);events=events if isinstance(events,list) else []
        chats=[e for e in events if isinstance(e,dict) and e.get('operation')=='chat']
        effects={e.get('request_number'):e for e in events if isinstance(e,dict) and e.get('operation')=='doctor_effect'}
        tokens=Counter();times=[];known_models=[];revision_exposed=False;revisions=set();usage_complete=0;valid=0;diagnostic=0;empty=0
        seen=set();classes=[]
        for e in chats:
            response=e.get('response') or {};response=response if isinstance(response,dict) else {}
            choices=response.get('choices') or []
            first=choices[0] if isinstance(choices,list) and choices and isinstance(choices[0],dict) else {}
            message=first.get('message') or {};text=message.get('content','') if isinstance(message,dict) else ''
            value=parsed(text);is_reasoning=e.get('purpose')!='phrasing'
            if is_reasoning:valid+=value is not None
            trunc=e.get('error_code')=='PROVIDER_RESPONSE_INVALID' or bool(e.get('success') and (first.get('finish_reason')=='length' or not isinstance(text,str) or not text.strip()))
            empty+=trunc
            model=response.get('model');known_models.append(model=='openai/gpt-oss-20b')
            revision_exposed|=any(response.get(k) is not None for k in ('revision','model_revision','model_sha'))
            for k in ('revision','model_revision','model_sha'):
                v=response.get(k)
                if isinstance(v,str) and re.fullmatch(r'[a-fA-F0-9]{40}|[a-fA-F0-9]{64}',v):revisions.add(v.lower())
            usage=response.get('usage') or {}
            if isinstance(usage,dict):
                for k in ('prompt_tokens','completion_tokens','total_tokens'):
                    n=usage.get(k)
                    if isinstance(n,int) and not isinstance(n,bool) and n>=0:tokens[k]+=n
                if all(isinstance(usage.get(k),int) and not isinstance(usage[k],bool) and usage[k]>=0 for k in ('prompt_tokens','completion_tokens')):
                    usage_complete+=1
                    if not isinstance(usage.get('total_tokens'),int):tokens['total_tokens']+=usage['prompt_tokens']+usage['completion_tokens']
            t=e.get('api_latency_seconds',e.get('latency_seconds'))
            if isinstance(t,(int,float)) and t>=0:times.append(t)
            effect=effects.get(e.get('request_number'),{})
            structural=bool(is_reasoning and value and not trunc and e.get('success') and
                            e.get('diagnostic_response_shape') is True)
            diagnostic+=structural
            flags={code:'MANUAL_REVIEW_REQUIRED' for code in CATEGORIES}
            flags['D']='DETECTED' if is_reasoning and not value and not trunc else 'NOT_DETECTED'
            flags['M']='DETECTED' if trunc else 'NOT_DETECTED'
            duplicate=isinstance(text,str) and bool(text.strip()) and text in seen
            flags['B']='DETECTED' if duplicate else 'NOT_DETECTED_BY_EXACT_MATCH'
            if isinstance(text,str) and text.strip():seen.add(text)
            if value and isinstance(value.get('questions'),list):
                broad=any(isinstance(q,str) and re.search(r'all symptoms|everything|모든 증상|전부|한꺼번|모두',q,re.I) for q in value['questions'])
                flags['G']='POTENTIAL_BROAD_QUESTION' if broad else 'NOT_DETECTED_BY_HEURISTIC'
            if value and isinstance(value.get('exams'),list):
                invalid=any(isinstance(x,str) and re.search(r'[,/]|\band\b|및|그리고|전신|전체|모두',x,re.I) for x in value['exams'])
                flags['H']='POTENTIAL_COMPOUND_EXAM' if invalid else 'NOT_DETECTED_BY_HEURISTIC'
            if 'primary_accepted' in effect:
                flags['J']='RUNTIME_REJECTED' if value and value.get('primary_diagnosis') and not effect['primary_accepted'] else 'NOT_DETECTED'
                flags['I']='RUNTIME_ACCEPTED_CORRECTION_REQUIRES_CLINICAL_REVIEW' if effect.get('primary_decision_kind')=='SUPPORTED_CORRECTION' else 'NOT_DETECTED'
            note=annotations.get(case,{}).get(str(e.get('request_number')), {})
            for code in CATEGORIES:
                if isinstance(note,dict) and isinstance(note.get(code),bool):flags[code]='HUMAN_YES' if note[code] else 'HUMAN_NO'
            classes.append({'request_number':e.get('request_number') if isinstance(e.get('request_number'),int) else None,
                            'purpose':e.get('purpose') if e.get('purpose') in ('phrasing','followup','final_consult','last_chance','reasoning') else 'UNKNOWN','json_parsed':value is not None,
                            'finish_reason':first.get('finish_reason') if first.get('finish_reason') in ('stop','length','content_filter','tool_calls') else 'NOT_EXPOSED_OR_UNKNOWN',
                            'structural_diagnostic_response':structural,'affected_reasoning':effect.get('affected_reasoning',False),
                            'categories':flags})
        reviewed=[c for c in classes if all(c['categories'][k] in ('HUMAN_YES','HUMAN_NO') for k in ('A','I','K'))]
        quality.append({'case':case,'calls':classes,'classification_is_clinical_adjudication':False,
                        'human_reviewed_calls':len(reviewed),
                        'useful_response_rate':sum(any(c['categories'][k]=='HUMAN_YES' for k in ('A','I','K')) for c in reviewed)/len(reviewed) if reviewed else None,
                        'redundant_response_rate_exact_match':sum(c['categories']['B']=='DETECTED' for c in classes)/len(classes) if classes else None,
                        'redundant_response_rate_human':sum(c['categories']['B']=='HUMAN_YES' for c in classes)/sum(c['categories']['B'] in ('HUMAN_YES','HUMAN_NO') for c in classes) if any(c['categories']['B'] in ('HUMAN_YES','HUMAN_NO') for c in classes) else None,
                        'valid_json_rate_reasoning_calls':valid/max(1,sum(e.get('purpose')!='phrasing' for e in chats)),
                        'diagnostic_reasoning_structural_rate':diagnostic/max(1,sum(e.get('purpose')!='phrasing' for e in chats)),
                        'empty_or_truncated_rate':empty/len(chats) if chats else None})
        latency.append({'case':case,'calls':len(chats),'chat_latency_seconds':distribution(times),'tokens':dict(tokens),
                        'mean_reported_total_tokens_per_call':tokens['total_tokens']/len(chats) if chats else None,
                        'token_usage_missing_calls':len(chats)-usage_complete,
                        'within_hard_caps':len(chats)<=200 and tokens['prompt_tokens']<=500000 and tokens['completion_tokens']<=100000 if usage_complete==len(chats) else None,
                        'phase_seconds':{op:sum(e.get('api_latency_seconds',e.get('latency_seconds',0)) or 0 for e in events if isinstance(e,dict) and e.get('operation')==op) for op in ('say','exam','chat','diagnose')},
                        'probe_overhead_seconds':sum(e.get('probe_latency_seconds',0) or 0 for e in events if isinstance(e,dict))})
        attempts=[e for e in events if isinstance(e,dict) and e.get('operation')=='exam']
        finals=[e for e in events if isinstance(e,dict) and e.get('operation')=='turn' and e.get('kind')=='EXAM']
        known_errors={'EXAM_NOT_SPECIFIC','EXAM_NOT_RECOGNIZED','CONTENT_TOO_LONG','EMPTY_CONTENT',
                      'PROVIDER_UNAVAILABLE','PROVIDER_RESPONSE_INVALID','API_UNAVAILABLE','SESSION_EXPIRED','SESSION_CLOSED'}
        errors=Counter(e.get('rejected') if e.get('rejected') in known_errors else 'OTHER_ERROR_VALUE_OMITTED' for e in finals if e.get('rejected'))
        deltas={}
        for e in events:
            if not isinstance(e,dict) or e.get('operation') not in ('exam','chat','say'):continue
            before=(e.get('server_before') or {}).get('turns_remaining');after=(e.get('server_after') or {}).get('turns_remaining')
            label=(e.get('error_code') if e.get('error_code') in known_errors else 'OTHER_ERROR_VALUE_OMITTED') if e.get('error_code') else e['operation']+'_success'
            if isinstance(before,int) and isinstance(after,int):deltas.setdefault(label,[]).append(before-after)
        exam.append({'case':case,'physical_attempts':len(attempts),'logical_exams':len(finals),'successful':sum(not e.get('rejected') for e in finals),
                     'errors':dict(errors),'rejection_rate':sum(errors.values())/len(finals) if finals else None,
                     'rejection_interpretation':'No rejections observed on these samples; rejected-turn semantics remain unmeasured' if finals and not errors else 'Naturally occurring requests only; no invalid probes',
                     'observed_server_turn_deltas':deltas,'ranking_causal_effect':'NOT ISOLATED; no extra diagnostic decisions performed for instrumentation'})
        exam[-1]['ranking_changes_observed']=[{'server_turn':e.get('server_turn') if isinstance(e.get('server_turn'),int) else None,
                                             'rank_changed':e.get('rank_changed') is True} for e in events if isinstance(e,dict) and e.get('operation')=='evidence_ranking' and e.get('kind')=='EXAM']
        diagnosis=next((e for e in reversed(events) if isinstance(e,dict) and e.get('operation')=='diagnose'),{})
        note=diagnosis.get('note') or {};so='\n'.join(str(v) for s in ('S','O') for v in (note.get(s) or {}).values()) if isinstance(note,dict) else ''
        observations=[e for e in events if isinstance(e,dict) and e.get('operation')=='turn' and not e.get('rejected') and e.get('category') not in ('explanation','plan_explanation')]
        answers=[e.get('reply') for e in observations if isinstance(e.get('reply'),str) and e['reply']]
        retained=sum(a in so for a in answers)
        evidence='\n'.join(str(e.get('text',''))+' → '+str(e.get('reply',''))+' '+str(e.get('kind','')) for e in observations if not UNKNOWN.search(str(e.get('reply',''))))
        checks={key:{'topic_observed_proxy':bool(re.search(pattern,evidence,re.I)),
                     'topic_retained_proxy':bool(re.search(pattern,so,re.I)),
                     'interpretation':'QA topic/answer presence proxy; confirm actual facts manually'} for key,pattern in ACCEPTANCE.get(case,{}).items()}
        samples.append({'case':case,'complete':row.get('status')=='completed','diagnose_success':diagnosis.get('success') is True,
                        'diagnostic_calls':diagnostic,'reference_diagnosis_match_heuristic':bool(re.search(REFERENCE.get(case,r'(?!)'),str(diagnosis.get('diagnosis','')),re.I)),
                        'acceptance_topics':checks,'observer_failures':row.get('observer_failures') if isinstance(row.get('observer_failures'),int) else None,
                        'mode':row.get('mode') if row.get('mode') in ('HUMAN_RUN','FIXTURE') else 'UNKNOWN'})
        grounding.append({'case':case,'noncommunication_replies':len(answers),'exact_reply_retention':retained/len(answers) if answers else None,
                          'unsupported_SO':'MANUAL REVIEW REQUIRED; no semantic truth guarantee','record_fields':sum(len(v) for v in note.values() if isinstance(v,dict)) if isinstance(note,dict) else None})
        identities.append({'case':case,'all_returned_models_expected':all(known_models) if known_models else False,
                           'MODEL_ID_RETURNED':'openai/gpt-oss-20b' if known_models and all(known_models) else 'MISSING_OR_UNEXPECTED_VALUE_OMITTED',
                           'ORGANIZER_DECLARED_REVISION':'4d7ae4984b7db7de8f8457170b3f1a419ee76d52',
                           'RUNTIME_REVISION_EXPOSED':revision_exposed,
                           'runtime_revision_returned':sorted(revisions),
                           'runtime_revision':'EXPOSED BUT NOT INDEPENDENTLY VERIFIED' if revision_exposed else 'NOT EXPOSED / NOT DIRECTLY VERIFIED'})
    unique=Counter(s['case'] for s in samples)
    targets={'all_three_unique':all(unique[c]==1 for c in ('C01','C03','C10')),
             'all_complete_and_diagnosed':bool(samples) and all(s['complete'] and s['diagnose_success'] for s in samples),
             'all_diagnostic_calls':bool(samples) and all(s['diagnostic_calls']>=1 for s in samples),
             'all_models_expected':bool(identities) and all(s['all_returned_models_expected'] for s in identities),
             'all_observations_captured':bool(samples) and all(s['observer_failures']==0 for s in samples)}
    rag=[{'case':row.get('case') if row.get('case') in ACCEPTANCE else 'UNMAPPED',
          'references_available':sum(len(e.get('references',[])) for e in row.get('events',[]) if isinstance(e,dict) and e.get('operation')=='guidelines'),
          'clinical_usefulness':'MANUAL REVIEW REQUIRED'} for row in rows]
    return {'label':LABEL,'origin_attestation':'USER-SUPPLIED CLAIM; not authenticated by this offline analyzer',
            'official_sample_summary':{'cases':samples,'target_checks':targets,'structural_targets_met':all(targets.values()),'clinical_quality':'NOT AUTOMATICALLY ADJUDICATED'},
            'doctor_quality':quality,'latency_tokens':latency,'exam_metrics':exam,
            'record_grounding':grounding,'model_identity':identities,'rag_metrics':{'cases':rag,'status':'Metadata availability only; actual guideline usefulness requires human review; full public-corpus topical suite is separate.'}}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--output',required=True);p.add_argument('--annotations');a=p.parse_args()
    annotations=json.loads(Path(a.annotations).read_text()) if a.annotations else None
    result=redact(analyze([row for _,row in safe_files(a.input)],annotations))
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Wrote analytical report; clinical classifications require human review.')

if __name__=='__main__':main()
