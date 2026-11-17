"""Saved V2 evaluation has no generation path and preserves catalogue settings."""
from pathlib import Path
import json

from final.src.modular.rescore import methods_for_rescore,build_rescore_pipeline
from final.src.modular.generators.frozen import FrozenInputsGenerator
from final.src.modular.tests.test_references import original_run


def test_restore_saved_v2_method_settings_without_generation():
    records=[{'name':'plain','configuration':{}},
        {'name':'ep_bva_v2','configuration':{'catalogue':False}},
        {'name':'decision_table_v2','configuration':{'catalogue':True}}]
    methods=methods_for_rescore(records)
    assert [m.name for m in methods]==['plain','ep_bva_v2','decision_table_v2']
    assert methods[1].configuration()["catalogue"] is False and methods[2].configuration()["catalogue"] is True


def test_prepare_actual_saved_baseline_leaf_uses_frozen_inputs_without_model(tmp_path):
    source=Path('final/out/gemini_catalogue_full164_20261112_193646').resolve()
    r=json.loads((source/'task_receipts/0.json').read_text());leaf=Path(r['generation_directory'])
    pipeline,tasks,metadata=build_rescore_pipeline(leaf,source/'cohort.json',tmp_path/'out',cache_directory=tmp_path/'fresh-cache')
    assert isinstance(pipeline.input_generator,FrozenInputsGenerator) and pipeline.calls is None
    assert [m.name for m in pipeline.input_generator.methods]==['plain','ep_bva_v2','decision_table_v2']
    assert tasks[0]['task_id']=='HumanEval/0' and 'HumanEval/0' in metadata
    assert not (tmp_path/'out').exists()


def test_rescore_cli_evaluation_and_read_only_replay_never_create_model(original_run,tmp_path,monkeypatch):
    from final.src.modular.rescore import main
    import pytest
    cohort,source=original_run
    def forbidden(*args,**kwargs):pytest.fail('Rescore must never create or call a model')
    monkeypatch.setattr('final.src.models.model.QwenModel.__init__',forbidden)
    monkeypatch.setattr('final.src.models.vertex.VertexAIModel.__init__',forbidden)
    output=tmp_path/'rescore';cache=tmp_path/'fresh-cache'
    arguments=['--source-run',str(source.directory),'--cohort',str(cohort),
        '--artifacts',str(output),'--execution-cache',str(cache)]
    assert main(arguments)==0
    metrics=json.loads((output/'rescore_metrics.json').read_text())
    assert metrics['new_model_calls']==0 and metrics['union']['total']==0
    before={str(p):p.read_bytes() for p in output.rglob('*') if p.is_file()}
    monkeypatch.setattr('final.src.modular.stages.reference_oracle.execute',forbidden)
    monkeypatch.setattr('final.src.modular.stages.put_evaluation.execute',forbidden)
    assert main([*arguments,'--replay'])==0
    assert before=={str(p):p.read_bytes() for p in output.rglob('*') if p.is_file()}
