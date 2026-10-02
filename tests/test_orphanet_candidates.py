import hashlib
import json
import pytest
from nova_agent.knowledge.reference_catalog import (ORPHANET_ROOT, reference_candidates,
    retrieve_reference_candidates, validate_bundle, clean)
from nova_agent.knowledge.retrieval import all_diseases
from scripts.import_orphanet_candidates import read_conditions


def test_new_identities_do_not_overlap_previous_names_or_aliases():
    entries=list(reference_candidates().values())
    old=[e for e in entries if not e['id'].startswith('orphanet_')]+list(all_diseases().values())
    occupied={clean(n) for e in old for n in [e['name'],*e['aliases']]}
    added=[e for e in entries if e['id'].startswith('orphanet_')]
    assert len(added)==2177
    for e in added:
        names={clean(n) for n in [e['name'],*e['aliases']]}
        assert not names & occupied,e['name']
        occupied.update(names)


@pytest.mark.parametrize('field,value',[
    ('source_status','ActiveHistorical'),('source_status','Inactive'),
    ('source_classification','Group'),('source_classification','Subtype'),
    ('source_disorder_type','Clinical situation'),('license_url',''),
    ('source_url','https://example.org/'),
    ('source_url','https://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=en&Expert=0'),
    ('clinical_review_verified',True),('autonomous_diagnosis_enabled',True)])
def test_bundle_rejects_scope_license_and_promotion_errors(field,value):
    data=json.loads((ORPHANET_ROOT/'catalog.json').read_text())
    manifest=json.loads((ORPHANET_ROOT/'manifest.json').read_text())
    data[0][field]=value
    raw=json.dumps(data).encode();manifest['catalog_sha256']=hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError):
        validate_bundle(raw,manifest,(ORPHANET_ROOT/'selection.txt').read_bytes(),
            expected_count=2177,source_kind='orphanet_disorder')


@pytest.mark.parametrize('status,level,lang,expected',[
    ('Active','Disorder','en',1),('ActiveHistorical','Disorder','en',0),
    ('Inactive','Disorder','en',0),('Active','Group','en',0),
    ('Active','Subtype','en',0),('Active','Disorder','fr',0)])
def test_importer_filters_source_scope(tmp_path,status,level,lang,expected):
    p=tmp_path/'source.xml'
    p.write_text(f'''<JDBOR><DisorderList><Disorder><OrphaCode>1</OrphaCode>
    <Name lang="en">Test disorder</Name><Totalstatus>{status}</Totalstatus>
    <ClassificationLevel><Name>{level}</Name></ClassificationLevel>
    <DisorderType><Name>Disease</Name></DisorderType>
    <ExpertLink>http://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=en&amp;Expert=1</ExpertLink>
    <SummaryInformationList><SummaryInformation><TextSectionList><TextSection lang="{lang}">
    <TextSectionType><Name>Definition</Name></TextSectionType><Contents>Definition.</Contents>
    </TextSection></TextSectionList></SummaryInformation></SummaryInformationList>
    </Disorder></DisorderList></JDBOR>''')
    assert len(read_conditions(p)[2])==expected


def test_exact_title_navigation_keeps_license_and_does_not_override_negation():
    e=next(e for e in reference_candidates().values() if e['id'].startswith('orphanet_') and ' without ' in e['name'])
    hit=retrieve_reference_candidates([e['name']],1)[0]
    assert hit['reference_id']==e['id'] and hit['match_type']=='exact_title'
    assert hit['license_url']=='https://creativecommons.org/licenses/by/4.0/'
    assert 'Orphanet' in hit['attribution']
    assert retrieve_reference_candidates([e['name']],0)==[]
    for prefix in ('No ','Possible ','Mother has ','History of '):
        assert e['id'] not in {h['reference_id'] for h in retrieve_reference_candidates([prefix+e['name']])}


def test_orphanet_cannot_authorize_final_diagnosis():
    from tests.test_reference_catalog import proposed_reference
    from nova_agent.safety_validator import SafetyValidator
    from nova_agent.state import PatientState
    from nova_agent.action_selector import AgentAction
    from nova_agent.stop_policy import StopDecision
    e=next(e for e in reference_candidates().values() if e['id'].startswith('orphanet_'))
    _,output=proposed_reference()
    output.differential[0].diagnosis=e['name'];output.differential[0].diagnosis_id=e['id']
    output.selected_action.key=e['id'];output.selected_action.content=e['name']
    validator=SafetyValidator();merged=validator.merge_differential(output,[],[])
    assert merged[0].confidence_band=='LOW'
    result=validator.validate_action(PatientState(turn_count=20),output,{},
        AgentAction(action_type='ASK',key='onset',content='Onset?',rationale='test'),merged,
        StopDecision(should_diagnose=True,forced=False,reason='test',readiness_score=1))
    assert result.overridden and result.action.action_type=='ASK'
