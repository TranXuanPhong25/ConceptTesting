import pytest


def test_tool_membership_accepts_native_predicates_that_failed_in_full_run():
    from final.src.modular.tool_sampling.membership import evaluate
    assert evaluate('isinstance(n, float) and n >= 0',{'n':0.5}) is True
    assert evaluate('n is None',{'n':None}) is True
    assert evaluate("len(s)>0 and all(c in 'aeiouAEIOU' for c in s)",{'s':'Ae'}) is True
    assert evaluate("len(s)>1 and 'y' in s[:-1] and s[-1]!='y'",{'s':'yab'}) is True
    assert evaluate('len(s)>0 and s.isupper()',{'s':'ABC'}) is True
    assert evaluate('all(x < limit for x in xs)',{'xs':[1,2],'limit':3}) is True
    assert evaluate('any(x % 2 == 0 for x in xs)',{'xs':[1,2]}) is True


@pytest.mark.parametrize('text',[
    "__import__('os').getcwd() == ''", "open('/etc/passwd').read() == ''",
    's.__class__ is str',"s.format_map({}) == ''",'xs.append(1) is None',
    '(lambda: True)()', '(x := 1) == 1', 'getattr(s, "upper")() == s',
])
def test_membership_rejects_io_private_attributes_mutation_and_arbitrary_code(text):
    from final.src.modular.tool_sampling.membership import expression
    with pytest.raises(ValueError):expression(text,{'s','xs'})


def test_sandbox_timeout_is_an_error_and_next_request_still_works():
    from final.src.modular.tool_sampling.membership import evaluate
    with pytest.raises(ValueError,match='timeout'):
        evaluate('all(x>=0 for x in range(10**12))',{})
    assert evaluate('s.isupper()',{'s':'ABC'}) is True


def test_non_boolean_result_is_rejected_even_when_python_valid():
    from final.src.modular.tool_sampling.membership import evaluate
    with pytest.raises(ValueError,match='predicate_must_return_bool'):
        evaluate('s.upper()',{'s':'abc'})


def test_one_unsupported_target_retains_good_targets_and_candidate_inputs():
    from final.src.modular.tests.test_tool_sampling import model,builder
    from final.src.modular.tool_sampling.schema import parse_preparation
    raw=model()
    raw['targets'].append({**raw['targets'][0],'id':'unsupported','predicate':'custom_logic(a)'})
    prepared=parse_preparation(raw,builder())
    assert prepared['targets'][0]['support']=='supported'
    assert prepared['targets'][-1]['support']=='unsupported'
    assert prepared['inputs']==raw['inputs']


def test_one_unsupported_target_does_not_disable_real_hypothesis_sampler(tmp_path):
    from final.src.modular.tests.test_tool_sampling import model,budgets
    from final.src.modular.context import TaskContext,PipelineSettings
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.generators.tools import ToolInputGenerator
    raw=model()
    raw['targets'].append({**raw['targets'][0],'id':'unknown_target','predicate':'custom_logic(a)'})
    config=budgets();config['arms']=['tool_direct','tool_hypothesis']
    context=TaskContext({'task_id':'HumanEval/7','entry_point':'f','prompt':'def f(a:int,b:int):\n pass\n'},
        {'contract':''},ArtifactStore(tmp_path),PipelineSettings())
    generator=ToolInputGenerator(config,preparations={'HumanEval/7':raw})
    context.inputs=generator.generate(context)
    generator.validate_generation([context])
    batch=context.inputs['arms']['tool_hypothesis']
    assert batch['inputs']
    assert batch['preparation']['targets'][-1]['support']=='unsupported'
    assert all(not row['membership']['unknown_target']['hit'] for row in batch['candidate_ledger'] if row.get('membership'))


@pytest.mark.parametrize('predicate',['len(a)>0 and a.isupper()','bool(a)','a.isupper() if a else False'])
def test_schema_accepts_boolean_methods_in_boolean_combinations(predicate):
    from final.src.modular.tool_sampling.schema import validate_expression
    validate_expression(predicate,{'a':'str'})


def test_parent_deadline_covers_pipe_write_to_stalled_worker():
    import subprocess,sys,time
    from final.src.modular.tool_sampling.membership import PredicateSandbox
    sandbox=PredicateSandbox()
    sandbox.process=subprocess.Popen([sys.executable,'-c',
        'import time,sys;time.sleep(3);sys.stdin.readline();print(\'{"result":true}\',flush=True)'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,bufsize=0)
    started=time.monotonic()
    try:
        with pytest.raises(ValueError,match='timeout'):
            sandbox.evaluate('bool(s)',{'s':'a'*100000})
        assert time.monotonic()-started<2.8
    finally:sandbox.close()


def test_unsupported_target_does_not_erase_supported_target_selection_priority():
    from final.src.modular.tool_sampling.selection import select_suite
    class Ledger:
        model={'targets':[{'id':'common','kind':'class','support':'supported'},
            {'id':'rare','kind':'class','support':'supported'},
            {'id':'unknown','kind':'class','support':'unsupported'}]}
        def __init__(self):
            self.rows=[]
            for key,rare in [('a',False),('b',True)]:
                self.rows.append({'dedup_group':key,'candidate_id':key,'errors':[],
                    'canonical_args':{'args':'(1,)','kwargs':'{}'},'selected':False,
                    'membership':{'common':{'context':'true','target':'true','hit':True},
                      'rare':{'context':'true','target':'true' if rare else 'false','hit':rare},
                      'unknown':{'context':'true','target':'unknown','hit':False}}})
        def pool(self):return self.rows
    chosen=select_suite(Ledger(),1)
    assert chosen[0]['candidate_id']=='b'


def test_saved_response_audit_distinguishes_usable_partial_from_fully_supported():
    from final.src.modular.tool_sampling.response_audit import inspect_response
    from final.src.modular.tests.test_tool_sampling import model,builder
    raw=model();raw['targets'].append({**raw['targets'][0],'id':'custom','predicate':'custom_logic(a)'})
    result=inspect_response(raw,builder())
    assert result['valid'] and not result['requires_new_preparation']
    assert result['fully_supported'] is False
    assert result['unsupported_target_ids']==['custom']
    assert result['issues'] and all(issue['severity']=='unsupported_target' for issue in result['issues'])
