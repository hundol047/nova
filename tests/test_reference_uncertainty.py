"""Development probes for uncertainty bypass at the title-navigation boundary."""
import pytest
from nova_agent.knowledge.reference_catalog import reference_candidates, retrieve_reference_candidates

NAMES=['Tuberculosis','Multiple Sclerosis',next(e['name'] for e in reference_candidates().values()
    if e['id'].startswith('orphanet_') and ' without ' in e['name'])]

@pytest.mark.parametrize('name',NAMES)
@pytest.mark.parametrize('suffix',['?','??',' (?)',' (??)'])
def test_question_mark_cannot_become_exact_title_evidence(name,suffix):
    assert retrieve_reference_candidates([name+suffix])==[]

@pytest.mark.parametrize('name',NAMES)
def test_case_and_whitespace_navigation_still_resolves(name):
    result=retrieve_reference_candidates(['  '+name.upper().replace(' ','  ')+'  '],1)
    assert result[0]['name']==name and result[0]['match_type']=='exact_title'
