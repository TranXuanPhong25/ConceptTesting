import pytest
from .recipe_compiler import compile_public
from .native_construct import certify_case

BUDGET={'max_candidates':8,'max_executions':32,'seeds':[20261024,20261025],'repeats':2}


def test_compiler_binds_generic_rounding_with_local_condition():
    source='''import math
def f(xs):
    gap = len(xs)
    return math.ceil(gap / 2)
'''
    req={'source':source,'entry':'f','public_examples':[{'arguments':'([1,2],)','expected':'1'}]}
    compiled=compile_public(req,BUDGET)
    recipe=next(r for r in compiled['recipes'] if r['kind']=='odd_cardinality_unique')
    assert recipe['event_predicate']['local_odd_equals_input_length']=='gap'
    report=certify_case(source,'f',[recipe],([1,2],))
    assert report['native_executions']<=256
    assert any(r['output_sensitivity'] is True for r in report['recipes'][0]['runs'])


def test_wrong_local_event_is_not_certified():
    source='''import math
def f(xs):
    gap = 2
    return math.ceil(gap / 2)
'''
    req={'source':source,'entry':'f','public_examples':[{'arguments':'([1,2],)','expected':'1'}]}
    recipe=next(r for r in compile_public(req,BUDGET)['recipes'] if r['kind']=='odd_cardinality_unique')
    report=certify_case(source,'f',[recipe],([1,2],))
    assert not any(r['obligation_realized'] for r in report['recipes'][0]['runs'])
