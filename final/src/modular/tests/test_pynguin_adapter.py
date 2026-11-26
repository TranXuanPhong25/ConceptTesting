from dataclasses import replace
from pathlib import Path
import pytest
from final.src.modular.pynguin.config import PynguinSettings
from final.src.modular.pynguin.adapter import PynguinInputGenerator
from final.src.modular.context import TaskContext, PipelineSettings
from final.src.modular.artifacts import ArtifactStore

PYTHON = str(Path('final/.venv_pynguin/bin/python').absolute())

def context(tmp_path, source='def f(x: int):\n    return x + 1\n'):
    return TaskContext(task={'task_id':'Toy/1','prompt':'def f(x: int):\n    pass\n','entry_point':'f'},
        metadata={'contract':'assert isinstance(x, int)'}, artifacts=ArtifactStore(tmp_path), settings=PipelineSettings(),
        cohort_task={'programs':[{'id':'p1','code':source,'base':{'status':'pass'}}]},
        packet={'visible_put_ids':['p1']})

@pytest.mark.parametrize('values', [{'search_seconds':0},{'wall_seconds':1},{'seed':True},{'owner_limit':1000},{'max_extract_calls':0}])
def test_invalid_settings(values):
    with pytest.raises(ValueError): PynguinSettings(python=PYTHON, **values)

def test_missing_runtime_is_explicit_and_replay_without_child(tmp_path):
    generator=PynguinInputGenerator(PynguinSettings(python='/missing/python'))
    ctx=context(tmp_path)
    batch=generator.run_task(ctx)
    assert batch['status']=='unsupported_environment'
    assert generator.generate(ctx)['arms']['pynguin']==batch
    ctx.cohort_task['programs'][0]['code']+='\n# changed\n'
    with pytest.raises(ValueError, match='source_info'): generator.run_task(ctx)

def test_interrupted_intent_never_dispatches(tmp_path):
    generator=PynguinInputGenerator(PynguinSettings(python=PYTHON))
    ctx=context(tmp_path)
    source_info=generator.source_info(ctx)
    ctx.artifacts.write('tasks/1/pynguin/intent.json',source_info)
    result=generator.run_task(ctx)
    assert result['status']=='failed' and result['reason']=='interrupted_unknown'

def test_skip_stays_pipeline_skip(tmp_path):
    generator=PynguinInputGenerator(PynguinSettings(python=PYTHON))
    ctx=context(tmp_path);ctx.packet={'skip':'no_base_pass'}
    assert generator.generate(ctx)=={'task_id':'Toy/1','skip':'no_base_pass'}

def test_unavailable_batch_blocks_reference(tmp_path):
    ctx=context(tmp_path)
    generator=PynguinInputGenerator(PynguinSettings(python='/missing/python'))
    ctx.inputs=generator.generate(ctx)
    with pytest.raises(ValueError, match='unsupported_environment'):
        generator.validate_generation([ctx])

def test_summary_reports_pending_executions(tmp_path):
    ctx=context(tmp_path)
    generator=PynguinInputGenerator(PynguinSettings(python='/missing/python'))
    ctx.inputs=generator.generate(ctx)
    summary={};generator.extend_summary([ctx],summary,None)
    assert summary['pynguin']['actual_test_executions']=='pending'
    assert summary['pynguin']['model_calls']==0
    assert summary['pynguin']['tasks'][0]['status']=='unsupported_environment'

def test_pipeline_manifest_hashes_assets_without_tool(tmp_path):
    from final.src.modular.pipeline import BenchmarkPipeline
    from final.src.modular.references import HumanEvalPlusReferencePrograms
    ctx = context(tmp_path)
    pipeline = object.__new__(BenchmarkPipeline)
    pipeline.input_generator = PynguinInputGenerator(PynguinSettings(python='/missing/python'))
    pipeline.calls = None
    pipeline.arms = pipeline.input_generator.methods
    pipeline.reference_programs = HumanEvalPlusReferencePrograms()
    assert pipeline.input_generator.configuration() == pipeline.generator_configuration()['configuration']
    assert pipeline.input_generator.source_info(ctx)['owners'][0]['id'] == 'p1'


def test_export_collection_has_aggregate_byte_budget(tmp_path):
    from final.src.modular.pynguin.adapter import read_export_sources
    export=tmp_path/'export';export.mkdir()
    for i in range(3):
        with (export/f'test_{i}.py').open('wb') as output:
            output.truncate(4*1024*1024)
    with pytest.raises(ValueError):
        read_export_sources(tmp_path)


def test_child_directory_enumeration_is_bounded(tmp_path):
    from final.src.modular.pynguin.adapter import child_directory_names
    for i in range(65):(tmp_path/str(i)).touch()
    with pytest.raises(ValueError):
        child_directory_names(tmp_path)


def test_valid_inputs_survive_failed_owner_with_partial_metadata(tmp_path,monkeypatch):
    ctx=context(tmp_path)
    ctx.cohort_task['programs'].append({'id':'p2','code':ctx.cohort_task['programs'][0]['code'],'base':{'status':'pass'}})
    ctx.packet['visible_put_ids'].append('p2')
    generator=PynguinInputGenerator(PynguinSettings(python=PYTHON))
    def search(context,prefix,index,owner):
        if index: return {'owner':owner['id'],'status':'failed','reason':'child_exit','calls':[]}
        return {'owner':owner['id'],'status':'complete','calls':[{'args':'(1,)','kwargs':'{}','test':'test_target.py::test_0'}]}
    monkeypatch.setattr(generator,'search_owner',search)
    batch=generator.construct(ctx,'tasks/1/pynguin/',generator.source_info(ctx))
    assert batch['status']=='partial' and len(batch['inputs'])==1
    assert batch['pynguin']['partial'] is True
    assert batch['pynguin']['owner_failures']==[{'owner':'p2','status':'failed','reason':'child_exit'}]
    ctx.inputs={'arms':{'pynguin':batch}}
    generator.validate_generation([ctx])
