"""One Prefect record for exact saved-pool union evaluation; no model/native rerun."""
import json

from prefect import flow
from prefect.artifacts import create_markdown_artifact,create_table_artifact
from prefect.context import get_run_context
from prefect.client.orchestration import get_client

from .config import ROOT
from .flows import BENCHMARK_PYTHON,command


@flow(name='Evaluate saved input union',retries=0,log_prints=False,persist_result=False)
async def evaluate_saved_union(union_source_directory:str):
    source=(ROOT/union_source_directory).resolve()
    if not source.is_relative_to(ROOT/'final/out'):
        raise ValueError('Union source must be inside final/out')
    run_id=str(get_run_context().flow_run.id)
    directory=ROOT/'final/out'/('union_'+run_id)
    directory.mkdir(parents=True,exist_ok=False)
    async with get_client() as client:
        await client.update_flow_run(get_run_context().flow_run.id,name='Full164 · Union Plain + EP+BVA + DT · saved evaluation replay')
    config={'source_directory':str(source),'output_directory':str(directory/'run'),
            'arms_to_merge':['plain','ep_bva','decision_table'],'new_model_calls':0,'new_native_calls':0,
            'input_budget_unit':'union of source valid inputs; at most60/task','timeout_seconds':8,
            'mode':'exact existing pool/checkpoint replay'}
    (directory/'config_snapshot.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    await create_markdown_artifact(markdown='Gộp input từ cùng full run, kiểm lại reference/native checkpoints. '
        'Chưa có final metrics; source không sửa, không gọi model hoặc chạy lại native pool.\n\n```json\n'+
        json.dumps(config,ensure_ascii=False,indent=2)+'\n```',key='union-config',
        description='Config union evaluation và nguồn/output; metrics trước replay là pending.')
    await command([BENCHMARK_PYTHON,'-m','final.src.audits.evaluate_input_union','--source',source,
        '--artifacts',directory/'run'],log_path=directory/'worker.log')
    output=directory/'run';result=json.loads((output/'result_digest.json').read_text())
    await create_table_artifact(table=[{'arm':name,**metrics} for name,metrics in result['arms'].items()],
        key='union-results',description='Số unique confirmed PUTs/1454 và novel valid inputs; union dùng budget lớn hơn.')
    await create_markdown_artifact(markdown=(output/'REPORT.md').read_text(),key='union-report',
        description='Report cuối tiếng Việt:raw/matched,union input budget,kind,upstreamcost,checkpointreplayverification.')
    return result
