"""Invented observations, not leaderboard cases or clinical score estimates."""
import json

import pytest

from test_adaptive_encounter import Scenario, fresh, accept, proposal, run_new, engine_config, nova_sdk
from competition.encounter_contract import ledger, cited_facts, plan_issues
from competition.interview_coverage import (actual_coverage, question_identity,
    question_category, options, attempted, reply_status)
from nova_agent.clinical_interview import next_history_clarification, DETAIL_QUESTIONS


def replies(server, mapping):
    original = server.action
    def action(body):
        result = original(body)
        if body.get('content') in mapping:
            field = 'result' if body['action'] == 'EXAM' else 'content'
            result[field] = mapping[body['content']]
            server.events[-1] = (body['action'], body['content'], result[field])
        return result
    server.action = action


def ask(e, text):
    return e._send_planned({'kind':'SAY', 'text':text})


def test_two_symptom_onsets_are_acquired_and_recorded_as_hpi():
    e,s = fresh('기침이 나고 열이 있어요.')
    replies(s, {'기침은 언제부터 시작됐나요?':'기침은 일주일 전부터요.',
                '열은 언제부터 났나요?':'열은 어젯밤부터 났어요.'})
    for q in ('기침은 언제부터 시작됐나요?', '열은 언제부터 났나요?'):
        assert ask(e,q) is not None
    assert ask(e,'기침이 시작된 때는 언제인가요?') is None
    accept(e,dict(proposal(), evidence=['I0']))
    record,_ = e.official_record([],None)
    assert '일주일 전부터' in record['S']['hpi']
    assert '어젯밤부터' in record['S']['hpi']
    assert '언제부터' not in record['S']['ros']
    assert all(x['status'] == 'observed_reply' for x in actual_coverage(e))


def test_two_drug_doses_are_not_one_topic_and_true_duplicate_is_blocked():
    e,s = fresh('복용 중인 약에 대해 상담하고 싶어요.')
    replies(s, {'암로디핀은 몇 mg 드시나요?':'5mg입니다.',
                '로사르탄은 몇 mg 드시나요?':'50mg입니다.'})
    assert ask(e,'암로디핀은 몇 mg 드시나요?')
    assert ask(e,'로사르탄은 몇 mg 드시나요?')
    assert ask(e,'암로디핀을 몇 mg 드시나요?') is None
    assert len(e.turns) == 2


def test_comprehension_failure_is_not_evidence_and_allows_one_simple_rephrase():
    e,s = fresh('기침 때문에 왔어요.')
    replies(s, {'기침은 언제부터 시작됐나요?':'무슨 뜻인지 이해하지 못했어요.',
                '기침이 시작된 때는 언제인가요?':'일주일 전부터요.'})
    assert ask(e,'기침은 언제부터 시작됐나요?')
    assert actual_coverage(e)[0]['status'] == 'needs_rephrase'
    assert not cited_facts(['T1'],ledger(e))
    assert ask(e,'기침이 시작된 때는 언제인가요?')
    assert ask(e,'기침이 언제부터 있었나요?') is None
    assert cited_facts(['T2'],ledger(e))


@pytest.mark.parametrize('answer',['기억이 안 나요.', '잘 모르겠어요.', '말하고 싶지 않아요.'])
def test_unknown_or_refusal_never_triggers_comprehension_retry(answer):
    e,s = fresh('기침 때문에 왔어요.')
    replies(s, {'기침은 언제부터 시작됐나요?':answer})
    ask(e,'기침은 언제부터 시작됐나요?')
    assert ask(e,'기침이 시작된 때는 언제인가요?') is None
    assert not cited_facts(['T1'],ledger(e))


def test_vague_medication_class_gets_actual_name_clarification():
    e,s = fresh()
    question = '복용 중인 약 이름이 뭔가요?'
    detail = DETAIL_QUESTIONS['medication_name']
    replies(s,{question:'혈압약을 먹고 있어요.', detail:'암로디핀이에요.'})
    ask(e,question)
    follow = next_history_clarification(e.pstate,max_details=8)
    assert follow and follow[2] == detail
    assert ask(e,detail)
    assert not next_history_clarification(e.pstate,max_details=8)
    accept(e,proposal()); record,_ = e.official_record([],None)
    assert '암로디핀' in record['S']['pmh']


def test_growth_history_requests_date_and_height_separately():
    e,s = fresh('열 살 남자아이인데 키가 잘 안 커요.')
    chosen = [a for a in options(e.pstate) if a['topic'].startswith('growth_record_')]
    assert len(chosen) == 2
    replies(s, {chosen[0]['text']:'작년 10월이요.',chosen[1]['text']:'125cm였어요.'})
    assert all(e._send_planned(a) is not None for a in chosen)
    assert len(e.turns) == 2 and all(t.ok for t in e.turns)
    assert not any('날짜와' in t.text for t in e.turns)


def test_ros_history_and_exams_have_exact_observation_provenance():
    e,s = fresh('기침 때문에 왔어요.')
    mapping = {'기침은 언제부터 시작됐나요?':'지난주 월요일부터요.',
               '손끝이 저린가요?':'아니요.',
               '가족 중 질환이 있는 분이 있나요?':'어머니가 천식이 있어요.',
               '평소 어떤 일을 하시나요?':'목공 일을 해요.',
               '폐를 청진하겠습니다':'오른쪽 하부에서 수포음이 들립니다.'}
    replies(s,mapping)
    for text in mapping:
        assert e._send_planned({'kind':'EXAM' if '청진' in text else 'SAY', 'text':text})
    accept(e,dict(proposal(),evidence=['I0']))
    record,_ = e.official_record([],None)
    assert '지난주 월요일' in record['S']['hpi']
    assert '손끝이 저린가요? → 아니요' in record['S']['ros']
    assert '어머니가 천식' in record['S']['fh']
    assert '목공' in record['S']['sh']
    assert '오른쪽 하부에서 수포음' in record['O']['exam']
    assert record['O']['tests'] == ''
    # Every observed answer is in its actual S/O record, not a model summary.
    serialized = json.dumps({'S':record['S'],'O':record['O']},ensure_ascii=False)
    assert all(answer in serialized for answer in mapping.values())


def test_long_unknown_diagnosis_is_spoken_in_full_not_replaced_by_generic_text():
    e,s = fresh()
    name = '매우 길게 표현된 환자별 임상 작업 진단명으로 아직 추가 평가가 필요한 상태'
    p = proposal(); p.update(primary_diagnosis=name,short_name='다른 병')
    accept(e,p); e._explain([],None)
    said = [t.text for t in e.turns if t.category == 'explanation']
    assert name in ''.join(said)
    assert '다른 병' not in said
    assert all(len(t.text) <= 30 for t in e.turns)


def test_treatment_and_result_branches_are_spoken_and_recorded_before_feedback():
    e,s = fresh(); p = proposal()
    p['plan']['treatment'] = '감염이 확인되면 약물 치료를 정해요. 약물 알레르기를 먼저 확인해요. 물을 적절히 마셔요.'
    p['plan']['tests'][0].update(if_abnormal='감염이면 치료를 조정해요',
                               if_normal='정상이어도 지속되면 재평가해요')
    accept(e,p); e._explain([],None); record,_ = e.official_record([],None)
    said = [t.text for t in e.turns]
    for text in ('감염이 확인되면 약물 치료를 정해요','약물 알레르기를 먼저 확인해요',
                 '물을 적절히 마셔요','정상이어도 지속되면 재평가해요'):
        assert text in said and text in json.dumps(record['P'],ensure_ascii=False)
    assert said.index('정상이어도 지속되면 재평가해요') < next(i for i,t in enumerate(e.turns) if t.category == 'understanding_check')
    assert len(e.turns) <= 24


def test_unspeakable_first_treatment_sentence_requires_repair():
    e,_ = fresh(); p = proposal()
    p['plan']['treatment'] = '매우 긴 치료 설명이므로 반드시 다시 작성해야 하는 중요한 첫 번째 치료 문장입니다. 쉬세요.'
    assert 'treatment_missing_unsafe_or_too_long' in plan_issues(p,ledger(e))


def test_full_encounter_acquires_facts_then_records_exams_and_delivers_plan():
    from test_v50_phased_encounter import Phased
    facts = {
        '기침은 언제부터 시작됐나요?':'지난주 월요일부터요.',
        '열은 언제부터 났나요?':'어제 저녁부터요.',
        '증상이 점점 심해지고 있나요?':'어제부터 기침이 더 심해졌어요.',
        '기침이 얼마나 심한가요?':'밤에 깰 정도예요.',
        '가래가 나오나요?':'누런 가래가 나와요.',
        '숨이 차나요?':'아니요.',
        '복용 중인 약 이름이 뭔가요?':'복용하는 약은 없어요.',
        '약물 알레르기가 있나요?':'아니요.',
        '진단받거나 치료 중인 병이 있나요?':'아니요.',
        '일상생활에 어떤 지장이 있나요?':'기침 때문에 수업을 쉬었어요.',
        '폐를 청진하겠습니다':'오른쪽 하부에서 수포음이 들립니다.',
        '호흡 양상을 살펴보겠습니다':'보조근 사용 없이 호흡합니다.',
        '가족 중 질환이 있는 분이 있나요?':'어머니가 천식이 있어요.',
        '평소 어떤 일을 하시나요?':'목공 일을 해요.',
        '담배를 피우시나요?':'아니요.',
        '주변에 비슷하게 아픈 사람이 있나요?':'직장 동료가 기침했어요.',
        '가슴에 통증이 있나요?':'아니요.',
        '기침할 때 피가 나오나요?':'아니요.',
    }
    s = Phased(opening='기침과 열 때문에 왔어요.')
    actions = [{'kind':'EXAM' if '겠습니다' in q else 'SAY','text':q} for q in facts]
    s.plans = [actions[i:i+6] for i in range(0,len(actions),6)] + [[]]
    s.final.update(primary_diagnosis='하부 호흡기 감염 의심', short_name='하부 호흡기 감염',
                   reason='관찰한 호흡기 증상의 추가 평가 필요', evidence=['I0'])
    # This plan only tests transport/record consistency, not clinical accuracy.
    replies(s,facts)
    e = run_new(s)
    assert 20 <= e._gather_end <= 25 and s.turns <= 49
    actual = [t for t in e.turns[:e._gather_end] if t.text in facts]
    assert len(actual) == len(facts), [(t.kind,t.text) for t in actual]
    content = json.dumps({'S':s.record['S'],'O':s.record['O']}, ensure_ascii=False)
    assert all(t.reply in content for t in actual)
    decision = next(x for x in s.inputs if x['phase'] == 'diagnosis')
    assert all(any(row.get('answer') == t.reply for row in decision['PATIENT_EVIDENCE']) for t in actual)
    assert sum(t.kind == 'EXAM' for t in actual) == 2
    assert s.record['O']['tests'] == ''
    assert any(t.category == 'understanding_check' for t in e.turns)
    assert any(t.category == 'patient_questions' for t in e.turns)
