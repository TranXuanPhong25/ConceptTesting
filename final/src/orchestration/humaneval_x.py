"""Explicitly requested Java experiment, including PUT generation, on Prefect local."""
import argparse
import asyncio
import json
import os
from pathlib import Path

from prefect import flow
from prefect.artifacts import create_markdown_artifact
from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import ArtifactUpdate
from prefect.context import get_run_context

from .flows import ROOT, BENCHMARK_PYTHON, command
from final.src.runtime.artifacts import save


@flow(name='HumanEval-X Java · Gemini · Plain + DT V2', retries=0, persist_result=False)
async def experiment(output):
    directory = Path(output).resolve()
    run_id = get_run_context().flow_run.id
    async with get_client() as client:
        await client.update_flow_run(run_id, name='HumanEval-X Java164 · Gemini · PUTs + Plain + DT V2')
    submission = directory.with_name(directory.name + '_submission')
    submission.mkdir(parents=True, exist_ok=False)
    prepare_code = ('from pathlib import Path; from final.src.benchmarks.java_run import prepare; '
        'prepare(Path(' + repr(str(directory)) + '))')
    await command([BENCHMARK_PYTHON, '-P', '-B', '-c', prepare_code],
        env={**os.environ, 'PYTHONPATH': str(ROOT)}, log_path=submission / 'prepare.log')
    config = json.loads((directory / 'experiment_config.json').read_text())
    config_id = await create_markdown_artifact(key='java-config', description='Config, budgets và source/output thực tế.',
        markdown='```json\n' + json.dumps(config, ensure_ascii=False, indent=2) + '\n```')
    progress_id = await create_markdown_artifact(key='java-progress', markdown='Chưa workload;metrics pending.')
    report_id = await create_markdown_artifact(key='java-report', markdown='PUT generation/evaluation chưa hoàn tất;metrics pending.')
    save(directory / 'prefect_record.json', {'flow_run_id': str(run_id),
        'url': 'http://127.0.0.1:4200/runs/flow-run/' + str(run_id),
        'artifact_ids': [str(i) for i in (config_id, progress_id, report_id)]})
    plan = json.loads((directory / 'launch_plan.json').read_text())
    environment = {key: value for key, value in os.environ.items() if key in (
        'HOME', 'PATH', 'LANG', 'LC_ALL', 'TZ', 'GOOGLE_APPLICATION_CREDENTIALS',
        'VERTEX_PROJECT', 'GOOGLE_CLOUD_PROJECT', 'VERTEX_LOCATION', 'LLM_THINKING_BUDGET')}
    environment.update(PYTHONPATH=plan['runtime'], PYTHONDONTWRITEBYTECODE='1', LANGCHAIN_TRACING_V2='false')
    worker = asyncio.create_task(command([BENCHMARK_PYTHON, '-P', '-B', '-m', 'final.src.benchmarks.java_run',
        '--artifacts', directory], env=environment, log_path=directory / 'worker.log'))
    previous = None
    try:
        while not worker.done():
            path = directory / 'progress.json'
            if path.exists():
                data = path.read_text()
                if data != previous:
                    async with get_client() as client:
                        await client.update_artifact(progress_id, ArtifactUpdate(data='Tiến độ đã lưu;đơn vị task/PUT/input theo field.\n```json\n' + data + '\n```'))
                    previous = data
            await asyncio.sleep(3)
        await worker
    finally:
        if not worker.done():
            worker.cancel()
            try:
                await worker
            except BaseException:
                pass
        report = directory / 'REPORT.md'
        if report.exists():
            async with get_client() as client:
                await client.update_artifact(report_id, ArtifactUpdate(data=report.read_text()[:80000]))
    result = json.loads((directory / 'result_digest.json').read_text())
    if json.loads((directory / 'status.json').read_text())['state'] != 'complete':
        raise RuntimeError('Java workload has not completed')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.environ['PREFECT_API_URL'] = 'http://127.0.0.1:4200/api'
    os.environ.pop('PREFECT_API_KEY', None)
    asyncio.run(experiment(str(args.output)))
