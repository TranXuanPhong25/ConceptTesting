"""JSON strategy validation preserves concepts, obligations and direct inputs."""
import json
import pytest

from final.src.modular.control_flow.schema import parse_response
from final.src.modular.spec_obligation.evidence import Evidence
from final.src.modular.spec_obligation.schema import parse_obligations
from final.src.modular.tests.test_spec_obligation import context, obligation


@pytest.mark.parametrize('value', [(1,2),{1:'value'}])
def test_strategy_cannot_change_value_type_on_prompt_json_roundtrip(value):
    from final.src.modular.spec_obligation.schema import normalize_strategies
    with pytest.raises(ValueError,match='strategy_requires_json_type_tags'):
        normalize_strategies({'x':{'kind':'sampled','values':[value]}})




def test_complex_concept_strategy_keeps_the_source_bound_concept():
    raw = {'concepts':[{'id':'c','target_id':'t','name':'empty','input_relation':'empty xs',
        'instruction':'Use empty xs.','evidence_lines':[2],
        'strategies':{'xs':{'kind':'sampled','values':[[1j]]}}}],
        'inputs':[{'arguments':{'xs':[]}}]}
    parsed = parse_response(raw,[{'id':'t','evidence_lines':[2]}],['xs'])
    assert parsed['concepts'][0]['strategies']=={} and parsed['inputs']==raw['inputs']
    assert parsed['errors'][0]['reason']=='strategy_not_json_data'
    json.dumps(parsed,allow_nan=False)
