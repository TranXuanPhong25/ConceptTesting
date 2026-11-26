"""JSON strategy validation preserves concepts and direct inputs."""
import json

from final.src.modular.control_flow.schema import parse_response

def test_complex_concept_strategy_keeps_the_source_bound_concept():
    raw = {'concepts':[{'id':'c','target_id':'t','name':'empty','input_relation':'empty xs',
        'instruction':'Use empty xs.','evidence_lines':[2],
        'strategies':{'xs':{'kind':'sampled','values':[[1j]]}}}],
        'inputs':[{'arguments':{'xs':[]}}]}
    parsed = parse_response(raw,[{'id':'t','evidence_lines':[2]}],['xs'])
    assert parsed['concepts'][0]['strategies']=={} and parsed['inputs']==raw['inputs']
    assert parsed['errors'][0]['reason']=='strategy_not_json_data'
    json.dumps(parsed,allow_nan=False)
