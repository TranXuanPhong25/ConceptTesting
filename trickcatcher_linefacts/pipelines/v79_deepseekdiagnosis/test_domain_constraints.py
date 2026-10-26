import ast
import copy
import itertools
import time

import pytest
import z3

from .domain_constraints import compile_domain,public_domain,check_domain,constraints
from .joint_constructor import solve_inputs,verify_input
from .predicates import SymbolicString
from .predicate_compiler import compile_condition
from .semantic_contract import admit
from .evidence_gate import select_evidence,assess_context
from .test_contractfix import REQ,proposal


def request(spec, source='def f(word1, word2):\n    return []\n', examples=None):
    return {'case_id':'authored','source':source,'entry':'f','spec':spec,
            'public_examples':examples or [{'arguments':"('abc', 'ab')",'expected':'[]'}]}


PAIR='Return a sequence.\nConstraints:\n\n1 <= word2.length < word1.length <= 3 * 10^5\nword1 and word2 consist only of lowercase English letters.'


def test_domain_quotes_bind_exact_spec_lines_and_source():
    req=request(PAIR);before=copy.deepcopy(req);domain=public_domain(req)
    assert domain['status']=='complete'and req==before
    for row in domain['rules']:
        assert req['spec'].splitlines()[row['line']]==row['quote']
        assert row['binding_sha256']==domain['binding_sha256']
    assert compile_domain(dict(req,source=req['source']+'\n'))['binding_sha256']!=domain['binding_sha256']
    assert compile_domain(dict(req,spec=PAIR+'\n'))['binding_sha256']!=domain['binding_sha256']


def test_pair_domain_matches_explicit_python_on_lengths_and_alphabet():
    domain=public_domain(request(PAIR))
    words=['','a','b','aa','abc','A','1','é']
    for a,b in itertools.product(words,repeat=2):
        expected=1<=len(b)<len(a)<=300000 and all('a'<=c<='z'for c in a+b)
        assert check_domain(domain,(a,b))['passed']==expected
        conditions=constraints(domain,[SymbolicString(map(ord,a)),SymbolicString(map(ord,b))],symbolic=True)
        assert z3.is_true(z3.simplify(z3.And(*conditions)))==expected


def test_invalid_shapes_are_pruned_before_query_and_candidate_budgets():
    domain=public_domain(request(PAIR));trigger={'op':'literal','value':True}
    solved=solve_inputs([('abc','ab')],trigger,time.monotonic()+5,max_candidates=2,max_queries=2,domain=domain)
    assert solved['inputs']and len(solved['inputs'])<=2
    assert solved['domain_pruned_shapes']>0 and solved['queries']<=2 and solved['domain_mismatches']==0
    assert all(check_domain(domain,args)['passed']for args in solved['inputs'])
    assert all(1<=len(b)<len(a)for a,b in solved['inputs'])


def test_domain_does_not_expand_inherited_search_bounds():
    spec='Return.\nConstraints:\n7 <= word1.length <= 100\n1 <= word2.length < word1.length'
    domain=public_domain(request(spec,examples=[{'arguments':"('abcdefgh','ab')",'expected':'[]'}]))
    solved=solve_inputs([('abcdefgh','ab')],{'op':'literal','value':True},time.monotonic()+3,domain=domain)
    assert not solved['inputs']and solved['queries']==0 and solved['domain_pruned_shapes']==49
    assert solved['domain']['max_length']==6


def test_numeric_array_elements_and_same_line_alias_are_enforced():
    req=request('Return.\nConstraints:\n1 <= n == nums.length <= 10^5\n1 <= nums[i] <= 10^9',
                'def f(nums):\n    return 0\n',[{'arguments':'([1,2],)','expected':'0'}])
    domain=public_domain(req)
    assert check_domain(domain,([1,2],))['passed']
    for args in (([],),([0],),([-1,2],),([True],)):
        assert not check_domain(domain,args)['passed']
    solved=solve_inputs([([1,2],)],{'op':'literal','value':True},time.monotonic()+5,max_candidates=5,domain=domain)
    assert solved['inputs']and all(xs and all(1<=x<=16 for x in xs)for(xs,)in solved['inputs'])


def test_digits_alphabet_intersects_the_search_alphabet():
    req=request('Return.\nConstraints:\n1 <= s.length <= 10^5\ns consists of digits only.',
                'def f(s):\n    return 0\n',[{'arguments':"('123',)",'expected':'0'}])
    domain=public_domain(req)
    node,_=compile_condition("arg0 != '0'",1)
    solved=solve_inputs([('123',)],node,time.monotonic()+5,max_candidates=5,domain=domain)
    assert solved['inputs']and all(s and all('0'<=c<='9'for c in s)and s!='0'for(s,)in solved['inputs'])
    assert not check_domain(domain,('abc',))['passed']


SQUARE='''The square has corners at (0, 0), (0, side), (side, 0), and (side, side).
Constraints:
1 <= side <= 10^9
4 <= points.length <= min(4 * side, 15 * 10^3)
points[i] == [xi, yi]
The input is generated such that:
points[i] lies on the boundary of the square.
All points[i] are unique.
4 <= k <= min(25, points.length)'''


def square_request(spec=SQUARE):
    return request(spec,'def f(side, points, k):\n    return 0\n',
                   [{'arguments':'(2, [[0,0],[0,2],[2,0],[2,2]], 4)','expected':'0'}])


def test_square_rules_match_concrete_geometry_and_uniqueness():
    domain=public_domain(square_request())
    good=(2,[[0,0],[0,2],[2,0],[2,2]],4)
    assert check_domain(domain,good)['passed']
    bad=[(2,[[0,0],[0,2],[2,0],[1,1]],4), (2,[[0,0],[0,2],[2,0],[2,2]],5),
         (2,[[0,0],[0,2],[2,0],[0,0]],4), (2,[[-1,0],[0,2],[2,0],[2,2]],4),
         (2,[[0,0,1],[0,2],[2,0],[2,2]],4)]
    assert all(not check_domain(domain,args)['passed']for args in bad)
    for args in [good,*bad]:
        conditions=constraints(domain,args,symbolic=True)
        assert z3.is_true(z3.simplify(z3.And(*conditions)))==check_domain(domain,args)['passed']


def test_square_solver_constructs_only_domain_valid_points():
    domain=public_domain(square_request())
    solved=solve_inputs([(2,[[0,0],[0,2],[2,0],[2,2]],4)],{'op':'literal','value':True},
                        time.monotonic()+6,max_candidates=3,domain=domain)
    assert solved['inputs']and all(check_domain(domain,args)['passed']for args in solved['inputs'])


@pytest.mark.parametrize('text',[
    'At least two characters must differ.',
    'unknown.length > 0',
    'n >= 1',  # No explicit same-line equality binding to an argument length.
    '__import__("os").system("true") == 0',
    'len(word1) == sum(range(10))',
    'word1.length > 10^100',
])
def test_unsupported_constraint_blocks_instead_of_silently_becoming_true(text):
    req=request('Return.\nConstraints:\n'+text)
    domain=compile_domain(req)
    assert domain['status']=='incomplete'and domain['unsupported']
    assert not check_domain(domain,('abc','ab'))['passed']
    with pytest.raises(ValueError,match='unsupported_or_inconsistent_public_domain'):
        public_domain(req)


def test_square_origin_must_be_explicit_and_missing_sections_remain_qualified():
    assert compile_domain(square_request(SQUARE.replace('corners at','vertices at')))['status']=='incomplete'
    d=compile_domain(request('Return a sequence.'))
    assert d['status']=='no_explicit_constraints'and d['coverage']=='no_constraints_section'
    assert check_domain(d,('a','b'))['passed']  # No inferred bounds from the examples.


def test_native_verifier_blocks_invalid_domain_before_program_execution(monkeypatch):
    from . import joint_constructor
    req=dict(REQ,spec=REQ['spec']+'\nConstraints:\n1 <= x <= 16')
    hypotheses,errors=admit(req,[proposal(req)])
    assert hypotheses and not errors
    def forbidden(*a,**kw):raise AssertionError('must not execute invalid input')
    monkeypatch.setattr(joint_constructor,'replay',forbidden)
    run=verify_input(req,hypotheses[0],(0,),{'repeat_seeds':[1,2],'repeats_per_program_seed':2},time.monotonic()+3)
    assert run['status']=='invalid_input_domain'and run['native_executions']==0


def test_selection_and_gate_recheck_forged_domain_witness():
    from .test_evidence_gate import construction,run
    req=dict(REQ,spec=REQ['spec']+'\nConstraints:\n1 <= x <= 16')
    report=construction([run('(0,)',True)])
    assert not select_evidence(req,report)['evidence']
    forged={'evidence':[{'hypothesis':report['records'][0]['hypothesis'],
                         'public_consistency':{'status':'passed'},'witnesses':[run('(0,)',True)]}]}
    assert not assess_context(req,forged)['passed']


def test_domain_and_condition_content_unchanged_from_v69():
    from .semantic_contract import writer_packet
    from ..v69_typedwriter.semantic_contract import writer_packet as previous
    current=writer_packet(REQ);old=previous(REQ)
    for key in ('source','spec_clauses','sites','public_examples','argument_types','condition_language','edit_forms'):
        assert current[key]==old[key]
    assert current['hypothesis_fields']==old['output_fields']
    assert set(current['output_schema'])=={'hypotheses'}
    assert current['empty_output']=={'hypotheses':[]}


def test_domain_receipt_does_not_accept_wrong_argument_count():
    domain=public_domain(request(PAIR))
    assert not check_domain(domain,('abc','ab','extra'))['passed']
    assert not check_domain(domain,('abc',))['passed']
    empty=public_domain(request('Return.'))
    assert not check_domain(empty,())['passed']
