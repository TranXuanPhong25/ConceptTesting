"""Fixed random28dev, two actual arms K1, bounded generation then CPU scoring."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,fcntl,json,os
from decimal import Decimal
from .paths import HERE,CONFIG,select_model
from . import provenance,v4_runtime,combined_generation,scoring
from .llm_client import atomic_json

ROOT=HERE/'out/deepinfra_quarter'


def prepare(root=ROOT):
    from .prepare_cpu import load
    from .context_preflight import preflight
    from .cost import estimate
    endpoints=json.loads((HERE/'assets/deepinfra_endpoints_20261026.json').read_text())['data']
    if endpoints['id']!=CONFIG['openrouter']['model']:raise ValueError('endpoint_model_mismatch')
    endpoint=next(e for e in endpoints['endpoints'] if e.get('tag')=='deepinfra/fp8')
    required={'reasoning','max_tokens','temperature','top_p','response_format'}
    if endpoint.get('status')!=0 or not required<=set(endpoint.get('supported_parameters') or []):
        raise ValueError('provider_not_ready')
    if endpoint['context_length']!=CONFIG['openrouter']['context_length'] or endpoint['max_completion_tokens']<131072:
        raise ValueError('provider_context_drift')
    for key in ('prompt','completion'):
        if Decimal(endpoint['pricing'][key])*1000000>Decimal(str(CONFIG['openrouter']['reservation_price_per_million'][key])):
            raise ValueError('provider_price_above_cap')
    rows=load('humaneval')
    if rows is None or len(rows)!=28:raise ValueError('all28_cpu_bundles_required')
    ids=json.loads((HERE/'COHORT.json').read_text())['task_ids']
    if [r['baseline']['task'] for r in rows]!=ids:raise ValueError('cohort_order_drift')
    v4_runtime.immutable(root/'humaneval/prepared.json',rows)
    atomic_json(root/'context_preflight.json',preflight({'humaneval':rows}))
    atomic_json(root/'estimate.json',estimate())
    return rows


def freeze(root):
    files={str(p.relative_to(root)):provenance.sha(p)
           for part in ('humaneval/generation','humaneval/paired_subset') for p in (root/part).rglob('*')
           if p.is_file() and p.suffix in ('.json','.jsonl','.py')}
    v4_runtime.immutable(root/'generation_frozen.json',files)


def paired_prefix(root):
    run=root/'humaneval/generation'
    bundles=json.loads((run/'tasks.json').read_text())
    selected=[];rows=[]
    for task in bundles['tasks']:
        paths=[run/'artifacts'/str(task['task'])/'0'/arm/'result.json' for arm in CONFIG['combined']['arms']]
        if not all(p.exists() for p in paths):break
        selected.append(task);rows.extend(json.loads(p.read_text()) for p in paths)
    out=root/'humaneval/paired_subset'
    v4_runtime.immutable(out/'tasks.json',dict(facts_version='v4',tasks=selected))
    out.mkdir(exist_ok=True,parents=True)
    if (out/'gen.jsonl').exists():raise ValueError('already_terminal_partial')
    (out/'gen.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    v4_runtime.immutable(root/'partial_status.json',dict(status='terminal partial, descriptive only',
        complete_tasks=[t['task'] for t in selected],expected_tasks=28,excluded_unfinished_task=True))
    return out if selected else None


def launch(root=ROOT):
    select_model('deepseek-v4-flash')
    from .prepared import verify
    verify()
    root.mkdir(exist_ok=True,parents=True)
    with (root/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'terminal.json').exists() or (root/'generation_frozen.json').exists():
            raise ValueError('completed_or_partial_run_is_terminal')
        rows=json.loads((root/'humaneval/prepared.json').read_text())
        protocol=json.loads((root/'protocol.json').read_text())
        if protocol['sources']!=provenance.sources():raise ValueError('frozen_source_drift')
        if protocol['prepared_sha256']!=provenance.sha(root/'humaneval/prepared.json'):
            raise ValueError('prepared_bundle_drift')
        from .stream_client import OpenRouterClient
        from .transport import Client
        transport=OpenRouterClient(root/'transport',budget_limit=4.2)
        stop=None;complete=False;score=None;score_error=None
        try:
            combined_generation.run(rows,root/'humaneval/generation',v4_runtime.interpreter(),
                                    client=Client(transport),k=1,workers=1)
            complete=True
        except Exception as exc:
            stop=type(exc).__name__+':'+str(exc)[:240]
        finally:transport.close()
        run=root/'humaneval/generation' if complete else paired_prefix(root)
        freeze(root)
        if run is not None:
            try:score=scoring.humaneval(run,root,client=None,k=1)
            except Exception as exc:score_error=type(exc).__name__+':'+str(exc)[:240]
        ledger=transport.ledger()
        record=dict(status='complete' if complete else 'partial',planned_tasks=28,arms=CONFIG['combined']['arms'],K=1,
                    generation_complete=complete,stop_reason=stop,score_error=score_error,
                    scored_tasks=score['ref']['tasks'] if score else 0,
                    known_cost_usd=transport.spent(),physical_attempts=len(ledger['entries']),
                    unresolved_attempts=sum(e.get('cost_usd') is None for e in ledger['entries'].values()),
                    finished_utc=datetime.now(timezone.utc).isoformat())
        atomic_json(root/'terminal.json',record);print(json.dumps(record),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('prepare','launch'))
    a=parser.parse_args()
    if a.command=='prepare':prepare()
    else:launch()


if __name__=='__main__':main()
