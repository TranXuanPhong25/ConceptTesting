import json
import pytest
from . import templates as t,template_semantic as s,behavior as b


def model(template,**params):return t.normalize(dict(template=template,**params),2)


def test_map_absolute_pair_difference_and_semantic_fault():
    m=model('MAP',other_argument=1,transform='abs_sub')
    assert t.expected(m,([2,4],[5,1]))==[3,3]
    fault=t.alternatives(m)[0];c=dict(model=m,fault=fault)
    assert t.activates(c,([2],[5]))
    assert not t.activates(c,([5],[2]))
    assert t.holds(m,([2],[5]),[-3]) is False


def test_filter_preserves_multiplicity_and_ordered_strings():
    m=model('FILTER',predicate='length_even',order='length_lex')
    assert t.expected(m,(['zz','aa','zz','b','aaaa'],))==['aa','zz','zz','aaaa']
    fault=next(x for x in t.alternatives(m) if x['change']['field']=='distinct')
    assert t.activates(dict(model=m,fault=fault),(['aa','aa'],))


def test_empty_group_and_tuple_component_requirement():
    m=model('REDUCE',predicate='positive',aggregate='min',component=1)
    assert t.expected(m,([0,-1],)) is None
    assert t.holds(m,([0,-1],),(-1,None)) is True
    fault=next(x for x in t.alternatives(m) if x['change']['field']=='empty_policy')
    assert t.activates(dict(model=m,fault=fault),([0],))
    assert not t.activates(dict(model=m,fault=fault),([1],))


def test_index_filter_count_and_characters():
    m=model('REDUCE',predicate='even',index='odd',aggregate='sum')
    assert t.expected(m,([2,4,6,8],))==12
    m=model('REDUCE',predicate='member',values='AEIOU',index='even',aggregate='count')
    assert t.expected(m,('IbEcU',))==3
    m=model('FILTER',predicate='not_member',values='aeiouAEIOU')
    assert t.expected(m,('a b E c',))==' b  c'


def test_ordering_ties_direction_and_multiplicity():
    m=model('ORDER_CHECK',direction='either')
    assert t.expected(m,([1,1,2],)) is True
    assert t.expected(m,([2,2,1],)) is True
    assert t.expected(m,([1,3,2],)) is False
    m=model('ORDER_CHECK',max_count=2)
    assert t.expected(m,([1,1,2],)) is True
    assert t.expected(m,([1,1,1],)) is False


def test_balance_prefix_and_empty():
    m=model('BALANCE',opening='<',closing='>')
    assert t.expected(m,('',)) is True
    assert t.expected(m,('><',)) is False
    fault=next(x for x in t.alternatives(m) if x['change']['field']=='check_prefix')
    assert t.activates(dict(model=m,fault=fault),('><',))


def test_segment_boundary_and_first_word():
    m=model('SEGMENT_COUNT',token='I')
    assert t.expected(m,('I wait? I work! You wait. I run',))==3
    assert t.expected(m,('Iceland is cold.',))==0
    assert t.expected(m,('',))==0


def test_capacity_different_collection_sizes():
    m=model('CAPACITY',true_value='YES',false_value='NO')
    assert t.expected(m,([1,3],[2,4,6]))=='YES'
    assert t.expected(m,([1,3],[2]))=='NO'


def test_containment_equality_proper_and_multiset():
    m=model('CONTAINMENT')
    assert t.expected(m,({1,2},{1,2})) is True
    fault=next(x for x in t.alternatives(m) if x['change']['alternative']=='proper_subset')
    assert t.activates(dict(model=m,fault=fault),({1,2},{1,2}))
    assert t.expected(model('CONTAINMENT',mode='multiset'),([1],[1,1])) is False
    assert t.expected(m,([1],[1,1])) is True


def test_neighborhood_selection():
    m=model('NEIGHBOR_SELECT',values='aeiouAEIOU')
    assert t.expected(m,('bAc',))=='A'
    assert t.expected(m,('bAcbdEf',))=='E'
    assert t.expected(m,('abc',))==''


def test_source_units_preserve_spans_without_asking_llm_to_copy_quotes():
    ir=b.build('def f(xs):\n    """Return the count of negative values,\n    preserving the original input.\n\n    Examples:\n    >>> f([])\n    0\n    """\n    return 0\n','f')
    units=s.units(ir)
    assert len(units)==1 and units[0]['id']=='S0'
    assert ir['docstring'][slice(*units[0]['span'])]==units[0]['quote']
    raw=json.dumps({'proposals':[dict(template='REDUCE',predicate='negative',aggregate='count',evidence=['S0'])]})
    accepted,reject=s.proposals(raw,ir)
    assert len(accepted)==1 and not reject
    assert 'result' not in raw


def test_malformed_params_and_no_invented_ids():
    for row in ({'template':'full_function'}, {'template':'MAP','transform':'invented'},
                {'template':'FILTER','unexpected':True},{'template':'REDUCE','argument':99}):
        with pytest.raises(ValueError):t.normalize(row,1)
    with pytest.raises(ValueError):s.parse('[]','proposals')


def test_compilation_rejects_base_contradiction_and_keeps_semantic_fault():
    from . import behavior_worker as worker
    source='''def pick(xs):
    """Keep positive items in input order, preserving repeated items."""
    out=[]
    for x in xs:
        if x>0 and x not in out:
            out.append(x)
    return out
'''
    task=dict(put=source,entry='pick',base='',mined_valid_src='def valid(xs):\n    return True\n',tool_inputs=[])
    ir=b.build(source,'pick')
    good=dict(id='P0',model=model('FILTER',predicate='positive'),evidence=s.units(ir))
    bad=dict(id='P1',model=model('FILTER',predicate='negative'),evidence=s.units(ir))
    prepared=dict(base_verification_complete=True,all_base_inputs=['([1, 2],)'],
                  discovery_pool=[dict(input_repr='([1, 1],)')],ir=ir)
    compiled=worker.compile_models(dict(task=task,prepared=prepared,proposals=[good,bad]),None)
    assert len(compiled['proposals'])==1 and compiled['rejections'][0]['reason']=='base_contradiction'
    good=compiled['proposals'][0]
    fault=next(x for x in good['faults'] if x['change']['field']=='distinct')
    block=next(x['id'] for x in ir['blocks'] if x['kind']=='RETURN')
    raw=json.dumps(dict(bindings=[dict(proposal=good['id'],fault=fault['id'],blocks=[block],
         reasoning=dict(code_claim='Current loop removes repeated items',path_guarantees='Value is positive on the append path',gap='No rule permits losing multiplicity'))]))
    cards,rejections=s.bindings(raw,ir,[good]);assert not rejections and len(cards)==1
    checked=worker.check(dict(task=task,prepared=prepared,cards=cards),None)
    assert len(checked['shown'])==1
    witness=checked['shown'][0]['witness']
    assert witness['candidate_violation'] and witness['anchor_hit'] and not witness['base_distinguished']


def test_unknown_spec_unit_is_rejected_without_quote_rewriting():
    ir=b.build('def f(xs):\n    """Keep the input sequence unchanged."""\n    return xs\n','f')
    accepted,rejected=s.proposals('{"proposals":[{"template":"MAP","evidence":["S999"]}]}',ir)
    assert accepted==[] and rejected[0]['reason']=='unknown_spec_unit'


def test_property_score_separates_confirmed_bug_from_false_requirement():
    from . import behavior_worker as worker
    source='def pick(xs):\n    out=[]\n    for x in xs:\n        if x>0 and x not in out: out.append(x)\n    return out\n'
    task=dict(put=source,entry='pick',mined_valid_src='def valid(xs):\n    return True\n')
    correct=model('FILTER',predicate='positive')
    fault=next(x for x in t.alternatives(correct) if x['change']['field']=='distinct')
    wrong=model('FILTER',predicate='negative')
    wrong_fault=next(x for x in t.alternatives(wrong) if x['change']['field']=='predicate' and x['change']['alternative']=='all')
    records=worker.property_score(dict(task=task,
        canon='def pick(xs):\n    return [x for x in xs if x>0]\n',contract='def pick(xs):\n    assert isinstance(xs,list)\n',
        cards=[dict(id='C0',model=correct,fault=fault),dict(id='C1',model=wrong,fault=wrong_fault)],
        samples=[dict(arm='behavior+concept',selected=[dict(input_repr='([1, 1],)')])]),None)['records']
    assert records[0]['confirmed_report'] and not records[0]['false_alarm']
    assert records[1]['false_alarm'] and not records[1]['confirmed_report']
