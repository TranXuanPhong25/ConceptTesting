"""Prefect form for MBPP; no automatic PUT generation."""
from __future__ import annotations

import asyncio
import json
import os
from typing import Literal

from prefect import flow
from prefect.artifacts import create_markdown_artifact, create_table_artifact
from prefect.context import get_run_context
from prefect.client.orchestration import get_client
from final.src.models import OPENROUTER_DEFAULT_MODEL
from final.src.modular.context import DEFAULT_CONTEXT_TOKENS, DEFAULT_INPUT_TOKENS
from .flows import ROOT, OUT, BENCHMARK_PYTHON, command, watch_worker, active_external_writers
from .routing import endpoint_identity_for_profile


async def attach_adapter_outputs(directory):
    config = json.loads((directory/'config_snapshot.json').read_text())
    await create_markdown_artifact(key='adapter-config', markdown='```json\n'
        +json.dumps(config, ensure_ascii=False, indent=2)+'\n```')
    if (directory/'REPORT.md').exists():
        await create_markdown_artifact(key='adapter-report', markdown=(directory/'REPORT.md').read_text()[:80000],
            description='Kết quả/giới hạn hoặc lý do run dở dang, từ artifacts đã lưu.')
    if (directory/'result_digest.json').exists():
        result = json.loads((directory/'result_digest.json').read_text())
        await create_table_artifact(key='adapter-results', table=[{'arm':arm, **metrics} for arm, metrics in result['arms'].items()],
            description='Đơn vị detected là PUT có reference disagreement, chưa xác minh bug theo spec.')
        return result
    return config


@flow(name='MBPP inputs', retries=0, log_prints=False, persist_result=False)
async def adapter_benchmark(
    dataset: Literal['mbpp']='mbpp',
    candidate_path: str='',
    task_numbers: list[int]=[],
    arms: list[Literal['plain','ep_bva_single','decision_table_single','control_flow','control_flow_4tool']]=['plain','ep_bva_single','decision_table_single'],
    backend: Literal['qwen','vertex','openrouter']='qwen',
    model_name: str | None=None,
    inputs_per_task: int=20,
    completion_tokens: int=DEFAULT_INPUT_TOKENS,
    context_tokens: int=DEFAULT_CONTEXT_TOKENS,
    temperature: float=.7,
    seed: int=314159,
    timeout_seconds: float=8,
    tool_runs_dir: str='',
    preview_only: bool=True,
):
    """Import saved complete PUTs, then compare shared input-generation arms.

    candidate_path: JSONL under the workspace: task_id, id, code (complete source).
    tool_runs_dir: Optional repo-local 4-tool runs directory for control_flow_4tool.
    preview_only: Validate/pin config/data/budget without a model, tokenizer or native call.
    Execution coverage and verified specification bugs are pending; detected means
    a confirmed disagreement with the dataset's canonical reference.
    """
    if model_name is None:
        model_name = OPENROUTER_DEFAULT_MODEL if backend == 'openrouter' else 'qwen3.5-27b-awq'
    parameters = locals().copy(); parameters.pop('preview_only')
    if candidate_path:
        source = (ROOT / candidate_path).resolve()
        if not source.is_relative_to(ROOT):
            raise ValueError('Choose a repository-local saved PUT JSONL')
        parameters['candidate_path'] = str(source)
    if tool_runs_dir:
        tools_source = (ROOT / tool_runs_dir).resolve()
        if not tools_source.is_relative_to(ROOT):
            raise ValueError('Choose a repository-local 4-tool runs directory')
        parameters['tool_runs_dir'] = str(tools_source)
    run_id = str(get_run_context().flow_run.id)
    directory = OUT / ('adapters_'+run_id)
    submission = OUT / ('adapters_submission_'+run_id)
    submission.mkdir(parents=True, exist_ok=False)
    config_file = submission/'config.json'
    config_file.write_text(json.dumps(parameters, ensure_ascii=False, indent=2)+'\n')
    async with get_client() as client:
        await client.update_flow_run(get_run_context().flow_run.id,
            name=('Preview · ' if preview_only else '') + f'{dataset} · {model_name}')
    await command([BENCHMARK_PYTHON,'-m','final.src.benchmarks.run','--action','prepare',
        '--config',config_file,'--artifacts',directory], log_path=submission/'prepare.log')
    description = json.loads((directory/'preview.json').read_text())
    await create_markdown_artifact(key='adapter-budget', markdown='Config/budget đã pin; metric chưa đo là pending.\n\n```json\n'
        + json.dumps(description, ensure_ascii=False, indent=2)+'\n```')
    await attach_adapter_outputs(directory)
    if preview_only:
        return {'preview_only':True, 'artifacts':str(directory), **description}
    if description['cohort_status']=='pending':
        raise ValueError('Chưa có PUT cohort. Nhập candidate_path trước khi Run; không tự gọi writer LLM.')
    endpoint = endpoint_identity_for_profile(os.environ.get(
        'FINAL_ENDPOINT_ENV_FILE', '~/.config/concepttester/final-qwen.env')) if backend == 'qwen' else None
    while active_external_writers(exclude=directory, selected_endpoint=endpoint):
        await asyncio.sleep(15)
    plan = json.loads((directory/'launch_plan.json').read_text())
    env = {key:value for key,value in os.environ.items() if key in (
        'HOME','LANG','LC_ALL','TZ','TMPDIR','GOOGLE_APPLICATION_CREDENTIALS','VERTEX_PROJECT','GOOGLE_CLOUD_PROJECT','VERTEX_LOCATION','FINAL_ENDPOINT_ENV_FILE')}
    env.update(PATH=os.defpath, PYTHONPATH=plan['runtime'], PYTHONDONTWRITEBYTECODE='1', LANGCHAIN_TRACING_V2='false')
    try:
        await watch_worker([BENCHMARK_PYTHON,'-P','-B','-m','final.src.benchmarks.run',
            '--action','run','--artifacts',directory], directory, env)
    finally:
        # Also expose progress and partial receipts for a failed/interrupted source run.
        progress = directory/'progress.json'
        if progress.exists():
            await create_table_artifact(key='adapter-progress', table=[json.loads(progress.read_text())],
                description='Tiến độ đã lưu; execution chưa xong không được coi là 0 detection.')
        await attach_adapter_outputs(directory)
    return json.loads((directory/'result_digest.json').read_text())
