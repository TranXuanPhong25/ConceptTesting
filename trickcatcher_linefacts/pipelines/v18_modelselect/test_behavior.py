import ast
from . import behavior as b,semantic as s

SOURCE='''def compare(game, guess):
    result = []
    for i in range(len(game)):
        result.append(game[i] - guess[i])
    return result
'''

def test_collection_write_propagates_and_aliases():
    run=b.replay(SOURCE,'compare',([2,5],[1,2]))
    assert run['status']=='ok' and run['output_repr']=='[1, 3]'
    returns=[e for e in run['events'] if e['event']=='return']
    assert returns[-1]['state']['result']['version']>=3
    assert returns[-1]['concrete']['result']=='[1, 3]'
    r=b.replay('def f(xs):\n    alias=xs\n    xs.append(3)\n    return alias\n','f',([1],))
    e=r['events'][-1]
    assert e['state']['alias']['object']==e['state']['xs']['object']
    assert e['concrete']['alias']=='[1, 3]'

def test_early_return_and_loop_else_edges():
    src='def f(xs):\n    for x in xs:\n        if x: return 4\n    else:\n        return 5\n    return 6\n'
    ir=b.build(src,'f')
    for block in ir['blocks']:
        if block['kind']=='RETURN':assert [e['target'] for e in ir['edges'] if e['source']==block['id']]==['EXIT']
    assert b.replay(src,'f',([1],))['output_repr']=='4'
    assert b.replay(src,'f',([],))['output_repr']=='5'

def test_predicate_machine_is_finite_projection_and_explicitly_partial():
    m=b.machine([b.replay(SOURCE,'compare',([2,5],[1,2]))])
    assert m['under_approximation'] is True
    assert m['states'] and m['transitions']
    assert all('version' not in str(x['predicates']) for x in m['states'])

def test_mutants_are_first_order_and_not_oracles():
    src='def f(xs):\n    ys=[x for x in xs if x>0]\n    if not ys: return None\n    return min(ys)\n'
    rows=b.mutants(src,'f')
    bypass=next(m for m in rows if m['operator']=='BYPASS_FILTER')
    assert b.replay(src,'f',([-1,2],))['output_repr']=='2'
    assert b.replay(bypass['source'],'f',([-1,2],))['output_repr']=='-1'
    skip=next(m for m in rows if m['operator']=='SKIP_THEN')
    assert b.replay(src,'f',([0],))['status']=='ok'
    assert b.replay(skip['source'],'f',([0],))['status']=='ValueError'
    assert all(m['origin']=='implementation' and m['syntactically_valid'] for m in rows)

def test_dsl_equality_vs_proper_containment():
    a={'op':'arg','index':0};c={'op':'arg','index':1}
    subset={'op':'subset','args':[c,a]};eq={'op':'eq','args':[a,c]}
    s.validate(subset,2,False)
    assert s.truth(subset,([1,2],[1,2])) is True
    assert s.truth(subset,([1,2,3],[1,2])) is True
    assert s.truth(eq,([1,2,3],[1,2])) is False
    assert s.truth(subset,([1],[1,2])) is False

def test_opaque_recursion_eval_float():
    for src in ['def f(x):\n return f(x-1)\n','def f(x):\n return eval(x)\n','def f(x):\n return x/2\n']:
        assert not b.build(src,'f')['structural_supported']

def test_empty_aggregation_requirement_and_concrete_failure():
    src='def f(xs):\n    neg=[x for x in xs if x<0]\n    pos=[x for x in xs if x>0]\n    if not neg: return (None,min(pos))\n    return (max(neg),None)\n'
    ir=b.build(src,'f');assert any(r['kind']=='NONEMPTY' and r['expression']=='pos' for r in ir['requirements'])
    r=b.replay(src,'f',([0,0],));assert r['status']=='ValueError'
    assert any(e.get('exception')=='ValueError' for e in r['events'])

def test_dsl_short_circuit_and_invalid_inputs():
    q={'op':'and','args':[{'op':'const','value':False},{'op':'eq','args':[{'op':'min','args':[{'op':'arg','index':0}]},{'op':'const','value':0}]}]}
    assert s.truth(q,([],)) is False
    import pytest
    with pytest.raises(ValueError):s.validate({'op':'eval','args':[]},1)
    with pytest.raises(ValueError):s.validate({'op':'result'},1,False)


def test_proposal_rejects_valid_json_with_wrong_container_shapes():
    import pytest
    for raw in ('[]','null','{"obligations":{}}','{"concepts":["bad"]}'):
        with pytest.raises(ValueError):s.parse(raw)


def test_malformed_dsl_and_quote_are_rejections():
    import json,pytest
    with pytest.raises(ValueError):s.validate({'op':[]},1)
    ir=b.build('def f(xs):\n    """Return the number of items."""\n    return len(xs)\n','f')
    obs,errors=s.obligations(json.dumps({'obligations':[{'quote':[],'domain':{},'relation':{}}]}),ir)
    assert obs==[] and len(errors)==1


def test_positive_quoted_obligation_and_source_binding():
    import json
    src='def f(xs):\n    """Return the number of items."""\n    if not xs: return 0\n    return len(xs)\n'
    ir=b.build(src,'f');arg={'op':'arg','index':0};result={'op':'result'}
    relation={'op':'eq','args':[result,{'op':'len','args':[arg]}]}
    obs,errors=s.obligations(json.dumps({'obligations':[{'quote':'Return the number of items.','domain':{'op':'const','value':True},'relation':relation}]}),ir)
    assert len(obs)==1 and errors==[] and obs[0]['span']==[0,27]
    mut=b.mutants(src,'f')[0]
    card={'family':'BOUNDARY','obligation_id':'R0','block_ids':[mut['target']],'mutant_id':mut['id'],
          'discriminator':{'op':'eq','args':[{'op':'len','args':[arg]},{'op':'const','value':0}]},
          'reasoning':{k:'Explicit candidate statement' for k in ('code_claim','required_condition','path_guarantees','unresolved_obligation','predicted_effect')}}
    cards,errors=s.cards(json.dumps({'concepts':[card]}),ir,obs,[mut]);assert len(cards)==1 and not errors
    card['block_ids']=['invented']
    cards,errors=s.cards(json.dumps({'concepts':[card]}),ir,obs,[mut]);assert cards==[] and errors
