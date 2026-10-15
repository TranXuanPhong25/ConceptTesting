import json
import pytest
from . import candidate_models as cm,templates


def base(args,result):return dict(args=args,result=result)


def test_pair_models_survive_base_and_diverge_off_base():
    evidence=[base(([3],[1]),[2]),base(([5,4],[2,1]),[3,3])]
    models=cm.enumerate_models(evidence,'Return absolute differences between corresponding positions.',2)
    pool,_=cm.retain(models,evidence,'Return absolute differences between corresponding positions.')
    transforms={r['model']['params'].get('transform') for r in pool if r['model']['template']=='MAP'}
    assert {'sub','abs_sub'}<=transforms
    menu=cm.display(pool,[([1],[3]),([2],[0])],19)
    assert len({cm.fingerprint(r['model'],[([1],[3])]) for r in menu})>=2
    assert pool[0]['model']['params']['transform']=='abs_sub'
    assert cm.display(pool,[([1],[3]),([2],[0])],19)==menu


def test_ordering_and_duplicate_rules_are_enumerated_not_task_mapped():
    evidence=[base(([1,2],),True),base(([2,1],),True),base(([1,3,2],),False)]
    models=cm.enumerate_models(evidence,'Monotonically increasing or decreasing, equal values allowed.',1)
    pool,_=cm.retain(models,evidence,'Monotonically increasing or decreasing, equal values allowed.')
    expected=[r for r in pool if r['model']['template']=='ORDER_CHECK' and r['model']['params']['direction']=='either' and r['model']['params']['max_count'] is None]
    assert expected
    assert templates.expected(expected[0]['model'],([1,1,1],)) is True
    assert any(templates.observe(r['model'],([1,1,1],))!=templates.observe(expected[0]['model'],([1,1,1],)) for r in pool)


def test_filter_sorted_multiplicity_candidates_are_available():
    evidence=[base((['a','aa','zz'],),['aa','zz'])]
    spec='Remove strings of odd length, sort by length and lexical order, preserving repeated occurrences.'
    pool,_=cm.retain(cm.enumerate_models(evidence,spec,1),evidence,spec)
    exact=[r for r in pool if r['model']['template']=='FILTER' and r['model']['params']['predicate']=='length_even' and
           r['model']['params']['order']=='length_lex' and not r['model']['params']['distinct']]
    assert exact
    assert templates.expected(exact[0]['model'],(['zz','aa','zz','a'],))==['aa','zz','zz']


def test_integer_scalar_is_explicitly_unsupported_and_no_vacuous_base():
    assert cm.enumerate_models([base((3,),True)],'Check a mathematical property of the integer.',1)==[]
    assert cm.enumerate_models([],'No public observations.',1)==[]


def test_menu_hides_rule_rank_and_choice_parser_does_not_repair():
    model=templates.normalize(dict(template='MAP',transform='swapcase'),1)
    menu=[dict(id='C2',model_id='M0',model=model)]
    text=cm.choice_messages('Flip character case.',menu)[-1]['content']
    assert 'model_id' not in text and 'M0' not in text
    assert cm.parse_choice('```json\n{"choice":"C2"}\n```',menu)=='C2'
    assert cm.parse_choice('{"choice":"NONE"}',menu)=='NONE'
    with pytest.raises(ValueError):cm.parse_choice('{"choice":"C0"}',menu)
    with pytest.raises(ValueError):cm.parse_choice('C2',menu)


def test_structured_paired_calls_use_literal_semantics_without_hidden_aliases():
    inputs=cm.structured_inputs([base(([1],[2]),[1])],2,19)
    assert all(type(args) is tuple and len(args)==2 for args in inputs)
    equal=next(args for args in inputs if args[0]==args[1] and type(args[0]) is list)
    assert equal[0] is not equal[1]
    assert any(args==([0],[1]) for args in inputs)


def test_vocabulary_and_scoped_components():
    alphabets,tokens=cm.vocabularies("Count occurrences of the word 'I'.")
    assert 'I' in tokens and '2357BD' in alphabets
    evidence=[base(([-1,2],),(-1,2)),base(([1,3],),(None,1))]
    pool,_=cm.retain(cm.enumerate_models(evidence,'largest negative and smallest positive integers',1),evidence,'largest negative and smallest positive integers')
    assert {r['model']['params']['component'] for r in pool}=={0,1}


def test_gold_audit_requires_full_choice_freeze(tmp_path,monkeypatch):
    from . import selection_experiment as e
    monkeypatch.setattr(e,'ROOT',tmp_path)
    with pytest.raises(RuntimeError,match='freeze all choices first'):e.audit(1)
