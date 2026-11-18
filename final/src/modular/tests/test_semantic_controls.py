"""Signed target checks are independent of PUT outputs and target naming."""
import pytest
from final.src.modular.call_builder import CallBuilder


def test_signed_controls_reject_overbroad_target_without_task_id_rule():
    from final.src.modular.tool_sampling.semantic_controls import check_controls
    builder=CallBuilder.for_source('def f(text:str):\n pass\n','f')
    model={'domain':'is_str(text) and chars_in(text,"abc")','types':{'text':'str'},
           'targets':[{'id':'arbitrary-id','predicate':'len(text)>1','context':'True'}]}
    controls={'targets':[{'target_id':'arbitrary-id','negative_status':'provided','reason':'contains more than one distinct symbol',
       'examples':[{'arguments':{'text':'ab'},'expected':True,'reason':'two different symbols'},
                   {'arguments':{'text':'aa'},'expected':False,'reason':'one repeated symbol'}]}]}
    report=check_controls(model,builder,controls)
    assert not report['passed']
    assert report['failures'][0]['arguments']=={'text':'aa'}


def test_unknown_or_missing_controls_cannot_be_semantic_pass():
    from final.src.modular.tool_sampling.semantic_controls import check_controls
    builder=CallBuilder.for_source('def f(x:int):\n pass\n','f')
    model={'domain':'is_int(x)','targets':[{'id':'t','predicate':'x>0','context':'True'}]}
    report=check_controls(model,builder,{'targets':[]})
    assert not report['passed'] and report['failures'][0]['code']=='missing_independent_controls'


def test_out_of_domain_negative_does_not_validate_target_semantics():
    from final.src.modular.tool_sampling.semantic_controls import check_controls
    builder=CallBuilder.for_source('def f(x:int):\n pass\n','f')
    model={'domain':'is_int(x) and x>=0','targets':[{'id':'t','predicate':'x>=0','context':'True'}]}
    controls={'targets':[{'target_id':'t','negative_status':'provided','reason':'test target',
       'examples':[{'arguments':{'x':1},'expected':True,'reason':'valid'},
                   {'arguments':{'x':-1},'expected':False,'reason':'invalid'}]}]}
    report=check_controls(model,builder,controls)
    assert not report['passed'] and any(r['code']=='control_outside_trusted_domain' for r in report['failures'])


def test_distinct_count_is_generic_for_strings_and_numeric_lists():
    from final.src.modular.input_buckets.predicates import evaluate
    assert evaluate('distinct_count(x)>1',{'x':'ab'})
    assert not evaluate('distinct_count(x)>1',{'x':'aa'})
    assert evaluate('distinct_count(x)>1',{'x':[7,8]})
    assert not evaluate('distinct_count(x)>1',{'x':[7,7]})


def test_semantic_gate_blocks_before_oracle_with_valid_mechanical_preparation(tmp_path,monkeypatch):
    from final.src.modular.artifacts import ArtifactStore
    from final.src.modular.context import PipelineSettings
    from final.src.modular.generators.tools import ToolInputGenerator
    from final.src.modular.pipeline import BenchmarkPipeline
    from final.src.modular.references import TaskReferencePrograms
    from final.src.modular.tests.test_testing_arms_integration import write_fixture_cohort
    from final.src.modular.tests.test_tool_sampling import budgets,model
    task={'task_id':'HumanEval/7','entry_point':'f','prompt':'def f(a:int,b:int=0):\n pass\n','canonical_solution':'    return a+b\n','test':''}
    cohort=write_fixture_cohort(tmp_path/'cohort.json',[task]);config=budgets();config['arms']=['tool_direct','tool_hypothesis']
    generator=ToolInputGenerator(config,preparations={'HumanEval/7':model()},semantic_controls={'HumanEval/7':{'targets':[]}})
    def forbidden(*args,**kwargs):pytest.fail('Oracle evaluated before independent target checks passed')
    monkeypatch.setattr('final.src.modular.stages.reference_oracle.execute',forbidden)
    out=tmp_path/'run';pipeline=BenchmarkPipeline(cohort,ArtifactStore(out),input_generator=generator,
      settings=PipelineSettings(target_programs=1),reference_programs=TaskReferencePrograms(),execution_cache=False)
    with pytest.raises(ValueError,match='semantic_controls_gate'):pipeline.run([task],{'HumanEval/7':{'contract':'','atol':0}})
    assert (out/'semantic_controls_gate.json').exists() and not(out/'generation_frozen.json').exists()


def test_generic_sequence_queries_cover_type_membership_stride_and_overlap():
    from final.src.modular.input_buckets.predicates import evaluate
    assert evaluate('any_type(xs,"int") and not all_type(xs,"int")',{'xs':[1,'a']})
    assert evaluate('any_in(s,"xyz") and any_not_in(s,"xyz")',{'s':'xa'})
    assert evaluate('all_in(s,"xyz")',{'s':'xy'})
    assert evaluate('any_multiple(slice_values(xs,1,2),2)',{'xs':[1,2,3,4]})
    assert not evaluate('any_multiple(slice_values(xs,1,2),2)',{'xs':[2,1,4,3]})
    assert evaluate('overlapping_occurrences(s,p)',{'s':'aaa','p':'aa'})
    assert not evaluate('overlapping_occurrences(s,p)',{'s':'ababa','p':'ab'})


def test_infeasible_declared_target_checks_negative_controls_without_fake_positive():
    from final.src.modular.tool_sampling.semantic_controls import check_controls
    builder=CallBuilder.for_source('def f(x:int):\n pass\n','f')
    model={'domain':'x>0','targets':[{'id':'outside','predicate':'x==0','context':'True','status':'infeasible'}]}
    controls={'targets':[{'target_id':'outside','negative_status':'provided','reason':'Trusted domain excludes zero',
                         'examples':[{'arguments':{'x':1},'expected':False,'reason':'admitted positive integer'}]}]}
    assert check_controls(model,builder,controls)['passed']


def test_distinct_count_supports_nested_json_values_generically():
    from final.src.modular.input_buckets.predicates import evaluate
    assert evaluate('distinct_count(x)==2',{'x':[[1],[2],[1]]})
    assert evaluate('distinct_count(x)==1',{'x':[{'a':[1]},{'a':[1]}]})


def test_boolean_helper_is_not_a_numeric_count_in_typed_contracts():
    from final.src.modular.tool_sampling.schema import validate_expression
    with pytest.raises(ValueError,match='bool'):
        validate_expression('overlapping_occurrences(s,p)>0',{'s':'str','p':'str'})
    validate_expression('overlapping_occurrences(s,p)',{'s':'str','p':'str'})
