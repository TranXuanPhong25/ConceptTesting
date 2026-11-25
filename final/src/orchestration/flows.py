"""Prefect's built-in parameter forms wrap existing local benchmark subprocesses."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
import time
from typing import Annotated, Literal

from pydantic import Field
from prefect import flow,get_run_logger
from prefect.artifacts import create_markdown_artifact,create_table_artifact
from prefect.context import get_run_context
from prefect.client.orchestration import get_client

from .config import ROOT,normalize,preview
from .names import benchmark_run_name,historical_run_name
from .task_log import task_error_rows
from .routing import endpoint_identity_for_run

BENCHMARK_PYTHON=ROOT/'final/.venv/bin/python'
OUT=ROOT/'final/out'


def active_external_writers(exclude=None, *, selected_endpoint=None):
    found=[]
    if selected_endpoint is None and exclude is not None:
        selected_endpoint = endpoint_identity_for_run(exclude)
    status_paths = set(OUT.glob('*/status.json')) | set(OUT.glob('console_*/run/status.json'))
    for path in sorted(status_paths):
        if exclude and path.parent==exclude:continue
        try:
            state=json.loads(path.read_text());pid=state.get('pid')
            if state.get('state') not in ('running','preflight') or state.get('phase')=='evaluation' or not pid:continue
            command=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
            if str(path.parent).encode() not in command.encode():continue
            writer_endpoint = endpoint_identity_for_run(path.parent)
            # Independent endpoints can generate concurrently; unknown routing stays serialized.
            if selected_endpoint and writer_endpoint and selected_endpoint != writer_endpoint:
                continue
            found.append({'directory':str(path.parent),'pid':pid,'phase':state.get('phase','running')})
        except (OSError,ValueError,TypeError):continue
    return found


async def command(arguments, *, env=None, log_path=None):
    """Cancellation terminates the owned subprocess; saved attempts are preserved."""
    log=None
    if log_path:
        log_path.parent.mkdir(parents=True,exist_ok=True);log=log_path.open('ab')
    process=await asyncio.create_subprocess_exec(*[str(value) for value in arguments],cwd=ROOT,
        env=env,stdout=log or asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
    try:
        output,_=await process.communicate()
        if process.returncode:raise RuntimeError(f'Worker exited{process.returncode}; inspect {log_path or "validation output"}')
        return output.decode() if output else ''
    except BaseException:
        if process.returncode is None:
            try:process.terminate()
            except ProcessLookupError:pass
            try:await asyncio.wait_for(process.wait(),15)
            except asyncio.TimeoutError:process.kill();await process.wait()
        if log_path and log_path.name=='worker.log':
            status_path=log_path.parent/'status.json'
            try:
                status=json.loads(status_path.read_text())
                if status.get('state') not in ('complete','interrupted','cancelled'):
                    status.update(state='interrupted',updated_utc=time.time(),error_type='OrchestratorCancellation',
                                  error='Owned worker exited; saved calls and retry history preserved')
                    temporary=status_path.with_suffix('.tmp');temporary.write_text(json.dumps(status)+'\n');temporary.replace(status_path)
            except (OSError,ValueError):pass
        raise
    finally:
        if log:log.close()


async def watch_worker(arguments,directory,env):
    logger=get_run_logger();task=asyncio.create_task(command(arguments,env=env,log_path=directory/'worker.log'))
    previous=None
    try:
        while not task.done():
            try:
                status=json.loads((directory/'status.json').read_text())
                key=(status.get('state'),status.get('phase'),status.get('task_id'),status.get('task'))
                if key!=previous:logger.info('Run status: %s',key);previous=key
            except (OSError,ValueError):pass
            await asyncio.sleep(3)
        await task
    except BaseException:
        task.cancel()
        try:await task
        except BaseException:pass
        # Keep the per-task error log visible for stopped or failed runs too.
        try:
            await attach_tool_generation_gate(directory)
            error_rows=task_error_rows(directory)
            if error_rows:await create_table_artifact(table=error_rows,key='task-error-log',
                description='Log lỗi theo task của run bị dừng/lỗi, từ record đã lưu')
        except Exception:pass
        raise


async def attach_tool_generation_gate(directory):
    path = directory / 'tool_generation_gate.json'
    if path.is_file():
        gate = json.loads(path.read_text())
        await create_markdown_artifact(key='tool-generation-gate',
            markdown='Tool treatment gate trước freeze/reference. Ready: ' + str(gate['ready']) +
                     '. Detection/coverage khi gate fail: pending, không phải kết quả comparison.\n\n```json\n' +
                     json.dumps(gate, ensure_ascii=False, indent=2) + '\n```',
            description='Evidence tools được exercise; invalid preparation chặn oracle/PUT workload.')


async def attach_outputs(directory):
    await attach_tool_generation_gate(directory)
    snapshot=json.loads((directory/'config_snapshot.json').read_text()) if (directory/'config_snapshot.json').exists() else {}
    await create_markdown_artifact(markdown='### Config snapshot\n\n```json\n'+json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n```\n\nArtifacts: `'+str(directory)+'`',key='config-snapshot')
    error_rows=task_error_rows(directory)
    if error_rows:await create_table_artifact(table=error_rows,key='task-error-log',
        description='Log lỗi theo task từ record đã lưu: generation, reference rejection, PUT failure')
    summary_path=directory/'result_digest.json'
    if summary_path.exists():
        result=json.loads(summary_path.read_text())
        rows=[{'arm':arm,**metrics} for arm,metrics in result.get('arms',{}).items()]
        if rows:await create_table_artifact(table=rows,key='benchmark-results',
            description='tested_base_pass là số PUT vượt base test đã nhận ít nhất một input bổ sung hợp lệ của arm.')
        report=directory/'REPORT.md'
        if report.exists():await create_markdown_artifact(markdown=report.read_text()[:80000],key='benchmark-report')
        return result
    return snapshot



@flow(name='HumanEval inputs',retries=0,log_prints=False,persist_result=False)
async def benchmark(
    cohort:Annotated[Literal['humaneval164','humaneval_plus_mini','humaneval_plus_full'],Field(title='Frozen PUT cohort',description='HumanEval base, EvalPlus Mini base, or EvalPlus Full base; task_numbers selects a subset.')]='humaneval164',
    mode:Annotated[Literal['batch','tools','pynguin'],Field(title='Generation mode',description='Batch, tool sampling or Pynguin.')]='batch',
    arms:Annotated[list[Literal['plain','direct','ep_bva_vf3_hybrid','decision_table_vf3_hybrid','pynguin','control_flow','control_flow_4tool','tool_direct','tool_hypothesis','tool_hypothesis_extra','tool_planner']],Field(title='Arms',description='batch: Plain, Control Flow, Control Flow + 4-tool trace, EP+BVA VF3 Hybrid and DT VF3 Hybrid.')]=['plain','ep_bva_vf3_hybrid','decision_table_vf3_hybrid'],
    task_numbers:Annotated[list[int],Field(title='Task subset (empty means all)',description='HumanEval task numbers, such as 2, 11, 72.')]=[],
    inputs_per_task:Annotated[int,Field(title='Input budget per task per arm',ge=1,le=200)]=20,
    completion_tokens:Annotated[int,Field(title='Maximum completion tokens per call',ge=128,le=32768)]=4096,
    context_tokens:Annotated[int,Field(title='Model context tokens',ge=512,le=131072)]=8192,
    temperature:Annotated[float,Field(title='Generation temperature',ge=0,le=2)]=.7,
    input_seed:Annotated[int,Field(title='Input generation seed',ge=0,le=2147483483)]=314159,
    reference_seed:Annotated[int,Field(title='Reference and PUT seed',ge=0,le=2147483483)]=271828,
    timeout_seconds:Annotated[float,Field(title='Native timeout per input (seconds)',ge=.1,le=60)]=8,
    per_put_base_examples:Annotated[int,Field(title='Legacy base examples field',ge=1,le=300,description='Retained for existing configuration snapshots.')]=12,
    scorer:Annotated[Literal['confirm_first_failures','full_two_repeats'],Field(title='Scorer repeat policy')]='confirm_first_failures',
    model_name:Annotated[str | None,Field(title='Served model name',min_length=1,max_length=120)]=None,
    model_backend:Annotated[Literal['qwen','vertex','openrouter'],Field(title='Model backend')]='qwen',
    tool_sampling:Annotated[dict | None,Field(title='Tool sampling budgets',description='Required for tools mode; explicit draws/query/time/audit/random budgets, including matching arms.')]=None,
    pynguin:Annotated[dict | None,Field(title='Pynguin settings',description='Pinned external Python environment, bounded per-owner upstream search; no credentials.')]=None,
    tool_runs_dir:Annotated[str | None,Field(title='4-tool saved runs directory',description='Optional repo-local directory for control_flow_4tool; defaults to final/out/put_pytest_tools_20261122.')]=None,
    preview_only:Annotated[bool,Field(title='Preview only · no model calls',description='Checked: save config and budget preview without model, tokenizer or native calls.')]=False,
):
    """Choose a preset, edit parameters, Run. Each run freezes its own config/code.

    Args:
        cohort: Frozen HumanEval PUT set: all164 tasks or the known-bug diagnostic10-task subset.
        mode: Choose batch, tools or pynguin.
        arms: Batch supports Plain, Direct, Control Flow, EP+BVA v2, DT v2, EP+BVA VF3 Measured, DT VF3 Measured, EP+BVA VF3 Hybrid and DT VF3 Hybrid.
        task_numbers: HumanEval task IDs as numbers, e.g. 2, 11, 72. An empty list selects all tasks in the cohort.
        inputs_per_task: Total new-input budget per task per arm.
        completion_tokens: Maximum completion tokens in each individual writer call.
        context_tokens: Model context ceiling; both batch arm prompts must fit the same visible-PUT set.
        temperature: Generation temperature for the writer calls.
        input_seed: Seed plus task number for generation requests; it is not offset by PUT ID.
        reference_seed: Seed plus task number for domain/reference/PUT execution.
        timeout_seconds: Native execution timeout per input.
        per_put_base_examples: Legacy configuration field.
        scorer: confirm_first_failures runs a second PUT check only after a first failure. full_two_repeats runs the historical full repeat policy; both arms in a run use the same scorer.
        model_name: Model ID served by the selected backend.
        model_backend: Qwen, Vertex AI hoặc OpenRouter.
        preview_only: Save resolved settings and input/call budget without model, tokenizer, or native calls.
    """
    parameters=locals().copy();parameters.pop('preview_only')
    if parameters['model_name'] is None:parameters.pop('model_name')
    if parameters.get('tool_sampling') is None:parameters.pop('tool_sampling')
    if parameters.get('pynguin') is None:parameters.pop('pynguin')
    if not parameters.get('tool_runs_dir'):
        parameters.pop('tool_runs_dir', None)
    else:
        resolved_tools = (ROOT / parameters['tool_runs_dir']).resolve()
        if not resolved_tools.is_relative_to(ROOT):
            raise ValueError('Choose a repository-local 4-tool runs directory')
        parameters['tool_runs_dir'] = str(resolved_tools.relative_to(ROOT))
    config=normalize(parameters);description=preview(config)
    run_id=str(get_run_context().flow_run.id)
    async with get_client() as client:
        await client.update_flow_run(get_run_context().flow_run.id,name=benchmark_run_name(config,preview_only))
    directory=OUT/('console_'+run_id)
    directory.mkdir(parents=True,exist_ok=False)
    (directory/'submitted_config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    (directory/'config_snapshot.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    (directory/'preview.json').write_text(json.dumps(description,ensure_ascii=False,indent=2)+'\n')
    await create_markdown_artifact(markdown='### Budget preview\n\n```json\n'+json.dumps(description,ensure_ascii=False,indent=2)+'\n```',key='budget-preview')
    logger=get_run_logger();logger.info('Budget: %s calls, %s eligible tasks; %s',description['logical_call_cap'],description['eligible_task_count'],description['input_budget_unit'])
    if preview_only:
        (directory/'status.json').write_text(json.dumps({'state':'preview','new_model_calls':0})+'\n')
        await attach_outputs(directory)
        return {'preview_only':True,'new_model_calls':0,'artifacts':str(directory),**description}
    # The worker creates a new child directory; the submission snapshot stays intact.
    output=directory/'run'
    await command([BENCHMARK_PYTHON,'-m','final.src.orchestration.worker','--config',directory/'submitted_config.json',
                   '--artifacts',output,'--prepare-only'],log_path=directory/'prepare.log')
    await attach_outputs(output)
    while active_external_writers(exclude=output):
        logger.info('Waiting for existing model writer; no duplicate generation started.')
        await asyncio.sleep(15)
    plan=json.loads((output/'launch_plan.json').read_text())
    env={key:value for key,value in os.environ.items() if key in ('HOME','LANG','LC_ALL','TZ','TMPDIR')}
    env.update(PATH=os.defpath,PYTHONPATH=plan['runtime'],PYTHONDONTWRITEBYTECODE='1')
    await watch_worker([BENCHMARK_PYTHON,'-P','-B','-m','final.src.orchestration.worker','--worker','--artifacts',output],output,env)
    return await attach_outputs(output)


@flow(name='Resume saved run',retries=0,log_prints=False,persist_result=False)
async def resume_saved_batch(source_directory:str, timeout_seconds:float | None=None,
                             retry_404_request_id:str | None=None):
    """Resume a stopped matched-batch run, preserving responses and attempt caps.

    source_directory: Path below final/out, relative to repository or absolute.
    timeout_seconds: Optional native timeout amendment; only before any native evaluation.
    retry_404_request_id: Explicitly retry one Qwen completion that returned 404, within its original attempt cap.
    """
    source=(ROOT/source_directory).resolve()
    if not source.is_relative_to(OUT) or not (source/'config_snapshot.json').exists():
        raise ValueError('Select a saved console run directory under final/out')
    async with get_client() as client:
        source_config = json.loads((source/'config_snapshot.json').read_text())
        effective_timeout = timeout_seconds if timeout_seconds is not None else source_config['timeout_seconds']
        title = f'Resume {effective_timeout:g}s · ' + benchmark_run_name(source_config)
        await client.update_flow_run(get_run_context().flow_run.id,name=title)
    directory=OUT/('console_resume_'+str(get_run_context().flow_run.id))
    module='final.src.orchestration.worker'
    arguments=[BENCHMARK_PYTHON,'-m',module,'--resume-from',source,'--artifacts',directory,'--prepare-only']
    if timeout_seconds is not None:
        arguments.extend(['--timeout-seconds',str(timeout_seconds)])
    if retry_404_request_id is not None:
        arguments.extend(['--retry-404-request-id', retry_404_request_id])
    await command(arguments)
    plan=json.loads((directory/'launch_plan.json').read_text())
    await attach_outputs(directory)
    if retry_404_request_id is not None:
        imports = json.loads((directory/'import_receipts.json').read_text())
        grant = imports['retry_grant']
        await create_markdown_artifact(key='resume-retry-grant', markdown=(
            f"Resume từ `{source_directory}`, giữ {imports['original_writer_usage']['received']} response đã lưu. "
            f"Cho phép retry HTTP 404 của đúng call `{grant['call']}` trong giới hạn {grant['max_attempts']} attempts."))
    while active_external_writers(exclude=directory):
        get_run_logger().info('Waiting for model writer on the same endpoint before resuming.')
        await asyncio.sleep(15)
    await create_markdown_artifact(markdown=f"Imported responses: {plan.get('imported_received_calls','see import_receipts.json')}\n\nMaximum logical slots: {plan['logical_call_cap']}\n\nArtifacts: `{directory}`",key='resume-budget')
    env={key:value for key,value in os.environ.items() if key in ('HOME','LANG','LC_ALL','TZ','TMPDIR')}
    env.update(PATH=os.defpath,PYTHONPATH=plan['runtime'],PYTHONDONTWRITEBYTECODE='1')
    await watch_worker([BENCHMARK_PYTHON,'-P','-B','-m',module,'--worker','--artifacts',directory],directory,env)
    return await attach_outputs(directory)
