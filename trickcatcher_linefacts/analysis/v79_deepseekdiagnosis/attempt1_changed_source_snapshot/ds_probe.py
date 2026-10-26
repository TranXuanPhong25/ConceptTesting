"""Exact v72 prompt replay on user-authorized OpenRouter model; four paid slots."""
import argparse
from datetime import datetime,timezone
from decimal import Decimal
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys

from .pipeline import checkpoint,load_checkpoint,source_identity
from .ngrok_run import read_record,digest
from .ngrok_client import json_object
from .diagnosis_probe import messages,summarize
from .openrouter_stream import MODEL,PROVIDER,MAX_TOKENS,payload,reservation,prompt_envelope,dispatch,known_cost

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def identity():
    return {'sources':source_identity(),'config_sha256':sha(HERE/'config.json'),
            'protocol_sha256':sha(HERE/'PREREG_V79.md'),'review_sha256':sha(HERE/'REVIEW_V79.md'),
            'python':sys.version}


def prepare(out,endpoints_path):
    if out.exists():raise ValueError('fresh_output_required')
    if not os.environ.get('OPENROUTER_API_KEY'):raise ValueError('missing_openrouter_key')
    cap=min(Decimal(os.environ.get('OPENROUTER_MAX_USD','5')),Decimal('0.15'))
    if not cap.is_finite()or cap<=0:raise ValueError('positive_run_cap_required')
    old=REPO/'trickcatcher_linefacts/analysis/v72_diagnosisprobe'
    previous=read_record(old/'CURRENT_RUN.json');qroot=Path(previous['out'])
    qplan=load_checkpoint(qroot/'plan.json');qfreeze=load_checkpoint(qroot/'frozen.json')
    for rel,h in qfreeze.items():
        if sha(qroot/rel)!=h:raise ValueError('qwen_frozen_artifact_drift')
    metadata=read_record(endpoints_path)['data']
    if metadata.get('id')!=MODEL:raise ValueError('model_endpoint_metadata_mismatch')
    required={'reasoning','max_tokens','temperature','top_p','response_format'}
    eligible=[]
    for endpoint in metadata['endpoints']:
        prices=endpoint.get('pricing')or{}
        if(endpoint.get('tag')=='relace/fp4' and endpoint.get('status')==0 and required<=set(endpoint.get('supported_parameters')or[])and
           Decimal(prices.get('prompt','999'))<=Decimal(str(PROVIDER['max_price']['prompt']))/1000000 and
           Decimal(prices.get('completion','999'))<=Decimal(str(PROVIDER['max_price']['completion']))/1000000 and
           (endpoint.get('max_completion_tokens')or 0)>=MAX_TOKENS):
            eligible.append({k:endpoint.get(k)for k in('provider_name','tag','pricing','context_length','max_completion_tokens','quantization')})
    if not eligible:raise ValueError('no_advertised_eligible_low_price_provider')
    eligible.sort(key=lambda e:(Decimal(e['pricing']['prompt']),Decimal(e['pricing']['completion'])))
    jobs=[]
    for previous_job in qplan['jobs']:
        req=next(r for r in qplan['requests']if r['case_id']==previous_job['case_id'])
        if messages(req,previous_job['arm'])!=previous_job['messages']:raise ValueError('prompt_drift')
        request=payload(previous_job['messages']);maximum=reservation(request)
        prompt_bound=prompt_envelope(request)
        context=eligible[0].get('context_length')
        if type(context) is not int or prompt_bound+MAX_TOKENS>context:
            raise ValueError('context_envelope_exceeds_exact_provider_limit')
        jobs.append({'case_id':previous_job['case_id'],'arm':previous_job['arm'],'request':request,
                     'request_sha256':digest(request),'messages_sha256':digest(previous_job['messages']),
                     'prompt_token_envelope':prompt_bound,'context_limit':context,
                     'worstcase_usd':str(maximum)})
    total=sum((Decimal(j['worstcase_usd'])for j in jobs),Decimal(0))
    if len(jobs)!=4 or total>cap:raise ValueError('four_slot_worstcase_exceeds_run_cap')
    out.mkdir(parents=True,exist_ok=False)
    plan={'identity':identity(),'model':MODEL,'jobs':jobs,'requests':qplan['requests'],
          'historical_qwen_root':str(qroot),'historical_freeze_sha256':sha(qroot/'frozen.json'),
          'endpoints_sha256':sha(endpoints_path),'eligible_providers':eligible,
          'run_cap_usd':str(cap),'sum_worstcase_usd':str(total),'max_paid_dispatches':4,
          'created_utc':datetime.now(timezone.utc).isoformat()}
    checkpoint(out/'plan.json',plan)
    print(json.dumps({'prepared':True,'jobs':4,'run_cap_usd':str(cap),'worstcase_usd':str(total),
                      'cheapest_advertised_eligible':eligible[0]}),flush=True)


def run(out):
    plan=load_checkpoint(out/'plan.json')
    if identity()!=plan['identity']:raise ValueError('source_drift')
    lock=(out/'.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if list(out.glob('*/*/attempt.json'))or(out/'summary.json').exists():raise ValueError('no_paid_retry_or_duplicate_run')
    rows=[];spent=Decimal(0);stop_reason=None
    try:
        for job in plan['jobs']:
            bound=Decimal(job['worstcase_usd'])
            live_cap=min(Decimal(plan['run_cap_usd']),Decimal(os.environ.get('OPENROUTER_MAX_USD','5')))
            if not live_cap.is_finite()or spent+bound>live_cap:raise ValueError('run_cost_cap')
            if digest(job['request'])!=job['request_sha256']:raise ValueError('payload_drift')
            folder=out/job['case_id']/job['arm'];folder.mkdir(parents=True,exist_ok=False)
            checkpoint(folder/'request.json',job['request'])
            checkpoint(folder/'attempt.json',{'request_sha256':job['request_sha256'],'status':'dispatched_cost_unknown',
                                           'worstcase_reserved_usd':str(bound),'time_utc':datetime.now(timezone.utc).isoformat()})
            result,raw,stderr=dispatch(folder/'request.json')
            (folder/'response.sse').write_text(raw);(folder/'curl.stderr.txt').write_text(stderr)
            checkpoint(folder/'stream_result.json',result)
            # Actual cost is required before any additional paid dispatch.
            try:cost=known_cost(result)
            except ValueError as exc:
                raise ValueError(str(result.get('stream_error') or 'no_stream_error')+';'+str(exc)) from None
            spent+=cost
            checkpoint(folder/'cost_receipt.json',{'actual_cost_usd':str(cost),'cumulative_cost_usd':str(spent),
                                                 'usage':result['usage'],'provider':result['provider']})
            if result['stream_error']is not None:raise ValueError(result['stream_error'])
            if result['model']!=MODEL:raise ValueError('served_model_mismatch')
            if result['provider']!='Relace':raise ValueError('served_provider_mismatch')
            error=None;value=None
            if result['finish_reason']!='stop':error='incomplete_completion'
            else:
                try:value=json_object(result['content'])
                except (ValueError,TypeError):error='invalid_json_object'
            response={'request_sha256':job['request_sha256'],'error':error,'value':value,'response':result}
            checkpoint(folder/'response.json',response)
            req=next(r for r in plan['requests']if r['case_id']==job['case_id'])
            assessment=summarize(req,job['arm'],response)
            row={'case_id':job['case_id'],'arm':job['arm'],'error':error,'cost_usd':str(cost),
                 'provider':result['provider'],'assessment':assessment}
            checkpoint(folder/'assessment.json',row);rows.append(row)
            print(json.dumps({'case_id':job['case_id'],'arm':job['arm'],'provider':result['provider'],
                              'cost_usd':str(cost),'error':error}),flush=True)
    except Exception as exc:
        stop_reason=type(exc).__name__+':'+str(exc)[:160]
    if identity()!=plan['identity']:raise ValueError('terminal_source_drift')
    attempts=list(out.glob('*/*/attempt.json'));receipts=list(out.glob('*/*/cost_receipt.json'))
    summary={'rows':rows,'completed':len(rows)==4 and stop_reason is None,'stop_reason':stop_reason,
             'paid_dispatches':len(attempts),'known_cost_receipts':len(receipts),
             'unknown_cost_attempts':len(attempts)-len(receipts),'actual_known_cost_usd':str(spent),
             'model':MODEL,'new_model_calls':len(attempts),'native_calls':0,'private_labels_read':0,
             'finished_utc':datetime.now(timezone.utc).isoformat()}
    checkpoint(out/'summary.json',summary)
    checkpoint(out/'frozen.json',{str(p.relative_to(out)):sha(p)for p in sorted(out.rglob('*'))if p.is_file()and p.name!='.lock'})
    print(json.dumps({k:v for k,v in summary.items()if k!='rows'}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('prepare','run'))
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--endpoints',type=Path)
    a=parser.parse_args()
    if a.command=='prepare':
        if a.endpoints is None:raise ValueError('endpoint_metadata_required')
        prepare(a.out,a.endpoints)
    else:run(a.out)


if __name__=='__main__':main()
