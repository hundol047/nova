"""Full packaged encounter against new synthetic patients and a SCRIPTED Doctor.

LOCAL RUBRIC PROXY — NOT OFFICIAL SCORE. No network/keys, no real-model
quality, latency or cost claims. Same fixtures can execute a baseline checkout.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.append(str(ROOT/'tests'))
from test_official_sdk_adapter import FakeServer,FakeClient,nova_sdk
from competition.nova_sdk_adapter import OfficialEncounter

COMMUNICATION = {'explanation','plan_explanation','understanding_check','patient_questions'}


def fixtures():
    cases = [
        {'id':'thyroid_midlife','opening':'44세 여자입니다. 식사량은 늘었는데 살이 빠져요.',
         'primary':'Graves disease','answers':{
          'appetite':'식욕이 늘었어요','heat':'더위를 못 견뎌요','sweat':'땀이 많아요','tremor':'손이 떨려요',
          'palpitations':'심장이 두근거려요','bowel':'묽은 변을 봐요','allergy':'약물 알레르기 없어요','med_name':'먹는 약 없어요'},
         'exams':{'thyroid':'양측 대칭성 미만성 비대(+), 결절(-), 압통(-)','eye':'안구 돌출(+)','tremor':'손 떨림(+)'},
         'questions':['더위를 견디기 어려우신가요?','가슴이 두근거리나요?'],'requested_exams':['갑상선을 촉진하겠습니다'],
         'required':['appetite','heat','palpitations','thyroid'],'urgent':False},
        {'id':'sleep_sedative','opening':'51세 여자입니다. 잠이 안 오고 낮에 졸려요.',
         'primary':'Sedative-Hypnotic Use Disorder','answers':{
          'med_name':'zopiclone을 복용해요','dose':'7.5mg씩 먹어요','frequency':'매일 밤 먹어요','duration':'8개월 복용해요',
          'tolerance':'같은 효과를 위해 용량을 늘려요','withdrawal':'약을 끊으면 잠이 더 안 오고 손이 떨려요',
          'daytime':'낮에 졸려서 일에 지장이 있어요','combined':'다른 진정제는 안 먹어요','allergy':'약물 알레르기 없어요'},
         'exams':{'thyroid':'갑상선 비대(-)','eye':'안구 돌출(-)','tremor':'손 떨림(-)'},
         'questions':['한 번에 몇 mg을 드시나요?','약을 줄이면 어떤 증상이 생기나요?'],'requested_exams':[],
         'required':['med_name','dose','frequency','duration','tolerance','withdrawal','daytime'],'urgent':False},
        {'id':'growth_school_age','opening':'9세 남아입니다. 또래보다 키가 작아요. 1년 전 키 121cm, 현재 키 127cm입니다.',
         'primary':'Constitutional growth delay','answers':{
          'parent_height':'아버지 키 176cm, 어머니 키 164cm입니다','parent_puberty':'아버지는 사춘기가 늦었어요',
          'birth':'출생 체중은 3.2kg입니다','nutrition':'식사는 규칙적이고 영양이 충분해요','chronic_gi':'만성 설사 없어요',
          'puberty':'아직 사춘기 변화는 없어요','allergy':'약물 알레르기 없어요'},
         'exams':{'height':'신장 127cm','weight':'체중 26kg','thyroid':'갑상선 비대(-)'},
         'questions':['부모님도 사춘기가 늦었나요?','설사가 오래 지속되나요?'],'requested_exams':[],
         'required':['parent_height','parent_puberty','nutrition','birth','height'],'urgent':False,'fail_final':True},
    ]
    # Same synthetic patients, newly explicit general-history response channels.
    # These are development fixtures, not independent or official case traces.
    for c in cases:
        c['answers'].update({'course':'증상은 비슷하게 지속돼요','medical_history':'기저질환 없어요',
            'family_illness':'관련 가족력 없어요','function':'일상생활이 조금 불편해요',
            'prior_care':'이 증상으로 진료받은 적 없어요','symptom_onset':'8개월 전부터요',
            'allergy':'약물 알레르기 없어요'})
        c['required'] += ['medical_history','family_illness','allergy','symptom_onset','course','function','prior_care']
    cases[0]['answers'].update({'weight_change':'7kg 줄었어요','menstrual':'생리 주기 변화 없어요'})
    cases[0]['required'] += ['weight_change','bowel','sweat','tremor','menstrual']
    cases[1]['answers'].update({'sleep_pattern':'자주 잠에서 깨요','sleep_hours':'4시간 자요',
                              'snoring':'코골이 없어요','caffeine':'커피는 하루 두 잔 마셔요'})
    cases[1]['required'] += ['sleep_pattern','sleep_hours','snoring','caffeine']
    cases[2]['answers']['med_name']='복용 약 없어요'
    return cases


def topic(text):
    for name,pattern in (
        ('birth',r'태어|출생'),('bowel',r'배변|bowel'),
        ('symptom_onset',r'언제부터|when.*start'),('course',r'점점.*심|경과|worsen'),
        ('medical_history',r'진단받.*병|과거.*병|병력|기저질환'),
        ('family_illness',r'가족.*(?:질환|병)|가족력'),
        ('function',r'일상.*지장'),('prior_care',r'이 증상.*진료'),
        ('sleep_pattern',r'잠들기|잠 유지'),('sleep_hours',r'몇 시간.*주무'),
        ('snoring',r'코골'),('caffeine',r'카페인|커피'),
        ('weight_change',r'체중.*(?:몇|얼마)'),('menstrual',r'생리|월경'),
        ('dose',r'몇\s*mg|용량|dose'),('frequency',r'몇\s*번|횟수|frequency'),
        ('duration',r'얼마나.*(?:드|복용)|복용.*기간'),('tolerance',r'같은 효과|내성|tolerance'),
        ('withdrawal',r'줄이면|끊으면|금단|withdraw'),('combined',r'다른.*진정제|병용'),
        ('med_name',r'약.*이름|복용 중인 약|먹는 약|medicat|medicine'),
        ('parent_height',r'부모.*키'),('parent_puberty',r'부모.*사춘기'),('puberty',r'사춘기'),
        ('birth',r'태어|출생'),('nutrition',r'식사|영양'),('chronic_gi',r'설사.*오래|만성.*설사'),
        ('appetite',r'식욕|appetite'),('heat',r'더위|heat'),('sweat',r'땀|sweat'),('tremor',r'떨|tremor'),
        ('palpitations',r'두근|palpitat'),('bowel',r'배변|bowel'),('daytime',r'낮.*(?:졸|활동)|daytime'),
        ('allergy',r'알레르기|allerg')):
        if re.search(pattern,text,re.I):return name
    return 'unmapped'


class Patient(FakeServer):
    def __init__(self,case):
        super().__init__();self.case=case;self.final_requests=0

    def session(self):
        row=super().session();row['initial']={'opening':self.case['opening'],'vital_signs':'BP 118/72, HR 88, RR 16, Temp 36.7, SpO2 98%'}
        return row

    def action(self,body):
        if body['action']=='DIAGNOSE':return super().action(body)
        rid=body['request_id']
        if rid in self.store:return self.store[rid]
        text=body['content'];kind=body['action'];self.turns+=1
        if kind=='SAY':value=self.case['answers'].get(topic(text),'잘 모르겠어요.')
        else:
            key=next((k for k,p in [('thyroid','갑상'),('eye','안구'),('tremor','떨림'),('height','신장'),('weight','체중')] if p in text),None)
            value=self.case['exams'].get(key,'경부 강직(-); 수포음(-/-), 천명음(-/-)')
        response={'status':'OK','turn':self.turns,'turns_remaining':50-self.turns,'content' if kind=='SAY' else 'result':value}
        self.events.append((kind,text,value));self.store[rid]=response;return response

    def chat(self,body):
        self.chat_calls+=1;system=body['messages'][0]['content']
        if '"questions"' in system:
            text=json.dumps({'differential':[{'name':self.case['primary']}],
                             'questions':self.case['questions'],'exams':self.case['requested_exams']},ensure_ascii=False)
        elif 'primary_diagnosis' in system:
            self.final_requests+=1
            if self.case.get('fail_final'):
                raise nova_sdk.NovaError('INVALID_API_RESPONSE' if self.final_requests==1 else 'REQUEST_PENDING',503)
            text=json.dumps({'primary_diagnosis':self.case['primary'],'short_name':'肺炎',
                             'evidence':list(self.case['answers'].values()),'urgent':self.case['urgent']},ensure_ascii=False)
        else:
            text=body['messages'][-1]['content'].split('바꿀 질문:')[-1].strip()
        return {'model':'openai/gpt-oss-20b','choices':[{'message':{'content':text},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}}


def run():
    rows=[]
    for case in fixtures():
        started=time.monotonic()
        server=Patient(case);events=[];e=OfficialEncounter(FakeClient(server),{},sleep=lambda _:None,log=lambda _:None,observer=events.append)
        result=e.run();gathered=set()
        for kind,text,answer in server.events:
            if answer=='잘 모르겠어요.':continue
            if kind=='SAY':gathered.add(topic(text))
            elif '신장' in text:gathered.add('height')
            elif '갑상' in text:gathered.add('thyroid')
        # Explicit opening appetite is already an observation, not a question.
        if '식사량은 늘' in case['opening']:gathered.add('appetite')
        required=set(case['required'])
        communication=[t.text for t in e.turns if t.category in COMMUNICATION]
        questions=[t.text for t in e.turns if t.kind=='SAY' and t.category not in COMMUNICATION]
        rows.append({'id':case['id'],'status':result['status'],'primary':server.diagnosis,'expected':case['primary'],
            'turns':server.turns,'exam_count':sum(t.kind=='EXAM' for t in e.turns),'say_count':sum(t.kind=='SAY' for t in e.turns),'fixture_wall_seconds':time.monotonic()-started,'doctor_physical_requests':e.stats.calls,'fixture_reported_prompt_tokens':e.stats.prompt_tokens,
            'fixture_reported_completion_tokens':e.stats.completion_tokens,'unique_required_topics':len(required&gathered),
            'required_topics':len(required),'topic_coverage':len(required&gathered)/len(required),
            'duplicate_questions_exact':len(questions)-len(set(questions)),
            'age_inappropriate_social_questions':sum('흡연' in t.text or '음주' in t.text for t in e.turns) if '9세' in case['opening'] else 0,
            'communication':communication,'unsafe_emergency_disposition':not case['urgent'] and '응급실' in server.record['P']['disposition'],
            'understanding_check':any(t.category=='understanding_check' for t in e.turns),
            'question_opportunity':any(t.category=='patient_questions' for t in e.turns),
            'observed_required_topics':sorted(required&gathered),'missing_required_topics':sorted(required-gathered),
            'nfc_or_test_violations':sum(len(t.text)>30 or t.kind=='TEST' for t in e.turns),
            'clinical_plan':server.record['P'],'diagnostic_successes_fixture':e.stats.diagnostic_reasoning_successful})
    n=len(rows)
    return {'label':'LOCAL RUBRIC PROXY — NOT OFFICIAL SCORE / FULL FAKE SDK / SCRIPTED DOCTOR',
            'real_model_tokens_latency_cost':'NOT MEASURED; fixture usage constants are not real costs',
            'mean_turns':sum(r['turns'] for r in rows)/n,'mean_doctor_physical_requests':sum(r['doctor_physical_requests'] for r in rows)/n,
            'mean_topic_coverage':sum(r['topic_coverage'] for r in rows)/n,'mean_exam_count':sum(r['exam_count'] for r in rows)/n,'cases':rows}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    r=run();Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='cases'}))
