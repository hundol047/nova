import hashlib
import json
from pathlib import Path
import pytest
from nova_agent.knowledge.reference_catalog import (
    ROOT, catalog_inventory, reference_candidates, reference_by_name,
    retrieve_reference_candidates, validate_bundle,
)
from nova_agent.knowledge.retrieval import all_diseases
from nova_agent.state import PatientState
from nova_agent.differential import DifferentialEngine
from nova_agent.action_selector import AgentAction
from nova_agent.llm_schema import AgentTurnOutput, DifferentialItemOutput, SelectedActionOutput
from nova_agent.safety_validator import SafetyValidator
from nova_agent.stop_policy import StopDecision

ENTRIES=list(reference_candidates().values())


def test_inventory_does_not_misrepresent_reference_topics_as_validated_diagnoses():
    assert catalog_inventory()=={'total_entries':1020,'rule_supported_entries':68,
        'reference_only_entries':952,'clinically_validated_entries':0,
        'reference_autonomous_diagnosis_enabled':False}
    assert not set(reference_candidates()).intersection(all_diseases())
    assert all(e['summary'] and e['attribution'] and e['source_url'] for e in ENTRIES)


@pytest.mark.parametrize('entry',ENTRIES,ids=[e['name'] for e in ENTRIES])
def test_reference_titles_resolve_and_retrieve_with_provenance(entry):
    assert reference_by_name(entry['id'])['name']==entry['name']
    assert reference_by_name(entry['name'])['id']==entry['id']
    hits=retrieve_reference_candidates([entry['name']],top_k=1)
    assert hits[0]['reference_id']==entry['id']
    assert hits[0]['validation_status']=='reference_only'
    assert hits[0]['source']==entry['source_url']
    assert hits[0]['autonomous_diagnosis_enabled'] is False


@pytest.mark.parametrize('text',['No tuberculosis','Mother has rheumatoid arthritis','Possible multiple sclerosis','History of measles','fatigue','Unknown / not provided.'])
def test_negated_family_tentative_history_and_sparse_text_do_not_generate_candidates(text):
    assert retrieve_reference_candidates([text])==[]


def test_reference_summary_cannot_become_patient_evidence():
    state=PatientState(chief_complaint='fatigue')
    before=state.all_findings_text()
    baseline=DifferentialEngine().update(state)
    state.reference_candidates=retrieve_reference_candidates(['Tuberculosis'])
    assert state.all_findings_text()==before
    assert [d.model_dump() for d in DifferentialEngine().update(state)]==[d.model_dump() for d in baseline]


@pytest.mark.parametrize('mutation',['checksum','promotion','duplicate','foreign_source','empty_summary'])
def test_reference_bundle_fails_closed_on_corruption_or_self_promotion(mutation):
    raw=(ROOT/'catalog.json').read_bytes();manifest=json.loads((ROOT/'manifest.json').read_text())
    selection=(ROOT/'selection.txt').read_bytes()
    if mutation=='checksum':
        with pytest.raises(ValueError):validate_bundle(raw+b' ',manifest,selection)
        return
    data=json.loads(raw)
    if mutation=='promotion':data[0]['autonomous_diagnosis_enabled']=True
    if mutation=='duplicate':data[1]['id']=data[0]['id']
    if mutation=='foreign_source':data[0]['source_url']='https://example.org/unsourced'
    if mutation=='empty_summary':data[0]['summary']=' '
    raw=json.dumps(data).encode();manifest['catalog_sha256']=hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError):validate_bundle(raw,manifest,selection)


def proposed_reference():
    entry=reference_by_name('Multiple Sclerosis')
    output=AgentTurnOutput(differential=[DifferentialItemOutput(diagnosis=entry['name'],
        diagnosis_id=entry['id'],rank=1,supporting_evidence=['one claimed clue','another claimed clue'],
        confidence='HIGH',dangerous_if_missed=True)],
        selected_action=SelectedActionOutput(type='DIAGNOSE',key=entry['id'],content=entry['name']))
    return entry,output


def test_reference_candidate_is_low_confidence_and_cannot_self_authorize_final():
    from nova_agent.decision_quality import assess_decision
    entry,output=proposed_reference();validator=SafetyValidator()
    state=PatientState(chief_complaint='weakness',turn_count=20)
    merged=validator.merge_differential(output,[],[])
    assert merged[0].confidence_band=='LOW'
    quality=assess_decision(state,merged)
    assert quality['catalog_status']=='reference_only' and quality['band']=='LOW'
    action=AgentAction(action_type='ASK',key='onset',content='When did it begin?',rationale='collect evidence')
    stop=StopDecision(should_diagnose=True,forced=False,reason='test fixture',readiness_score=1)
    result=validator.validate_action(state,output,{},action,merged,stop)
    assert result.overridden and result.action.action_type=='ASK'
    assert 'Reference-only' in result.override_reason


def test_forced_submission_cannot_mix_known_key_with_reference_label():
    entry,output=proposed_reference();validator=SafetyValidator()
    state=PatientState(chief_complaint='weakness',turn_count=59)
    action=AgentAction(action_type='DIAGNOSE',key='hypoglycemia',content='Hypoglycemia',rationale='forced')
    stop=StopDecision(should_diagnose=True,forced=True,reason='turn budget',readiness_score=0)
    result=validator.validate_action(state,output,{},action,[],stop)
    assert result.action.key=='hypoglycemia' and result.action.content=='Hypoglycemia'


def test_reference_context_is_bounded_and_explicitly_labeled_in_model_prompt():
    from nova_agent.clinical_summary import build_clinical_summary
    from nova_agent.llm_client import TurnContext,build_reasoning_prompt
    state=PatientState(chief_complaint='multiple sclerosis')
    hits=retrieve_reference_candidates([state.chief_complaint],top_k=1000)
    assert len(hits)<=5 and all(len(h['text'])<=1100 for h in hits)
    ctx=TurnContext(summary=build_clinical_summary(state,[],[]), differential=[],safety_findings=[],candidates=[],
        chosen_action=AgentAction(action_type='ASK',key='onset',content='Onset?',rationale='test'),
        stop_decision=StopDecision(should_diagnose=False,forced=False,reason='test',readiness_score=0),retrieved_context=hits)
    prompt=build_reasoning_prompt(ctx)
    assert 'REFERENCE ONLY' in prompt and 'autonomous diagnosis disabled' in prompt
    assert 'Source: MedlinePlus, National Library of Medicine.' in prompt


def test_candidate_pipeline_and_disable_switch(monkeypatch):
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent import config
    original=config._config
    try:
        monkeypatch.setenv('NOVA_REFERENCE_CANDIDATES','1');config.get_config(reload=True)
        state=PatientState(chief_complaint='rheumatoid arthritis')
        DoctorAgent().decide(state)
        assert any(h['name']=='Rheumatoid Arthritis' for h in state.reference_candidates)
        monkeypatch.setenv('NOVA_REFERENCE_CANDIDATES','0');config.get_config(reload=True)
        DoctorAgent().decide(state)
        assert state.reference_candidates==[]
    finally:config._config=original


@pytest.mark.parametrize('name',['Possible multiple sclerosis','Likely HIV infection','Multiple sclerosis versus myasthenia gravis'])
def test_qualifiers_cannot_bypass_reference_finalization_guard(name):
    entry,output=proposed_reference()
    output.selected_action.key=''
    output.selected_action.content=name
    action=AgentAction(action_type='ASK',key='onset',content='Onset?',rationale='collect evidence')
    stop=StopDecision(should_diagnose=True,forced=False,reason='fixture',readiness_score=1)
    state=PatientState(turn_count=20)
    validator=SafetyValidator()
    result=validator.validate_action(state,output,{},action,validator.merge_differential(output,[],[]),stop)
    assert result.overridden and result.action.action_type=='ASK'


def test_reference_guard_does_not_match_any_original_rule_identity():
    from nova_agent.knowledge.reference_catalog import reference_mentions
    for id,e in all_diseases().items():
        assert not reference_mentions(id), id
        assert not reference_mentions(e['name']), e['name']
        assert all(not reference_mentions(alias) for alias in e['aliases']), e['aliases']


def test_added_genetics_identities_do_not_duplicate_prior_candidates_or_rules():
    from nova_agent.knowledge.reference_catalog import clean
    old = [e for e in ENTRIES if not e['id'].startswith('medlineplus_genetics_')]
    old.extend(all_diseases().values())
    occupied = {clean(n) for e in old for n in [e['name'], *e['aliases']]}
    added = [e for e in ENTRIES if e['id'].startswith('medlineplus_genetics_')]
    assert len(added) == 748
    for entry in added:
        names = {clean(n) for n in [entry['name'], *entry['aliases']]}
        assert not names & occupied, entry['name']
        occupied.update(names)


@pytest.mark.parametrize('mutation', ['gene_page', 'wrong_condition', 'promotion', 'duplicate', 'selection', 'checksum'])
def test_genetics_bundle_rejects_wrong_scope_corruption_and_promotion(mutation):
    from nova_agent.knowledge.reference_catalog import GENETICS_ROOT
    raw = (GENETICS_ROOT / 'catalog.json').read_bytes()
    manifest = json.loads((GENETICS_ROOT / 'manifest.json').read_text())
    selection = (GENETICS_ROOT / 'selection.txt').read_bytes()
    data = json.loads(raw)
    if mutation == 'gene_page': data[0]['source_url'] = 'https://medlineplus.gov/genetics/gene/brca1/'
    if mutation == 'wrong_condition': data[0]['source_url'] = data[1]['source_url']
    if mutation == 'promotion': data[0]['clinical_review_verified'] = True
    if mutation == 'duplicate': data[1] = data[0]
    raw = json.dumps(data).encode()
    manifest['catalog_sha256'] = hashlib.sha256(raw).hexdigest()
    if mutation == 'checksum': raw += b' '
    if mutation == 'selection': selection += b'Extra condition\n'
    with pytest.raises(ValueError):
        validate_bundle(raw, manifest, selection, expected_count=748, source_kind='genetics_condition')


def test_new_genetics_candidate_cannot_authorize_final_diagnosis():
    entry = next(e for e in ENTRIES if e['id'].startswith('medlineplus_genetics_'))
    _, output = proposed_reference()
    output.differential[0].diagnosis = entry['name']
    output.differential[0].diagnosis_id = entry['id']
    output.selected_action.key = entry['id']
    output.selected_action.content = 'Likely ' + entry['name']
    validator = SafetyValidator()
    merged = validator.merge_differential(output, [], [])
    assert merged[0].confidence_band == 'LOW'
    action = AgentAction(action_type='ASK', key='onset', content='Onset?', rationale='collect evidence')
    result = validator.validate_action(PatientState(turn_count=20), output, {}, action, merged,
        StopDecision(should_diagnose=True, forced=False, reason='fixture', readiness_score=1))
    assert result.overridden and result.action.action_type == 'ASK'


def test_genetics_importer_excludes_gene_pages_and_non_description_text(tmp_path):
    from scripts.import_genetics_candidates import read_conditions
    xml = tmp_path / 'source.xml'
    xml.write_text('''<summaries xmlns="https://medlineplus.gov/download/test.xsd">
      <gene-summary><name>GENE1</name><ghr-page>https://medlineplus.gov/genetics/gene/gene1</ghr-page></gene-summary>
      <health-condition-summary><name>Example condition</name>
        <ghr-page>https://medlineplus.gov/genetics/condition/example-condition</ghr-page>
        <text-list>
          <text><text-role>description</text-role><html><p>Preserved <b>condition</b> description.</p></html></text>
          <text><text-role>frequency</text-role><html><p>Not imported.</p></html></text>
        </text-list>
      </health-condition-summary></summaries>''')
    _, entries = read_conditions(xml)
    assert len(entries) == 1
    assert entries[0]['summary'] == 'Preserved condition description.'
    assert entries[0]['autonomous_diagnosis_enabled'] is False


def test_genetics_importer_rejects_external_entity_declarations(tmp_path):
    from scripts.import_genetics_candidates import read_conditions
    xml = tmp_path / 'source.xml'
    xml.write_text('<!DOCTYPE summaries [<!ENTITY x SYSTEM "file:///nonexistent">]><summaries/>')
    with pytest.raises(ValueError, match='entity declaration'):
        read_conditions(xml)
