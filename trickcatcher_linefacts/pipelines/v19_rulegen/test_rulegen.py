import json
from . import behavior_experiment as e


def candidate(task):
    return json.loads((e.PARENT/'selection_pilot/prepared'/str(task)/'candidates_result.json').read_text())


def test_all_models_keep_frozen_rule_first():
    for task in e.CFG['task_ids']:
        c=candidate(task);cards=e.rule_cards(c)
        if c['pool']:
            selected=next(r for r in c['pool'] if r['id']==c['rule_first'])
            assert cards and all(r['model']==selected['model'] for r in cards)
        else:assert not cards


def test_no_concrete_witness_in_concept_guidance():
    t=e.tasks()[-1];cards=e.rule_cards(candidate(t['task']))
    p={'usable':True,'pseudocode':'FLOW'};pool=[{'input_repr':'SECRET_WITNESS'}]
    concept=e.guidance(t,'behavior+concept',p,cards,pool,0)
    assert 'SECRET_WITNESS' not in concept
    assert 'SECRET_WITNESS' in e.guidance(t,'toolinput',p,cards,pool,0)
    assert e.guidance(t,'behavior',p,cards,pool,0)=='FLOW'


def test_common_pool_is_deterministic_and_capped():
    for t in e.tasks():
        c=candidate(t['task']);a=e.common_pool(t,c)
        assert a==e.common_pool(t,c) and len(a)<=12


def test_unsupported_fallback_matches():
    t=e.tasks()[0];p={'usable':False}
    assert e.guidance(t,'behavior',p,[],[],0)==e.guidance(t,'behavior+concept',p,[],[],0)
