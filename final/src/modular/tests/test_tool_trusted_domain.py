"""Trusted admission, safe projections and dependent construction regressions."""
import pytest

from final.src.modular.common.predicates import evaluate


CONTRACT44 = '''
    assert type(x) == int and type(base) == int, "invalid inputs"
    assert x >= 0, "invalid inputs"
    assert 2 <= base <= 9, "invalid inputs"
'''
CONTRACT11 = '''
    assert isinstance(a, str) and isinstance(b, str), "invalid inputs"
    assert len(a) == len(b), "invalid inputs"
    assert set(a).issubset({"0", "1"}) and set(b).issubset({"0", "1"}), "invalid inputs"
'''
CONTRACT120 = '''
    assert type(arr) == list, "invalid inputs"
    assert 1 <= len(arr) <= 1000, "invalid inputs"
    assert all(-1000 <= x <= 1000 for x in arr), "invalid inputs"
    assert type(k) == int, "invalid inputs"
    assert 0 <= k <= len(arr), "invalid inputs"
'''
CONTRACT137 = '''
    assert isinstance(a, (int, float, str)), "invalid inputs"
    assert isinstance(b, (int, float, str)), "invalid inputs"
    try:
        float(str(a).replace(",", "."))
        float(str(b).replace(",", "."))
    except ValueError: raise Exception("invalid inputs")
'''


@pytest.mark.parametrize('values,expected', [({'x':-1,'base':2}, False), ({'x':0,'base':1},False),
    ({'x':0,'base':10},False), ({'x':0,'base':2},True), ({'x':8,'base':3},True), ({'x':True,'base':2},False)])
def test_compile_trusted_domain44_enforces_every_assert(values, expected):
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    result = compile_domain(CONTRACT44, ['x', 'base'])
    assert result['status'] == 'supported'
    assert evaluate(result['expression'], values) is expected


@pytest.mark.parametrize('contract,names,accepted,rejected', [
    (CONTRACT11, ['a','b'], {'a':'010','b':'110'}, {'a':'abc','b':'def'}),
    (CONTRACT120, ['arr','k'], {'arr':[-1000,1000],'k':2}, {'arr':[1001],'k':1}),
    (CONTRACT137, ['a','b'], {'a':2.5,'b':'2,3'}, {'a':'abc','b':1}),
])
def test_supported_trusted_domains_cover_real_string_list_numeric_cases(contract,names,accepted,rejected):
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    domain = compile_domain(contract, names)
    assert domain['status'] == 'supported'
    assert evaluate(domain['expression'], accepted) is True
    assert evaluate(domain['expression'], rejected) is False


def test_unsupported_trusted_clause_is_not_silently_dropped():
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    result = compile_domain(CONTRACT44+'\n    assert arbitrary_helper(x)\n', ['x','base'])
    assert result['status'] == 'unsupported'
    assert result['expression'] is None and result['unsupported']


def test_safe_domain_helpers_preserve_numeric_repr_and_enforce_limits():
    assert evaluate('is_numeric(a) and numeric_value(a) == numeric_value(b)', {'a':'2,3','b':2.3})
    assert not evaluate('is_numeric(a)', {'a':'abc'})
    assert not evaluate('is_numeric(a)', {'a':True})
    assert evaluate('chars_in(a, "01") and all_in_range(xs, -1000, 1000)', {'a':'010','xs':[-1000,1000]})
    with pytest.raises(ValueError):
        evaluate('chars_in(a, "01")', {'a':'0'*1001})
    with pytest.raises(ValueError):
        evaluate('all_in_range(xs, 0, 1)', {'xs':[0]*1001})
    with pytest.raises(ValueError):
        evaluate('a.replace("a", "b") == "b"', {'a':'a'})


def test_len_dependent_bound_uses_only_previously_generated_parameter():
    from final.src.modular.tool_sampling.constructors import bound_value
    assert bound_value('len(arr)', {'arr':[1,2,3]}) == 3
    assert bound_value('len(a) - 1', {'a':'010'}) == 2
    with pytest.raises(ValueError):
        bound_value('arr.pop()', {'arr':[1,2]})
    with pytest.raises(ValueError):
        bound_value('sum(arr)', {'arr':[1,2]})


def test_domain_is_pinned_by_schema_and_local_validation():
    from final.src.modular.call_builder import CallBuilder
    from final.src.modular.tool_sampling.schema import preparation_schema, parse_preparation
    from final.src.modular.tests.test_tool_sampling import model
    builder = CallBuilder.for_source('def f(a:int, b:int):\n    pass\n', 'f')
    domain = 'is_int(a) and is_int(b) and a >= 0 and 2 <= b <= 9'
    schema = preparation_schema(builder, trusted_domain=domain)
    assert schema['properties']['domain']['const'] == domain
    raw = model()
    raw['domain'] = 'is_int(a) and is_int(b)'
    with pytest.raises(ValueError):
        parse_preparation(raw, builder, trusted_domain=domain)
    raw['domain'] = domain
    assert parse_preparation(raw, builder, trusted_domain=domain)['domain'] == domain


def test_generator_blocks_luna44_weakened_domain_and_preserves_raw(tmp_path):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    from final.src.modular.tests.test_tool_sampling import budgets
    spec = {'types': {'x':'int','base':'int'}, 'domain':'is_int(x) and is_int(base)',
        'domain_source_quote':'contract', 'strategies':{'x':{'kind':'int'},'base':{'kind':'int'}},
        'targets':[], 'factors':{}, 'inputs':[{'arguments':{'x':-1,'base':2}}]}
    context = TaskContext({'task_id':'HumanEval/44','entry_point':'f','prompt':'def f(x:int, base:int):\n pass\n'},
        {'contract': CONTRACT44},ArtifactStore(tmp_path), PipelineSettings())
    generator = ToolInputGenerator(budgets(),preparations={'HumanEval/44':spec})
    result = generator.generate(context)
    batch = result['arms']['tool_direct']
    assert batch['preparation_error'] is not None
    assert batch['domain_authority']['source'] == 'trusted_input_admission'
    context.inputs = result
    with pytest.raises(ValueError,match='tool_generation_gate'):
        generator.validate_generation([context])
    assert spec['domain'] == 'is_int(x) and is_int(base)'


def test_generator_skips_model_when_trusted_contract_is_unsupported(tmp_path):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    from final.src.modular.tests.test_tool_sampling import budgets
    class Forbidden:
        def token_count(self,*args):
            pytest.fail('No model call/tokenization for unsupported trusted admission')
    context = TaskContext({'task_id':'HumanEval/44','entry_point':'f','prompt':'def f(x:int, base:int):\n pass\n'},
        {'contract': CONTRACT44+'\n    assert unknown(x)\n'}, ArtifactStore(tmp_path),PipelineSettings(),calls=Forbidden())
    raw, failure = ToolInputGenerator(budgets()).prepare(context)
    assert raw is None and failure['code'] == 'invalid_response'
    assert 'unsupported_trusted_domain' in failure['detail']


def test_string_constructor_supports_joint_equal_length_without_arbitrary_cap():
    from hypothesis import given, settings, Phase
    from final.src.modular.tool_sampling.constructors import strategy
    from final.src.modular.tool_sampling.schema import preparation_type
    from final.src.modular.call_builder import CallBuilder
    from final.src.modular.tests.test_tool_sampling import model
    # Schema accepts data-only len(previous) bounds, constructor preserves length.
    raw = model()
    raw['types'] = {'a':'str','b':'str'}
    raw['strategies'] = {'a':{'kind':'sampled','values':['','0','010']},
                         'b':{'kind':'str','min_size':'len(a)','max_size':'len(a)','alphabet':'01'}}
    builder = CallBuilder.for_source('def f(a:str,b:str):\n pass\n','f')
    preparation_type(builder).model_validate(raw)
    @settings(max_examples=4, phases=(Phase.generate,), database=None)
    @given(strategy(raw['strategies']['b'], {'a':'010'}))
    def check(value):
        assert len(value) == 3 and set(value) <= {'0','1'}
    check()


def test_subset_or_quantifier_without_container_type_guard_is_unsupported():
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    for contract in ['assert set(a).issubset({"0","1"})']:
        # Empty list/string can satisfy the original iterable check; a typed
        # helper must not silently strengthen it without known container type.
        assert compile_domain(contract, ['a'])['status'] == 'unsupported'


@pytest.mark.parametrize('number,contract,source,types,strategies,inputs', [
    (44,CONTRACT44,'def f(x:int, base:int):\n pass\n', {'x':'int','base':'int'},
     {'x':{'kind':'int','min':0},'base':{'kind':'int','min':2,'max':9}},
     [{'x':0,'base':2},{'x':8,'base':3}]),
    (11,CONTRACT11,'def f(a:str,b:str):\n pass\n', {'a':'str','b':'str'},
     {'a':{'kind':'sampled','values':['','0','010']},
      'b':{'kind':'str','min_size':'len(a)','max_size':'len(a)','alphabet':'01'}},
     [{'a':'010','b':'110'}]),
    (120,CONTRACT120,'def f(arr,k):\n pass\n', {'arr':'list[int]','k':'int'},
     {'arr':{'kind':'list','min_size':1,'max_size':1000,'elements':{'kind':'int','min':-1000,'max':1000}},
      'k':{'kind':'int','min':0,'max':'len(arr)'}}, [{'arr':[-1000,1000],'k':2}]),
    (137,CONTRACT137,'def f(a,b):\n pass\n', {'a':'any','b':'any'},
     {'a':{'kind':'sampled','values':[1,2.5,'2,3','1']}, 'b':{'kind':'sampled','values':[1,2.5,'2,3','1']}},
     [{'a':2.5,'b':'2,3'}]),
])
def test_all_four_corrected_contracts_construct_clean_inputs_without_oracle(tmp_path,number,contract,source,types,strategies,inputs):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings, TaskContext
    from final.src.modular.tool_sampling import ToolInputGenerator
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    from final.src.modular.tool_sampling.gate import treatment_status
    from final.src.modular.tests.test_tool_sampling import budgets
    domain = compile_domain(contract, types)['expression']
    spec = {'types':types,'domain':domain,'domain_source_quote':'Copied trusted admission',
            'strategies':strategies,'targets':[], 'factors':{}, 'inputs':[{'arguments':item} for item in inputs]}
    if number == 137:
        spec['targets'] = [{'id':'numeric_order','kind':'rule','predicate':'numeric_value(a) > numeric_value(b)',
                           'context':'True','origin':'spec','source_quote':'returns the larger variable in its given variable type'}]
    config = budgets()
    config['arms'] = ['tool_direct','tool_hypothesis']
    config['draws'] = 8
    task_id = f'HumanEval/{number}'
    context = TaskContext({'task_id':task_id,'entry_point':'f','prompt':source},{'contract':contract},ArtifactStore(tmp_path),PipelineSettings())
    generator = ToolInputGenerator(config,preparations={task_id:spec})
    context.inputs = generator.generate(context)
    batch = context.inputs['arms']['tool_hypothesis']
    assert batch['preparation_error'] is None
    assert batch['domain_authority']['status'] == 'supported'
    assert treatment_status('tool_hypothesis',batch)['status'] == 'exercised'
    assert all(not row['errors'] for row in batch['candidate_ledger'])
    generator.validate_generation([context])
    assert not list(tmp_path.glob('**/oracle_*.json'))


def test_schema_pass_cannot_override_pinned_domain_receipt_at_gate():
    from final.src.modular.tool_sampling.gate import treatment_status
    batch = {'preparation_error':None,'preparation':{'domain':'True'},
             'domain_authority':{'status':'supported','expression':'x >= 0'}}
    assert treatment_status('tool_direct',batch)['status'] == 'invalid_preparation'


@pytest.mark.parametrize('cached_authority', [None, {'source':'trusted_input_admission','status':'supported','expression':'True'}])
def test_gate_recomputes_trusted_authority_instead_of_trusting_cached_batch(tmp_path,cached_authority):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import TaskContext,PipelineSettings
    from final.src.modular.tool_sampling.gate import validate_generation
    context=TaskContext({'task_id':'HumanEval/44','entry_point':'f','prompt':'def f(x:int,base:int):\n pass\n'},
        {'contract':CONTRACT44},ArtifactStore(tmp_path),PipelineSettings())
    batch={'preparation_error':None,'preparation':{'domain':'True'},'candidate_ledger':[],'tool_receipts':[]}
    if cached_authority is not None:batch['domain_authority']=cached_authority
    context.inputs={'arms':{'tool_direct':batch}}
    with pytest.raises(ValueError,match='tool_generation_gate'):
        validate_generation([context])
    assert context.artifacts.read('tool_generation_gate.json')['ready'] is False


def test_trusted_compiler_handles_depth_limits_and_shadowed_names():
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    deep=compile_domain('assert '+'not '*400+'True',[])
    assert deep['status']=='unsupported' and deep['expression'] is None
    shadowed=compile_domain('assert type(x) == int',['x','int'])
    assert shadowed['status']=='unsupported' and shadowed['expression'] is None


def test_llm_sampling_types_cannot_reject_trusted_polymorphic_seed(tmp_path):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import TaskContext,PipelineSettings
    from final.src.modular.tool_sampling import ToolInputGenerator
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    from final.src.modular.tests.test_tool_sampling import budgets
    domain=compile_domain(CONTRACT137,['a','b'])['expression']
    spec={'types':{'a':'str','b':'str'},'domain':domain,'domain_source_quote':'trusted',
          'strategies':{'a':{'kind':'sampled','values':['1','2,3']},'b':{'kind':'sampled','values':['1','2,3']}},
          'targets':[],'factors':{},'inputs':[{'arguments':{'a':2.5,'b':'2,3'}}]}
    context=TaskContext({'task_id':'HumanEval/137','entry_point':'f','prompt':'def f(a,b):\n pass\n'},
        {'contract':CONTRACT137},ArtifactStore(tmp_path),PipelineSettings())
    generator=ToolInputGenerator(budgets(),preparations={'HumanEval/137':spec})
    batch=generator.generate(context)['arms']['tool_direct']
    row=batch['candidate_ledger'][0]
    assert not row['errors'] and row['domain']=='true'
    assert batch['preparation']['types']=={'a':'str','b':'str'}
    assert batch['preparation']['admission_types']=={'a':'any','b':'any'}


def test_existing_smoke12_admission_contracts_have_no_silent_unsupported_clauses():
    from final.src.benchmarks.datasets import load_tasks,load_metadata
    from final.src.modular.call_builder import CallBuilder
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    selected={0,5,11,18,22,26,51,81,85,99,120,137}
    metadata=load_metadata()
    for task in load_tasks():
        if int(task['task_id'].split('/')[1]) not in selected:
            continue
        builder=CallBuilder.for_source(task['prompt'],task['entry_point'])
        domain=compile_domain(metadata[task['task_id']]['contract'],builder.signature.parameters)
        assert domain['status']=='supported', (task['task_id'],domain['unsupported'])


def test_float_string_admission_distinguishes_comma_and_nonfinite_values():
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    contract='''
    try:
        assert isinstance(value, str)
        value = float(value)
    except:
        raise Exception("invalid inputs")
    import math
    assert not (math.isinf(value) or math.isnan(value)), "invalid inputs"
'''
    domain=compile_domain(contract,['value'])
    assert domain['status']=='supported'
    for value,valid in [('2.5',True),('2,5',False),('nan',False),('inf',False),('abc',False),(2.5,False)]:
        assert evaluate(domain['expression'],{'value':value}) is valid


def test_quantified_type_helpers_preserve_bool_int_and_iterable_semantics():
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    exact=compile_domain('assert all(type(x) == int for x in xs)',['xs'])
    instance=compile_domain('assert all([isinstance(v, (int, float)) for v in xs])',['xs'])
    assert exact['status']==instance['status']=='supported'
    assert not evaluate(exact['expression'],{'xs':[True]})
    assert evaluate(instance['expression'],{'xs':[True,2.5]})
    assert evaluate(exact['expression'],{'xs':[]})
    assert evaluate(exact['expression'],{'xs':''})


def test_quantifier_rewrite_rejects_shadowed_type_name():
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    result=compile_domain('assert all(type(int) == int for int in xs)',['xs'])
    assert result['status']=='unsupported'


def test_finite_numeric_string_idiom_requires_exact_error_and_conversion_structure():
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    valid='''
try:
    assert isinstance(value, str)
    value = float(value)
except:
    raise Exception("invalid inputs")
import math
assert not (math.isinf(value) or math.isnan(value)), "invalid inputs"
'''
    for changed in [valid.replace('float(value)','int(value)'),
                    valid.replace('raise Exception("invalid inputs")','pass'),
                    valid.replace('import math','import os as math')]:
        assert compile_domain(changed,['value'])['status']=='unsupported'


def test_range_list_comprehension_does_not_lose_eager_errors_under_not():
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    result=compile_domain('assert not all([0 <= x <= 1 for x in arr])',['arr'])
    assert result['status']=='unsupported'


def test_finite_string_template_rejects_parameter_shadowed_by_import_math():
    from final.src.modular.tool_sampling.trusted_domain import compile_domain
    contract='''
try:
    assert isinstance(math, str)
    math = float(math)
except:
    raise Exception("invalid inputs")
import math
assert not (math.isinf(math) or math.isnan(math)), "invalid inputs"
'''
    assert compile_domain(contract,['math'])['status']=='unsupported'
