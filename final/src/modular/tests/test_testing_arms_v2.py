"""V2 composition, hypotheses, shared context and immutable example dependencies."""
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from final.src.modular.arms.classical import EpBvaArm, DecisionTableArm, CatalogueSettings
from final.src.modular.arms.fault_oriented import EpBvaV2Arm,DecisionTableV2Arm,V2_ARMS
from final.src.modular.catalogue import validate_catalogue
from final.src.modular.tests.test_testing_arms import context,decode,task
from final.src.modular.input_prompts import structured_input_prompt
from final.src.modular.tests.test_testing_arms_integration import make_pipeline,TASK,META
from final.src.modular.pipeline import BenchmarkPipeline
from final.src.modular.artifacts import ArtifactStore
from final.src.modular.references import TaskReferencePrograms
from final.src.orchestration import config,worker


def test_v2_combines_three_refinements_with_one_soft_example_per_technique(tmp_path):
    common=structured_input_prompt(task(),[], '',20)
    for factory in V2_ARMS:
        arm=factory();prompt=arm.build_messages({'common':common})[1]['content']
        assert len(arm.guidance.splitlines())<=8
        assert 'fault hypotheses' in ' '.join(arm.guidance.split())
        assert 'membership' in arm.guidance
        assert prompt.count('SOFT EXAMPLE')==1 and 'fault_hypothesis' in prompt
        assert len(arm.configuration()['soft_example'].split())<=140
        off=factory(CatalogueSettings(catalogue=False)).build_messages({'common':common})[1]['content']
        assert 'catalogue' not in off
    assert 'input dependencies' in EpBvaV2Arm.guidance
    assert 'one parameter' in DecisionTableV2Arm.guidance
    for arm in [EpBvaArm(),DecisionTableArm()]:
        prompt=arm.build_messages({'common':common})[1]['content']
        assert 'SOFT EXAMPLE' not in prompt and 'fault_hypothesis' not in prompt


def test_optional_hypotheses_survive_decoder_without_certifying_faults(tmp_path):
    raw={'classes':[{'id':'E','description':'joint behavior','fault_hypothesis':'missing joint check'}],
         'boundaries':[{'id':'B','dimension':'x','values':[1,2]}]}
    result=decode(EpBvaV2Arm(),{'catalogue':raw,'inputs':[{'arguments':{'x':2},'covers':['E','B']}]},tmp_path)
    assert result['catalogue_status']=='applicable'
    assert result['catalogue']['classes'][0]['fault_hypothesis']=='missing joint check'
    assert len(result['inputs'])==1
    plain,_=validate_catalogue({'classes':[{'id':'E','description':'ordinary'}]},('classes',))
    assert 'fault_hypothesis' not in plain.model_dump(mode='json')['classes'][0]


def test_four_arm_smoke_budget_and_json_asset_freeze(tmp_path,monkeypatch):
    values={'cohort':'humaneval164','task_numbers':[0,5,18,81,99,120],'arms':['ep_bva','ep_bva_v2','decision_table','decision_table_v2'],
            'completion_tokens':4096,'timeout_seconds':8}
    preview=config.preview(values)
    assert preview['logical_call_cap']==24 and preview['target_program_count']==10
    assert preview['max_input_slots_per_arm']==120
    monkeypatch.setattr(worker,'private_endpoint',lambda *args:tmp_path/'private.env')
    prepared=tmp_path/'prepared';worker.prepare(values,prepared)
    asset=Path('final/src/modular/fault_oriented_testing/soft_examples.json')
    assert (prepared/'runtime'/asset).read_bytes()==asset.read_bytes()
    source=json.loads((prepared/'source_snapshot.json').read_text())['sources']
    assert str(prepared/'runtime'/asset) in source
    import os,subprocess,sys
    script='''
from pathlib import Path
from final.src.modular.arms.fault_oriented import EpBvaV2Arm
import final.src.modular.fault_oriented_testing.prompts as prompts
assert Path(prompts.__file__).resolve().is_relative_to(Path.cwd()/'prepared/runtime')
assert 'package-version filtering' in EpBvaV2Arm().configuration()['soft_example']
'''
    environment={**os.environ,'PYTHONPATH':str(prepared/'runtime')}
    checked=subprocess.run([sys.executable,'-P','-c',script],cwd=tmp_path,env=environment,capture_output=True,text=True)
    assert checked.returncode==0,checked.stderr


def test_v1_v2_four_arm_input_freeze_and_replay(tmp_path,monkeypatch):
    original,model,events,tasks=make_pipeline(tmp_path,monkeypatch)
    methods=(EpBvaArm(),EpBvaV2Arm(),DecisionTableArm(),DecisionTableV2Arm())
    pipeline=BenchmarkPipeline(original.cohort_stage.cohort_path,original.artifacts,arms=methods,
        settings=original.settings,calls=original.calls,execution_cache=False,reference_programs=TaskReferencePrograms())
    result=pipeline.run(tasks,{TASK['task_id']:META})
    assert len(model.messages)==4 and len(result['comparisons'])==6
    packet=original.artifacts.read('tasks/7/packet.json')
    assert set(packet['prompt_tokens'])=={method.name for method in methods}
    manifest=original.artifacts.read('modular_manifest.json')
    assert any(path.endswith('soft_examples.json') for path in manifest['sources'])
    replay=BenchmarkPipeline(original.cohort_stage.cohort_path,ArtifactStore(original.artifacts.directory,read_only=True),
        arms=methods,settings=original.settings,execution_cache=False,reference_programs=TaskReferencePrograms())
    assert replay.run(tasks,{TASK['task_id']:META})==result
