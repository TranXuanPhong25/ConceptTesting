"""Controlled16 fixture run. No real20 run, canonical oracle or automatic semantic pass."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import threading
from . import paths,source_view,pilot_fixtures,schemas
from .online_chain import OnlineChain
from .online_transport import Connection,Tokenizer,OnlineTransport
from .llm_client import atomic_json
from .v4_runtime import immutable
HERE=Path(__file__).resolve().parent;ROOT=paths.DATA_OUT/'qwen_chain_pilot'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    rows=pilot_fixtures.cases()
    immutable(ROOT/'fixture_packets.json',rows)
    files={p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.json','.jinja','.md')}
    protocol=dict(scope='P2 controlled16 only; no D_IO or automatic real20',sources=files,fixture_packet_sha256=sha(ROOT/'fixture_packets.json'),model=paths.CONFIG['chain']['model'],human_semantic_gate='pending_independent_adjudication')
    immutable(ROOT/'protocol.json',protocol);return protocol


def verify_models(connection):
    data=connection.call('/models',timeout=15);model=next((r for r in data.get('data',[]) if r.get('id')==paths.CONFIG['chain']['model']),None)
    if not model or model.get('max_model_len')!=paths.CONFIG['chain']['context_window_tokens']:raise RuntimeError('pinned_model_or_context_unavailable')
    immutable(ROOT/'server_metadata.json',{k:model.get(k) for k in ('id','max_model_len','root')})


def run(workers):
    freeze();connection=Connection();verify_models(connection)
    tokenizer=Tokenizer(connection,ROOT/'tokenizer_cache');transport=OnlineTransport(connection,ROOT/'physical_calls.jsonl');abort=threading.Event();transport.abort=abort
    def one(case):
        if abort.is_set():return
        # No evaluator label, witness or applicability field enters generation.
        task=source_view.prepare(case['source'],case['entry'],case['base'],valid_code=case['valid_code'])
        chain=OnlineChain(task,ROOT/'cases'/case['fixture_id'])
        try:
            for stage in schemas.STAGES:
                if abort.is_set():return
                result=chain.run_stage(stage,tokenizer,transport)
                if stage in ('S4','S5') and result['state']=='valid':chain.execute_fixture_slots(stage)
                print(case['fixture_id'],stage,result['state'],result.get('reason',''),flush=True)
            immutable(ROOT/'cases'/case['fixture_id']/'summary.json',chain.report())
        except BaseException:
            abort.set();raise
    with ThreadPoolExecutor(workers) as pool:list(pool.map(one,pilot_fixtures.order()))
    files=sorted((ROOT/'cases').rglob('*.json'))
    immutable(ROOT/'generation_frozen.json',{str(p.relative_to(ROOT)):sha(p) for p in files})


def report():
    if not (ROOT/'generation_frozen.json').exists():raise RuntimeError('generation_incomplete_no_report')
    freeze();snapshot=json.loads((ROOT/'generation_frozen.json').read_text())
    for name,digest in snapshot.items():
        if sha(ROOT/name)!=digest:raise RuntimeError('generation_snapshot_changed')
    rows=[];packets=[];stage_counts={s:{} for s in schemas.STAGES};required=62;optional=0;valid_slots=0;probe_parseable=0;probe_admissible=0
    for case in pilot_fixtures.cases():
        directory=ROOT/'cases'/case['fixture_id'];summary=json.loads((directory/'summary.json').read_text());state=json.loads((directory/'state.json').read_text())
        applicable=case['evaluator']['probe_applicable'];states=summary['states']
        for stage in schemas.STAGES:
            status=states[stage];stage_counts[stage][status]=stage_counts[stage].get(status,0)+1
            mandatory=stage in ('S1','S2','S3') or applicable
            attempted=stage in state['stages']
            if not mandatory and attempted:optional+=1
            if (mandatory or attempted) and status=='valid':valid_slots+=1
        accepted=sum(1 for r in state['inputs'].values() if r.get('result') and r['result'].get('worker_details',{}).get('ordinary',{}).get('validity_provenance')=='mined_filter_not_spec_proof' and r['result']['status']!='filtered')
        if applicable:
            probe_parseable+=states['S4']=='valid' and states['S5']=='valid'
            probe_admissible+=accepted>0
        row=dict(fixture_id=case['fixture_id'],**summary,accepted_unique_inputs=accepted,probe_applicable=applicable,stage_errors={s:r.get('reason') for s,r in state['stages'].items() if r['state']=='failed'})
        rows.append(row);packets.append(dict(fixture_id=case['fixture_id'],source=case['source'],evaluator=case['evaluator'],stages=state['stages'],feedback=state['feedback'],semantic_labels='pending_human_review_not_model_self_grade'))
    ledger=[json.loads(x) for x in (ROOT/'physical_calls.jsonl').read_text().splitlines()] if (ROOT/'physical_calls.jsonl').exists() else []
    metas=[json.loads(x) for x in (ROOT/'tokenizer_cache/metadata_calls.jsonl').read_text().splitlines()] if (ROOT/'tokenizer_cache/metadata_calls.jsonl').exists() else []
    costs=dict(scheduled_slots=80,physical_completion_attempts=len(ledger),received_completions=sum(r['status']=='response_received' for r in ledger),input_tokens=sum(r['n_in'] for r in ledger if type(r.get('n_in')) is int),output_tokens=sum(r['n_out'] for r in ledger if type(r.get('n_out')) is int),unknown_usage_attempts=sum(r['status']!='response_received' or type(r.get('n_out')) is not int for r in ledger),tokenizer_metadata_calls=len(metas),tokenizer_metadata_errors=sum(r['status']!='ok' for r in metas))
    result=dict(scope='controlled16 authored fixtures, five-stage Qwen pilot; no D_IO',tasks=16,stage_counts=stage_counts,costs=costs,mechanical_gates=dict(required_slots=required,optional_attempted_slots=optional,valid_required_or_requested=valid_slots,stage_validity=valid_slots/(required+optional),stage_validity_passed=valid_slots/(required+optional)>=.9,probe_parseable=probe_parseable,probe_admissible=probe_admissible,probe_required=7,probe_parseable_passed=probe_parseable>=6,probe_admissible_passed=probe_admissible>=6),semantic_gate=dict(state='pending_independent_human_adjudication',threshold='12/16',accuracy=None),advance_to_real20=False,D_IO=None,rows=rows)
    atomic_json(ROOT/'review_packets.json',packets);immutable(ROOT/'report.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2));return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['all','report']);p.add_argument('--workers',type=int,default=2);a=p.parse_args()
    if a.stage=='all':run(a.workers)
    report()


if __name__=='__main__':main()
