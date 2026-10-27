"""Resume once after the user refreshed the API key; preserve old root/reserves."""
from pathlib import Path
from decimal import Decimal
import hashlib,json,shutil,sys
from datetime import datetime,timezone

from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter import paths,provenance,v4_runtime,combined_generation,scoring,run_gen,preconditions
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.prepared import verify as verify_prepared
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.run_v81 import prepare,freeze,paired_prefix
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.stream_client import OpenRouterClient
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.transport import Client
from trickcatcher_linefacts.pipelines.v81_deepinfra_quarter.llm_client import atomic_json

REPO=Path(__file__).resolve().parents[3]
PIPE=REPO/'trickcatcher_linefacts/pipelines/v81_deepinfra_quarter'
ANALYSIS=REPO/'trickcatcher_linefacts/analysis/v81_deepinfra_quarter'
OLD=PIPE/'out/deepinfra_quarter'
NEW=PIPE/'out/deepinfra_quarter_resume2_20261027'
CAP=Decimal('4.20')
ENDPOINTS=ANALYSIS/'resume_endpoints_20261027.json'


def run_id_for(all_tasks,python,model):
    exported=tuple(paths.CONFIG['combined']['arms'])
    manifest=dict(version='v4-o0',pipeline_version=paths.CONFIG['VERSION'],facts_version='v4',model=model,k=1,
                  arms=exported,tasks_sha256=run_gen._digest(all_tasks),sources=provenance.sources(),
                  tools=v4_runtime.VERSIONS,prereg_sha256=preconditions.sha((PIPE/'PREREG_V81.md').read_bytes()),
                  python=str(python),generator_python=str(python),n_round2=100,per_fact=2,
                  templates=combined_generation.gen_prompts.TEMPLATE_SHA256)
    if any(paths.CONFIG.get(key) for key in ('strict_round2','placebo_matched','caps','shared_scorer')):
        manifest['fair_flags']={key:paths.CONFIG.get(key,False) for key in ('strict_round2','placebo_matched','caps','shared_scorer')}
    return run_gen._digest(manifest)


def main():
    paths.select_model('deepseek-v4-flash');verify_prepared()
    if NEW.exists():raise ValueError('resume_root_already_exists')
    old_terminal=json.loads((OLD/'terminal.json').read_text())
    if old_terminal['stop_reason']!='AccountingUnknown:api_error:401;reserved_charge_retained':
        raise ValueError('old_terminal_not_expired_key')
    old_ledger=json.loads((OLD/'transport/cost.json').read_text())['entries']
    old_protocol=json.loads((OLD/'protocol.json').read_text())
    if old_protocol['sources']!=provenance.sources():raise ValueError('old_source_identity_drift')
    old_freeze=json.loads((OLD/'generation_frozen.json').read_text())
    if len(old_freeze)!=69 or any(provenance.sha(OLD/name)!=digest for name,digest in old_freeze.items()):
        raise ValueError('old_generation_freeze_drift')
    if provenance.sha(OLD/'humaneval/prepared.json')!=old_protocol['prepared_sha256']:
        raise ValueError('old_prepared_bundle_drift')
    old_known=sum((Decimal(e['cost_usd']) for e in old_ledger.values() if e.get('cost_usd') is not None),Decimal(0))
    old_reserved=sum((Decimal(e['reserved_usd']) for e in old_ledger.values() if e.get('cost_usd') is None),Decimal(0))
    remaining=CAP-old_known-old_reserved
    if remaining<=0:raise ValueError('prior_known_and_reserved_costs_exhaust_cap')
    endpoint_data=json.loads(ENDPOINTS.read_text())['data']
    if endpoint_data.get('id')!=paths.CONFIG['openrouter']['model']:raise ValueError('resume_endpoint_model_mismatch')
    endpoint=next(e for e in endpoint_data['endpoints'] if e.get('tag')=='deepinfra/fp8')
    required={'reasoning','max_tokens','temperature','top_p','response_format'}
    if endpoint.get('status')!=0 or not required<=set(endpoint.get('supported_parameters') or []):
        raise ValueError('resume_provider_not_ready')
    if endpoint['context_length']!=paths.CONFIG['openrouter']['context_length'] or endpoint['max_completion_tokens']<131072:
        raise ValueError('resume_provider_context_drift')
    prices=paths.CONFIG['openrouter']['reservation_price_per_million']
    if any(Decimal(endpoint['pricing'][k])*Decimal(1000000)>Decimal(str(prices[k])) for k in ('prompt','completion')):
        raise ValueError('resume_provider_price_above_ceiling')
    # Preserve source, cohort, prepared public inputs, and 2 fully paired K1 tasks.
    rows=prepare(NEW)
    protocol=dict(old_protocol,prepared_sha256=provenance.sha(NEW/'humaneval/prepared.json'),
                  continuation_of=str(OLD),prior_known_bill_usd=str(old_known),
                  prior_unresolved_reserve_usd=str(old_reserved),remaining_cap_usd=str(remaining),
                  continuation_endpoint_sha256=provenance.sha(ENDPOINTS),
                  failed_slot_retry='same first pending logical slot after expired-key repair')
    v4_runtime.immutable(NEW/'protocol.json',protocol)
    old_tasks=json.loads((OLD/'humaneval/generation/tasks.json').read_text())['tasks']
    prior_done=json.loads((OLD/'humaneval/generation/completed_tasks.json').read_text())
    if prior_done!=[3,10]:raise ValueError('unexpected_old_paired_prefix')
    new_ids=[r['baseline']['task'] for r in rows]
    if [t['task'] for t in old_tasks]!=new_ids:raise ValueError('prepared_task_manifest_mismatch')
    cached=OLD/'humaneval/generation/artifacts';target=NEW/'humaneval/generation/artifacts'
    # Task15's baseline arm completed before the expired-key rejection stopped
    # its combined arm. Reuse it too; the first new dispatch must be its exact
    # previously failed combined request.
    reuse={3:paths.CONFIG['combined']['arms'],10:paths.CONFIG['combined']['arms'],15:['concept-hybrid']}
    for task,arms in reuse.items():
        for arm in arms:
            shutil.copytree(cached/str(task)/'0'/arm,target/str(task)/'0'/arm)
    python=v4_runtime.interpreter();expected=run_id_for(rows,python,paths.CONFIG['openrouter']['model'])
    for task,arms in reuse.items():
        for arm in arms:
            got=json.loads((target/str(task)/'0'/arm/'result.json').read_text())
            if got.get('run_id')!=expected:raise ValueError('cached_pair_run_id_mismatch')
    attempt401=next(k for k,e in old_ledger.items() if e['state']=='unknown' and e.get('http_status') is None)
    expected_slot=attempt401.rsplit('/attempt-',1)[0]
    manifest=dict(version='v4-o0',pipeline_version=paths.CONFIG['VERSION'],facts_version='v4',
                  model=paths.CONFIG['openrouter']['model'],k=1,arms=tuple(paths.CONFIG['combined']['arms']),
                  tasks_sha256=run_gen._digest(rows),sources=provenance.sources(),tools=v4_runtime.VERSIONS,
                  prereg_sha256=preconditions.sha((PIPE/'PREREG_V81.md').read_bytes()),python=str(python),generator_python=str(python),
                  n_round2=100,per_fact=2,templates=combined_generation.gen_prompts.TEMPLATE_SHA256)
    if any(paths.CONFIG.get(k) for k in ('strict_round2','placebo_matched','caps','shared_scorer')):
        manifest['fair_flags']={k:paths.CONFIG.get(k,False) for k in ('strict_round2','placebo_matched','caps','shared_scorer')}
    if run_gen._digest(manifest)!=expected:raise ValueError('cached_manifest_identity_mismatch')
    client=OpenRouterClient(NEW/'transport',budget_limit=remaining)
    original=client.complete;seen=[False]
    def require_same_failed_slot(request):
        if not seen[0]:
            if request['slot']!=expected_slot:raise ValueError('first_retried_slot_not_original401')
            seen[0]=True
        return original(request)
    client.complete=require_same_failed_slot
    generation_complete=False;stop=None;score_error=None;score=None
    try:
        combined_generation.run(rows,NEW/'humaneval/generation',python,client=Client(client),k=1,workers=1)
        generation_complete=True
    except Exception as exc:
        stop=type(exc).__name__+':'+str(exc)[:240]
    finally:client.close()
    run=NEW/'humaneval/generation' if generation_complete else paired_prefix(NEW)
    freeze(NEW)
    if run is not None:
        try:score=scoring.humaneval(run,NEW,client=None,k=1)
        except Exception as exc:score_error=type(exc).__name__+':'+str(exc)[:240]
    ledger=json.loads((NEW/'transport/cost.json').read_text())['entries']
    new_known=sum((Decimal(e['cost_usd']) for e in ledger.values() if e.get('cost_usd') is not None),Decimal(0))
    new_reserved=sum((Decimal(e['reserved_usd']) for e in ledger.values() if e.get('cost_usd') is None),Decimal(0))
    terminal=dict(status='complete' if generation_complete else 'partial',continuation_of=str(OLD),
                  planned_tasks=28,completed_prefix=json.loads((NEW/'humaneval/generation/completed_tasks.json').read_text()),
                  arms=paths.CONFIG['combined']['arms'],K=1,generation_complete=generation_complete,
                  first_dispatch_retried_original401=seen[0],stop_reason=stop,score_error=score_error,
                  scored_tasks=score['ref']['tasks'] if score else 0,old_known_bill_usd=str(old_known),
                  old_unresolved_reserve_usd=str(old_reserved),new_known_bill_usd=str(new_known),
                  new_unresolved_reserve_usd=str(new_reserved),cumulative_known_bill_usd=str(old_known+new_known),
                  cumulative_unknown_reservations_usd=str(old_reserved+new_reserved),hard_cap_usd=str(CAP),
                  physical_attempts=len(old_ledger)+len(ledger),finished_utc=datetime.now(timezone.utc).isoformat())
    atomic_json(NEW/'terminal.json',terminal)
    audit=dict(terminal=terminal,prior_terminal=json.loads((OLD/'terminal.json').read_text()),
               prior_and_new_sources_verified=True,prior_and_new_generation_freezes_verified=True,
               source_hashes=provenance.sources(),old_frozen_entries=len(json.loads((OLD/'generation_frozen.json').read_text())),
               new_frozen_entries=len(json.loads((NEW/'generation_frozen.json').read_text())),
               prior_responses_reused_tasks=prior_done,no_prior_failed_attempt_removed=True)
    atomic_json(ANALYSIS/'RESUME_AUDIT.json',audit)
    print(json.dumps(terminal),flush=True)


if __name__=='__main__':main()
