"""Closing still runs after gathering ends; observed sends respect the budget."""
import pytest
from competition import nova_sdk_adapter as A
from test_official_independent_audit import encounter, initialise, official_mode

PLAN = {'spoken_next_step':'원인 평가를 받으세요',
        'spoken_precautions':'악화하면 바로 진료받으세요',
        'spoken_test_purpose':'검사로 원인을 구분해요',
        'spoken_follow_up':'1~2주 내 증상과 결과를 다시 확인해요',
        'spoken_treatment':'결과에 따라 치료를 정해요'}

def setup(monkeypatch, seconds, urgent=False, reply='1주 후요'):
    e,_=encounter();initialise(e,'불편해요');e.turns_left=10
    monkeypatch.setattr(e,'_urgent',lambda *a:urgent)
    monkeypatch.setattr(e,'_engine_plan',lambda *a:PLAN)
    monkeypatch.setattr(e,'seconds_left',lambda:seconds)
    def say(text,category):
        t=A.Turn('SAY',text,reply if category=='understanding_check' else '없어요',category)
        e.turns.append(t);e.turns_left-=1;return t
    monkeypatch.setattr(e,'say',say)
    return e

@pytest.mark.parametrize('seconds',[239,120,75])
def test_reserved_time_delivers_purpose_followup_and_checks(monkeypatch,seconds):
    e=setup(monkeypatch,seconds);assert not e.can_gather()
    e._explain([],None)
    spoken=[t.text for t in e.turns]
    assert PLAN['spoken_test_purpose'] in spoken
    assert spoken.count(PLAN['spoken_follow_up'])==1
    assert any(t.category=='understanding_check' for t in e.turns)
    assert any(t.category=='patient_questions' for t in e.turns)
    assert len(e.turns)<=A.CLOSING_TURN_RESERVE
    assert all(A.fits(t.text) for t in e.turns)


def test_time_exhaustion_during_dialogue_stops_sends(monkeypatch):
    e=setup(monkeypatch,60)
    monkeypatch.setattr(e,'seconds_left',lambda:60 if len(e.turns)<3 else 19)
    e._explain([],None)
    assert len(e.turns)==3


def test_urgent_path_does_not_add_routine_followup_dialogue(monkeypatch):
    e=setup(monkeypatch,60,urgent=True);e._explain([],None)
    assert not any(t.category in ('understanding_check','patient_questions') for t in e.turns)
    assert PLAN['spoken_follow_up'] not in [t.text for t in e.turns]


def test_wrong_teachback_corrected_within_reserved_turns(monkeypatch):
    e=setup(monkeypatch,120,reply='3개월 후요');e._explain([],None)
    assert [t.text for t in e.turns].count(PLAN['spoken_next_step'])==2
    assert len(e.turns)<=A.CLOSING_TURN_RESERVE


def test_submission_margin_prevents_any_dialogue(monkeypatch):
    e=setup(monkeypatch,20);e._explain([],None);assert not e.turns


@pytest.mark.parametrize('seconds',[60,30])
def test_short_deadline_preserves_disposition_and_precautions(monkeypatch,seconds):
    e=setup(monkeypatch,seconds);e._explain([],None)
    spoken=[t.text for t in e.turns]
    assert PLAN['spoken_next_step'] in spoken
    assert PLAN['spoken_precautions'] in spoken
    assert len(spoken)==3
    assert not any(t.category in ('understanding_check','patient_questions') for t in e.turns)
