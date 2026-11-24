"""Offline slide fixtures and integration contracts: zero model/network calls."""
from dataclasses import replace
import json
import math
from types import SimpleNamespace

import pytest

from final.src.models.core_model import ModelResponse
from final.src.modular.arms.classical import CatalogueArm
from final.src.modular.arms.fault_oriented import EpBvaV2Arm
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.call_builder import CallBuilder
from final.src.modular.catalogue import (Boundary, Catalogue, boundary_targets, decision_table_check,
    measure_catalogue, measure_task_catalogues, validate_catalogue)
from final.src.modular.context import PipelineSettings, TaskContext
from final.src.modular.input_prompts import structured_input_prompt
from final.src.modular.reference_oracle import run_reference_oracle
from final.src.orchestration import config


def task(source='def f(x): pass'):
    return {'task_id':'HumanEval/0', 'entry_point':'f', 'prompt':source, 'test':''}


def context(tmp_path, source='def f(x): pass'):
    return TaskContext(task(source), {'contract':''}, ArtifactStore(tmp_path), PipelineSettings(input_tokens=4096))


def decode(arm, raw, tmp_path, source='def f(x): pass'):
    return arm.decode_response(ModelResponse(json.dumps(raw),finish_reason='stop'), context(tmp_path,source))


def measure(raw, records, *, name='bva_normal', source='def f(x): pass', budget=20):
    sections = {'bva_normal':('boundaries',),'ep_bva':('classes','boundaries'), 'decision_table':('rules',),
                'equivalence':('classes',), 'ep_strong':('classes',),'bva_worst_case':('boundaries',)}[name]
    catalogue, errors = validate_catalogue(raw, sections)
    assert not errors, errors
    builder = CallBuilder.for_source(source, 'f')
    inputs = [{**builder.build(record['arguments']), 'covers':record.get('covers')} for record in records]
    batch = {'catalogue':catalogue.model_dump(mode='json'), 'catalogue_status':'applicable','inputs':inputs}
    return measure_catalogue(batch,task(source),list(range(len(inputs))),arm_name=name,input_budget=budget)


def boundary_only_arm():
    arm=CatalogueArm()
    arm.name='bva_normal'
    arm.sections=('boundaries',)
    return arm


def bva(identifier='B1', parameter='x', lower=1, upper=12, nominal=None, **extra):
    return {'id':identifier, 'dimension':parameter, 'parameter':parameter,'lower':lower,'upper':upper,
            'values':[lower,lower+1,upper-1,upper], 'nominal':nominal or {parameter:6}, **extra}


def test_month_normal_uses_exact_five_values_and_nominal():
    result=measure({'boundaries':[bva()]},[{'arguments':{'x':x}} for x in [1,2,6,11,12]])
    row=result['boundaries'][0]
    assert row['matched_values']==[1,2,11,12]
    assert row['missing_values']==[] and row['nominal_input_present'] is True
    assert row['single_fault']=='checked'
    assert result['normal_design']['required_inputs']==5


def test_two_dimensions_single_fault_nine_cases_and_joint_changes_excluded():
    nominal={'x':6,'y':6}
    raw={'boundaries':[bva(nominal=nominal),bva('B2','y',nominal=nominal)]}
    calls=[{'arguments':nominal}]
    calls += [{'arguments':{**nominal,parameter:value}} for parameter in ['x','y'] for value in [1,2,11,12]]
    assert len(calls)==9
    result=measure(raw,calls,source='def f(x,y): pass')
    assert all(row['missing_values']==[] for row in result['boundaries'])
    assert result['normal_design']['required_inputs']==9
    assert measure(raw,calls,source='def f(x,y): pass',budget=8)['budget_limited'] is True
    result=measure(raw,[{'arguments':{'x':1,'y':1}}],source='def f(x,y): pass')
    assert all(row['matched_values']==[] and row['non_single_fault_input_indices']==[0] for row in result['boundaries'])


def test_nextday_dependency_context_and_robust_only_outside_neighbors():
    nominal={'day':15,'month':2,'year':2024}
    raw={'boundaries':[bva(parameter='day',upper=29,nominal=nominal,context={'month':2,'year':2024})]}
    calls=[{'arguments':{**nominal,'day':day}} for day in [1,2,15,28,29]]
    calls.append({'arguments':{'day':29,'month':3,'year':2024}})
    result=measure(raw,calls,source='def f(day,month,year): pass')
    assert result['boundaries'][0]['matched_values']==[1,2,28,29]
    boundary=Boundary.model_validate(raw['boundaries'][0])
    assert set(boundary_targets(boundary))=={1,2,28,29}
    assert set(boundary_targets(boundary,robust=True))=={0,1,2,28,29,30}
    # Century divisibility is an EP representative, not a fabricated numeric edge.
    catalogue={'classes':[{'id':'E1900','description':'century not divisible by 400','partition':'leap', 'parameter':'year','members':[1900]},
                           {'id':'E2000','description':'century divisible by 400','partition':'leap','parameter':'year','members':[2000]}]}
    assert not validate_catalogue(catalogue,('classes',))[1]
    unresolved={'boundaries':[], 'status':'unresolved','reason':'31/12/9999: spec omits next year behavior'}
    assert validate_catalogue(unresolved,('boundaries',))[0].status=='unresolved'


def test_float_neighbors_and_admission_relation_with_fixed_context():
    item=Boundary(id='B',dimension='grade',values=[0.0,10.0],lower=0.0,upper=10.0,numeric_kind='float')
    assert boundary_targets(item)==[0.0,math.nextafter(0.0,math.inf),10.0,math.nextafter(10.0,-math.inf)]
    nominal={'t':8.0,'l':9.0,'h':9.0}
    raw={'classes':[{'id':'pass','description':'total >=28','kind':'output'},
                    {'id':'fail','description':'total <28','kind':'output'}],
         'boundaries':[{'id':'sum28','dimension':'t with l=h=9; admission total28', 'parameter':'t',
                        'lower':10.0,'upper':10.0,'numeric_kind':'float','step':0.1,
                        'values':[10.0,10.1,9.9], 'context':{'l':9.0,'h':9.0},'nominal':nominal}]}
    # The checker measures declared values, while the shared domain/reference
    # separately rejects t>10; an interval [10,10] has no inward neighbor.
    result=measure(raw,[{'arguments':{'t':10.0,'l':9.0,'h':9.0},'covers':['pass']},
                        {'arguments':nominal,'covers':['fail']}],name='ep_bva',source='def f(t,l,h): pass')
    assert result['declared']['covered_ids']==['fail','pass']
    assert result['boundaries'][0]['semantic_grounding']=='pending'


def test_grade_overlap_at_four_and_independent_partition_axes():
    raw={'classes':[{'id':'F','description':'F','partition':'grade','parameter':'x','lower':0,'upper':4},
                    {'id':'D','description':'D','partition':'grade','parameter':'x','lower':4,'upper':5}]}
    assert 'overlap:F:D' in validate_catalogue(raw,('classes',))[1]
    raw['classes'][1]['lower_inclusive']=False
    assert not validate_catalogue(raw,('classes',))[1]
    raw['classes'][1]['partition']='other-axis'
    raw['classes'][1]['lower_inclusive']=True
    assert not validate_catalogue(raw,('classes',))[1]


def test_duplicate_empty_and_malformed_catalogues_preserve_valid_inputs(tmp_path):
    examples=[None, {'classes':'wrong'}, {'classes':[]},
              {'classes':[{'id':'E','description':'a'},{'id':'E','description':'b'}]},
              {'classes':[{'id':'E','description':'empty','members':[]}]}]
    for raw in examples:
        result=decode(EpBvaV2Arm(),{'catalogue':raw,'inputs':[{'arguments':{'x':2}}]},tmp_path)
        assert result['catalogue_status']=='catalogue_invalid'
        assert result['inputs'][0]['args']=='(2,)'


def test_decoder_keeps_label_alignment_after_rejection_and_records_no_expected(tmp_path):
    result=decode(boundary_only_arm(),{'catalogue':{'boundaries':[bva()]},'inputs':[
        {'arguments':{'unknown':9},'covers':['Bbad']},{'arguments':{'x':12},'covers':['B1']}]},tmp_path)
    assert len(result['inputs'])==1
    assert result['inputs'][0]['source_index']==1 and result['inputs'][0]['covers']==['B1']
    assert 'expected' not in result['inputs'][0]


def salary_table():
    # Slide p38-48: two roles and five hour ranges. Endpoints h=0,168
    # remain unresolved in the slide predicates; no invented behavior for them.
    actions=[['E5'],['E1','E3'],['E1'],['E1','E4'],['E5'],
             ['E5'],['E2'],['E2'],['E2','E4'],['E5']]
    originals=[]
    for role in range(2):
        for hour in range(5):
            conditions={'C1':'T' if role==0 else 'F','C2':'F' if role==0 else 'T'}
            conditions.update({f'C{i+3}':'T' if i==hour else 'F' for i in range(5)})
            index=role*5+hour
            originals.append({'id':f'O{index+1}','conditions':conditions,'actions':actions[index]})
    rules=[{'id':f'R{i+1}','conditions':{**row['conditions'],'C2':'-'} if i<5 else row['conditions'],
            'actions':row['actions'],'merged_from':[row['id']]} for i,row in enumerate(originals)]
    return {'rules':rules,'original_rules':originals,'mutually_exclusive':[['C1','C2'],['C3','C4','C5','C6','C7']]}


def test_salary_ten_rules_and_slide_infeasible_combination():
    raw=salary_table()
    catalogue,errors=validate_catalogue(raw,('rules',))
    assert not errors and len(catalogue.rules)==10
    bad={'id':'bad','conditions':{f'C{i}':'T' for i in range(1,8)},'actions':['E5']}
    raw['original_rules'].append(bad)
    assert 'infeasible_combination:bad' in validate_catalogue(raw,('rules',))[1]
    bad.update(status='infeasible',reason='C1/C2 and C3-C7 mutually exclusive')
    assert not validate_catalogue(raw,('rules',))[1]


def test_dt_original_denominator_no_coverage_inflation_and_ordered_actions():
    raw={'rules':[{'id':'R','conditions':{'C':'-'},'actions':['A','B'],'merged_from':['O1','O2']}],
         'original_rules':[{'id':'O1','conditions':{'C':'T'},'actions':['A','B']},
                           {'id':'O2','conditions':{'C':'F'},'actions':['A','B']}]}
    result=measure(raw,[{'arguments':{'x':1},'covers':['R','O1']}],name='decision_table')
    assert result['original_rule_coverage']=={'status':'declared','covered':1,'total':2}
    raw['original_rules'][1]['actions']=['B','A']
    assert any('invalid_merge' in error for error in validate_catalogue(raw,('rules',))[1])
    raw.pop('original_rules')
    result=measure(raw,[{'arguments':{'x':1},'covers':['R']}],name='decision_table')
    assert result['original_rule_coverage']['total'] is None


def test_dt_unresolved_is_not_infeasible_and_infeasible_needs_reason():
    raw=salary_table()
    raw['original_rules'].append({'id':'missing','conditions':{'C1':'F','C2':'F'},'status':'unresolved'})
    check=decision_table_check(Catalogue.model_validate(raw))
    assert check['unresolved_rule_ids']==['missing'] and not check['infeasible_rule_ids']
    raw['original_rules'][-1]['status']='infeasible'
    assert 'infeasible_without_reason:missing' in validate_catalogue(raw,('rules',))[1]


def test_cartesian_ep_cap_and_one_input_cannot_cover_two_combinations():
    raw={'classes':[{'id':f'{parameter}{i}','description':str(i),'partition':parameter,'parameter':parameter,'members':[i]}
                    for parameter in ['x','y'] for i in [1,2]]}
    result=measure(raw,[{'arguments':{'x':1,'y':2},'covers':['x1','y2']}],name='ep_strong',source='def f(x,y): pass',budget=2)
    assert result['strong_ep']=={'covered':1,'total_cartesian':4,'feasibility':'pending',
                                 'conflicting_input_indices':[], 'coverage_basis':'self_reported'}
    assert result['budget_limited'] is True


def test_worst_case_cartesian_cap_without_materializing_product():
    raw={'boundaries':[bva(parameter='x',nominal={'x':6,'y':6}),bva('B2','y',nominal={'x':6,'y':6})]}
    result=measure(raw,[{'arguments':{'x':1,'y':12}}],name='bva_worst_case',source='def f(x,y): pass',budget=20)
    assert result['worst_case']=={'covered':1,'total_cartesian':25,'feasibility':'pending'}
    assert result['budget_limited'] is True


def test_reference_survivors_exclude_base_and_rejected_but_keep_global_duplicates(tmp_path,monkeypatch):
    import final.src.modular.reference_oracle as reference
    ctx=context(tmp_path)
    ctx.inputs_frozen=True
    ctx.cohort_task={'base_input_keys':['base']}
    values=[2,99,1,2]
    arm=boundary_only_arm()
    batch=decode(arm,{'catalogue':{'boundaries':[bva()]},'inputs':[
        {'arguments':{'x':value},'covers':['B1']} for value in values]},tmp_path)
    ctx.inputs={'task_id':'HumanEval/0','arms':{'bva_normal':batch}}
    ctx.packet={}
    class Reference:
        record_provenance=False
        def for_task(self,*args):return {'context':'','source':'','entry':'f','contract':''}
    def execute(context,path,job,*args):
        return {'tests':[{'status':'ok','expected':'2','input_key':'two'}, {'status':'error'},
                         {'status':'ok','expected':'1','input_key':'base'}, {'status':'ok','expected':'2','input_key':'two'}]}
    monkeypatch.setattr(reference,'cached_execution',execute)
    run_reference_oracle(ctx, reference_programs=Reference())
    assert ctx.oracle['catalogue_valid_input_indices']['bva_normal']==[0,3]
    assert ctx.oracle['arm_indices']['bva_normal']==[0]
    measure_task_catalogues(ctx, [arm.name])
    measured=ctx.extensions['catalogue_measurements']['bva_normal']
    assert measured['valid_input_records']==2
    assert measured['boundaries'][0]['matched_values']==[2]


def test_console_comparison_preset_has_v2_arms_and_shared_budget():
    from pathlib import Path
    presets = json.loads(Path('final/presets/run_console.json').read_text())
    preset = next(preset for preset in presets if preset['name'] == 'Full164 · Plain vs EP+BVA v2 vs DT v2 · batch')
    preview=config.preview(preset['parameters'])
    assert preview['config']['arms']==['plain','ep_bva_v2','decision_table_v2']
    assert preview['completion_token_cap_per_call']==4096
    assert preview['logical_call_cap']==471
    assert preview['max_input_slots_per_arm']==3140


def test_malformed_tagged_context_or_nominal_cannot_abort_generation_or_evaluation(tmp_path):
    for field in ['context','nominal']:
        boundary=bva()
        boundary[field]={'x':{'__python_type__':'tuple','items':'bad'}}
        result=decode(boundary_only_arm(),{'catalogue':{'boundaries':[boundary]},'inputs':[{'arguments':{'x':2}}]},tmp_path)
        assert result['catalogue_status']=='catalogue_invalid'
        assert result['inputs'][0]['args']=='(2,)'
        ctx=context(tmp_path/field)
        ctx.inputs_frozen=True
        ctx.inputs={'arms':{'bva_normal':result}}
        ctx.oracle={'catalogue_valid_input_indices':{'bva_normal':[0]}}
        measure_task_catalogues(ctx, [boundary_only_arm().name])
        assert ctx.extensions['catalogue_measurements']['bva_normal']['status']=='catalogue_invalid'


def test_strong_ep_contradictory_classes_never_expand_a_single_input():
    raw={'classes':[{'id':f'{parameter}{i}','description':str(i),'partition':parameter,'parameter':parameter,'members':[i]}
                    for parameter in ['x','y'] for i in [1,2]]}
    for covers in [['x1','x2','y1','y2'], ['x2','y2']]:
        result=measure(raw,[{'arguments':{'x':1,'y':1},'covers':covers}],name='ep_strong',source='def f(x,y): pass')
        assert result['strong_ep']['covered']==0
        assert result['strong_ep']['conflicting_input_indices']==[0]


def test_single_fault_checks_other_dimensions_sharing_the_parameter():
    nominal={'x':[0,1,1]}
    raw={'boundaries':[{'id':'length','dimension':'length(x)','parameter':'x','transform':'length',
                        'lower':0,'upper':5,'values':[0,1,4,5],'nominal':nominal},
                       {'id':'zeros','dimension':'count zero','parameter':'x','transform':'count','count_value':0,
                        'lower':0,'upper':2,'values':[0,1,2],'nominal':nominal}]}
    result=measure(raw,[{'arguments':{'x':[]}}])
    assert all(row['matched_values']==[] for row in result['boundaries'])
    assert all(row['non_single_fault_input_indices']==[0] for row in result['boundaries'])


def test_merged_original_id_collision_is_invalid_and_prose_only_coverage_pending():
    raw={'rules':[{'id':'R1','conditions':{'C':'-'},'actions':['A'],'merged_from':['R1','R2']}],
         'original_rules':[{'id':'R1','conditions':{'C':'T'},'actions':['A']},
                           {'id':'R2','conditions':{'C':'F'},'actions':['A']}]}
    assert 'ambiguous_merged_original_id:R1' in validate_catalogue(raw,('rules',))[1]
    result=measure({'boundaries':[{'id':'B','dimension':'length unknown','values':[0,1]}]},[{'arguments':{'x':1}}])
    assert result['boundaries'][0]['single_fault']=='pending'
    assert result['normal_design']['required_inputs'] is None
    assert result['base_call_coverage']=='pending'


def test_narrow_numeric_interval_has_no_out_of_domain_normal_neighbors():
    for kind,lower,upper in [('integer',1,1),('float',0.0,math.nextafter(0.0,math.inf))]:
        boundary=Boundary(id='B',dimension='x',numeric_kind=kind,lower=lower,upper=upper,values=[lower,upper])
        assert all(lower<=value<=upper for value in boundary_targets(boundary))
        assert any(value<lower or value>upper for value in boundary_targets(boundary,robust=True))


def test_per_arm_usage_includes_unknown_attempts_without_blending_arms(tmp_path):
    from final.src.runtime.artifacts import save
    from final.src.modular.catalogue_reporting import usage_by_arm
    for name in ['ep_bva','ep_bva_unknown_attempt_0000','plain']:
        save(tmp_path/f'tasks/0/calls/{name}/attempt.json',{'state':'unknown'})
    save(tmp_path/'tasks/0/calls/ep_bva/response.json',{'usage':{'prompt_tokens':10,'completion_tokens':40,'total_tokens':50}})
    save(tmp_path/'tasks/0/calls/plain/response.json',{'usage':{'prompt_tokens':8,'completion_tokens':2,'total_tokens':10}})
    usage=usage_by_arm(tmp_path,['ep_bva','plain'])
    assert usage['ep_bva']['known_usage']['total_tokens']==50
    assert usage['ep_bva']['unknown']==1 and usage['plain']['unknown']==0


def test_dt_syntactic_overlap_on_explicit_infeasible_combination_is_not_invalid():
    raw={'conditions':{'C1':['T','F'],'C2':['T','F']},
         'rules':[{'id':'A','conditions':{'C1':'T','C2':'-'},'actions':['a'],'merged_from':['TT']},
                  {'id':'B','conditions':{'C1':'-','C2':'F'},'actions':['b'],'merged_from':['FF']}],
         'original_rules':[{'id':'TT','conditions':{'C1':'T','C2':'T'},'actions':['a']},
                           {'id':'FF','conditions':{'C1':'F','C2':'F'},'actions':['b']},
                           {'id':'TF','conditions':{'C1':'T','C2':'F'},'status':'infeasible','reason':'C1 implies C2'},
                           {'id':'FT','conditions':{'C1':'F','C2':'T'},'status':'infeasible','reason':'C2 implies C1'}]}
    catalogue,errors=validate_catalogue(raw,('rules',))
    assert not errors
    assert 'potential_overlap:A:B' not in decision_table_check(catalogue)['pending']


def test_console_config_is_independent_of_benchmark_transport_packages():
    import subprocess
    import sys
    script='''
import importlib.abc
import sys
class BlockBenchmark(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('final.src.modular.arms', 'final.src.runtime', 'openai', 'langchain')):
            raise AssertionError('Benchmark dependency imported by Prefect config: '+fullname)
sys.meta_path.insert(0, BlockBenchmark())
from final.src.orchestration.config import normalize
assert normalize({'arms':['plain','ep_bva_v2']})['completion_tokens']==4096
'''
    result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    from final.src.modular.arm_names import CATALOGUE_ARM_NAMES
    from final.src.modular.arms.fault_oriented import V2_ARMS
    assert set(CATALOGUE_ARM_NAMES)=={arm.name for arm in V2_ARMS}


def test_float_and_finite_enum_domains_infer_kind_when_optional_field_is_omitted():
    boundary=Boundary(id='float',dimension='x',values=[0.0,1.0],lower=0.0,upper=1.0)
    assert boundary_targets(boundary)==[0.0,math.nextafter(0.0,math.inf),1.0,math.nextafter(1.0,-math.inf)]
    assert boundary_targets(Boundary(id='bool',dimension='flag',values=[True,False]))==[True,False]
    assert boundary_targets(Boundary(id='enum',dimension='mode',values=['a','b']))==['a','b']


def test_unknown_boundary_coverage_is_pending_instead_of_a_zero_count():
    from final.src.modular.catalogue import count_uncovered_boundary_values
    assert count_uncovered_boundary_values([]) is None
    assert count_uncovered_boundary_values([{'missing_values':None}]) is None
    assert count_uncovered_boundary_values([{'missing_values':[1]}, {'missing_values':None}]) is None
    assert count_uncovered_boundary_values([{'missing_values':[]}])==0
    assert count_uncovered_boundary_values([{'missing_values':[1,2]}, {'missing_values':[3]}])==3
