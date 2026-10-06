import io
import json
import urllib.error
from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace

import pytest
from nova_agent import config
from nova_agent.llm_client import CompetitionLLMClient, parse_agent_turn_output
from nova_agent.llm_preflight import PreflightStatus
from nova_agent.uncertainty import assess_evidence
from nova_agent.state import PatientState
from nova_agent.differential import _score_disease
from nova_agent.matching import explicitly_denied_in_findings
from nova_agent.knowledge.retrieval import disease_by_id

CONTENT = json.dumps({'selected_action': {'type': 'ASK', 'key': 'onset', 'content': 'When did this start?'}})


def configured_client(monkeypatch, response=None, error=None):
    client=CompetitionLLMClient();client.base_url='http://127.0.0.1:9876/v1';client.max_retries=1
    attempts=[]
    def send(request):
        attempts.append(json.loads(request.data))
        if error: raise error
        body=response if isinstance(response, bytes) else json.dumps(response or {
            'model':client.MODEL_TARGET,'choices':[{'message':{'content':CONTENT}}]}).encode()
        return nullcontext(SimpleNamespace(status=200,read=lambda:body))
    monkeypatch.setattr(client,'_open_request',send)
    return client,attempts


def test_unconfigured_endpoint_never_probes_default_localhost(monkeypatch):
    monkeypatch.setattr(config,'_config',replace(config.get_config(),competition_base_url=''))
    client=CompetitionLLMClient()
    monkeypatch.setattr(client,'_open_request',lambda request:pytest.fail('must not send'))
    assert client.preflight()==(False,'NOT_CONFIGURED')
    assert client.last_preflight.attempts==0 and not client.last_preflight.endpoint_configured


@pytest.mark.parametrize('status',[401,403,429,500,502,503])
def test_http_status_categories_and_bounded_retry(monkeypatch,status):
    client,calls=configured_client(monkeypatch,error=urllib.error.HTTPError(
        'http://private.invalid/?token=do-not-log',status,'sensitive reason',{},None))
    assert not client.preflight()[0]
    expected='AUTH_FAILED' if status in {401,403} else 'REAL_CALL_FAILED'
    assert client.last_preflight.status.value==expected
    assert len(calls)==(1 if status in {401,403} else 2)
    rendered=json.dumps(client.last_preflight.as_dict())
    assert 'do-not-log' not in rendered and 'sensitive' not in rendered


@pytest.mark.parametrize('error',[TimeoutError(),ConnectionResetError(),urllib.error.URLError('redacted')])
def test_network_failure_is_distinct_from_parse_failure(monkeypatch,error):
    client,calls=configured_client(monkeypatch,error=error)
    assert not client.preflight()[0]
    assert client.last_preflight.status==PreflightStatus.ENDPOINT_UNREACHABLE and len(calls)==2


@pytest.mark.parametrize('body',[b'not json',b'{"choices":',b'{}'])
def test_actual_http_success_with_invalid_structure_fails_parse(monkeypatch,body):
    client,calls=configured_client(monkeypatch,response=body)
    assert not client.preflight()[0]
    assert client.last_preflight.status==PreflightStatus.STRUCTURED_OUTPUT_FAILED
    assert client.last_preflight.http_status_category=='2xx' and len(calls)==2


@pytest.mark.parametrize('revision,ok',[(None,True),(config.EXPECTED_COMPETITION_REVISION,True),('wrong-revision',False)])
def test_optional_revision_checked_but_never_sent(monkeypatch,revision,ok):
    payload={'model':config.EXPECTED_COMPETITION_MODEL,'choices':[{'message':{'content':CONTENT}}]}
    if revision is not None:payload['revision']=revision
    client,calls=configured_client(monkeypatch,response=payload)
    assert client.preflight()[0] is ok
    assert all('revision' not in c and 'model_revision' not in c for c in calls)
    if revision is None:assert client.last_preflight.revision_status=='NOT_VERIFIABLE_FROM_RUNTIME'
    if not ok:assert client.last_preflight.status==PreflightStatus.REVISION_MISMATCH


@pytest.mark.parametrize('url',['https://user:password@private.invalid/v1','https://private.invalid/v1?token=private','ftp://private.invalid/v1'])
def test_credential_bearing_urls_are_rejected_before_transport(monkeypatch,url):
    client,calls=configured_client(monkeypatch);client.base_url=url
    assert not client.preflight()[0] and not calls
    assert client.last_preflight.status==PreflightStatus.INVALID_CONFIGURATION
    assert 'password' not in json.dumps(client.last_preflight.as_dict())


def test_repair_preserves_string_content_and_never_invents_action():
    raw="{'selected_action': {'type': 'ask', 'content': 'true false null remain literal'}, 'ready_to_diagnose': false}"
    parsed=parse_agent_turn_output(raw)
    assert parsed.selected_action.content=='true false null remain literal'
    assert parsed.ready_to_diagnose is False
    assert parse_agent_turn_output('{"summary":"medical content without an action"}') is None


@pytest.mark.parametrize('finding,denied',[('focal neurological deficit',False),('no focal neurological deficit',True),
    ('no fever; focal neurological deficit',False),('without focal neurological deficit',True)])
def test_reassuring_negation_requires_a_real_denial(finding,denied):
    assert explicitly_denied_in_findings('focal neurological deficit',[finding]) is denied
    state=PatientState(chief_complaint='dizziness');state.record_exam('neuro_exam',finding)
    contradictions=_score_disease(disease_by_id('ischemic_stroke'),state)[3]
    assert ('no focal neurological deficit' in contradictions) is denied


@pytest.mark.parametrize('text',["Send the appointment confirmation.","Summarize the school agenda.",
    "What is the expiry date on this medicine label?"])
def test_nondiagnostic_requests_without_patient_evidence_are_out_of_scope(text):
    assert assess_evidence(PatientState(chief_complaint=text),[]).internal_result=='OUT_OF_DOMAIN'


@pytest.mark.parametrize('text',["Send my appointment confirmation; I have fainted twice.",
    "How do I store this medication? I accidentally took a double dose.",
    "예약을 바꾸고 싶은데 지금 숨이 차고 가슴이 아파요."])
def test_request_intent_never_suppresses_current_clinical_or_exposure_risk(text):
    assert assess_evidence(PatientState(chief_complaint=text),[]).internal_result!='OUT_OF_DOMAIN'
