"""Retired generators cannot be selected; retained research arms stay available."""
import pytest

from final.src.modular.arms import selected_arms
from final.src.orchestration.config import normalize


@pytest.mark.parametrize('name',[
    'ep_bva_vf3_replace','decision_table_vf3_replace','decision_table_vf3_prompt_rollback',
    'ep_bva_vf4','decision_table_vf4','control_flow_obligation_validated','control_flow_obligation',
    'simple_discovery','ep_bva_vf3','decision_table_vf3',
    'ep_bva_reflection','decision_table_reflection',
    'ep_bva_catalogue_then_inputs','decision_table_catalogue_then_inputs',
    'spec_obligation','large_input','data_flow','data_flow_feedback',
    'control_flow_c_use',
    'soft_bva','boundary','equivalence','bva_normal','ep_bva','decision_table',
    'ep_strong','bva_robust','bva_worst_case','ep_dt_bva',
])
def test_retired_arm_is_rejected_by_registry_and_console(name):
    with pytest.raises(ValueError,match='Unknown input-generation method'):
        selected_arms([name])
    with pytest.raises(ValueError,match='Unknown or duplicate'):
        normalize({'arms':[name]})


def test_selected_baselines_and_original_cf_remain_available():
    names=['plain','ep_bva_v2','decision_table_v2','control_flow']
    assert [arm.name for arm in selected_arms(names)]==names


@pytest.mark.parametrize('language', ['cpp', 'java'])
def test_humaneval_x_adapter_is_rejected_before_preparation(tmp_path, language):
    from final.src.benchmarks.datasets import DatasetLoader
    from final.src.benchmarks.PUT_generation import main as generate_puts
    from final.src.benchmarks.pipeline import normalize as adapter_config
    from final.src.benchmarks.language_runtime import execute_program, UnsupportedSignature
    from final.src.benchmarks.run import prepare
    with pytest.raises(ValueError):
        DatasetLoader('he-' + language)
    with pytest.raises(SystemExit) as error:
        generate_puts(['--dataset-type', 'he-' + language])
    assert error.value.code == 2
    with pytest.raises(ValueError):
        adapter_config({'dataset':'humaneval_x_' + language})
    with pytest.raises(ValueError):
        prepare({'dataset':'humaneval_x_' + language}, tmp_path/'retired')
    assert not (tmp_path/'retired').exists()
    with pytest.raises(UnsupportedSignature):
        execute_program({'language':language}, '', [])
