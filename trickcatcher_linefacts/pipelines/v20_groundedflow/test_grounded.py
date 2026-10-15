"""Independent structural expectations; native cases live in preregistered fixtures."""
import ast
import pytest
from . import grounded as g,behavior as b


def test_alias_and_cycle_rejected_before_transport():
    xs=['a'];args=(xs,xs)
    with pytest.raises(ValueError,match='shared_mutable'):g.checked_input(args)
    xs=[];xs.append(xs)
    with pytest.raises(ValueError,match='cycle'):g.checked_input((xs,))
    with pytest.raises(ValueError,match='flat_immutable'):g.checked_input(([[]],))


def test_augassign_reads_old_state_and_lambda_bound_name_not_free():
    node=ast.parse('total += x').body[0]
    assert b.local_effects(node)['reads']==['total','x']
    assert b.local_effects(node)['writes']==['total']
    node=ast.parse('ys = list(filter(lambda x: x > limit, xs))').body[0]
    assert b.local_effects(node)['reads']==['filter','limit','list','xs']


def test_cfg_branch_and_loop_break_continue_else():
    source='def f(xs):\n for x in xs:\n  if x < 0: break\n  if x == 0: continue\n else:\n  return 5\n return 6\n'
    ir=b.build(source,'f');bytext={r['text']:r['id'] for r in ir['blocks']}
    loop=bytext['FOR x IN xs'];br=bytext['break'];cont=bytext['continue']
    assert dict(source=br,target=bytext['return 6'],label='break') in ir['edges']
    assert dict(source=cont,target=loop,label='continue') in ir['edges']
    assert dict(source=loop,target=bytext['return 5'],label='exhausted/false') in ir['edges']
    for node in ir['blocks']:
        if node['kind']=='RETURN':assert [x['target'] for x in ir['edges'] if x['source']==node['id']]==['EXIT']


def test_unsupported_match_no_longer_supported():
    source='def f(xs):\n match xs:\n  case []: return 0\n return 1\n'
    assert not b.build(source,'f')['structural_supported']
    assert not g.analyze(source,'f')['supported']


def test_builtin_shadowing_and_module_execution_rejected():
    for s in ['def f(xs, set):\n return list(set(xs))\n',
              'set = list\ndef f(xs):\n return set(xs)\n',
              'def f(xs):\n set=xs\n return set\n',
              'def f(xs):\n return sorted(xs,key=lambda set: set)\n']:
        assert not g.analyze(s,'f')['supported']


def test_operation_ids_return_slice_and_argument_binding():
    ir=g.analyze('def f(xs, ys):\n unused=set(xs)\n return sorted(set(ys)-set([]))\n','f')
    assert ir['supported']
    assert len({x['id'] for x in ir['operations']})==3
    unused,live,empty=ir['operations']
    assert unused['input_arguments']==[0] and not unused['in_return_slice']
    assert live['input_arguments']==[1] and live['in_return_slice']
    assert empty['input_arguments']==[]


def test_probe_identity_occurrences_and_no_iterator_consumption():
    p=g.Probe();xs=['a','a'];assert p.before('a',xs) is xs
    ys=set(xs);assert p.after('a',ys) is ys
    assert p.events[-1]['local_count_loss'] is True
    it=filter(None,['a','b']);p.before('b',it)
    assert list(it)==['a','b']
    assert p.events[-1]['value']['type']=='unknown'


def test_eligibility_does_not_exclude_valid_negative_elements():
    r=dict(mode='preserve',eligibility='positive',element_type='int',argument=0)
    result=g.requirement_check(r,([-1,-1,2],),g.snapshot([-1,2]))
    assert result['domain'] is True and result['holds'] is True and result['trigger'] is False
    result=g.requirement_check(r,([-1,2,2],),g.snapshot([-1,2]))
    assert result['domain'] is True and result['holds'] is False and result['trigger'] is True
