import pytest
from nova_agent.matching import feature_present, feature_present_with_aliases


@pytest.mark.parametrize('matcher',[feature_present,feature_present_with_aliases])
@pytest.mark.parametrize('feature,text,expected',[
 ('severe diffuse abdominal pain','Diffuse crampy abdominal pain.',False),
 ('severe diffuse abdominal pain','Mild diffuse abdominal pain.',False),
 ('severe diffuse abdominal pain','Severe diffuse abdominal pain.',True),
 ('severe diffuse abdominal pain','Intense pain all over my abdomen.',True),
 ('severe diffuse abdominal pain','No severe diffuse abdominal pain.',False),
 ('crampy lower abdominal pain','Diffuse crampy abdominal pain.',False),
 ('crampy lower abdominal pain','Crampy upper abdominal pain.',False),
 ('crampy lower abdominal pain','Crampy lower abdominal pain.',True),
 ('crampy lower abdominal pain','No crampy lower abdominal pain.',False),
 ('crampy lower abdominal pain','My mother has crampy lower abdominal pain.',False),
])
def test_descriptor_must_be_observed(matcher,feature,text,expected):
    assert matcher(feature,[text],scrub_negated_spans=True) is expected
