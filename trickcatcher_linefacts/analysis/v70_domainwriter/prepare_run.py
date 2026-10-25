"""Detached prepare-only run with immutable inputs and terminal public audit.

No endpoint values in command arguments, artifacts or output. Inherits private env.
No retries, arm calls, scoring, or additional model/PUT execution in summarization.
"""
import argparse
import ast
import collections
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from trickcatcher_linefacts.pipelines.v70_domainwriter.pipeline import (
    readiness_identity,load_checkpoint,contexts,validate_cohort)
from trickcatcher_linefacts.pipelines.v70_domainwriter.evidence_gate import realized
from trickcatcher_linefacts.pipelines.v70_domainwriter.writer_compiler import compile_and_admit
from trickcatcher_linefacts.pipelines.v70_domainwriter.domain_constraints import public_domain,check_domain

REPO=Path(__file__).resolve().parents[3]
MODULE='trickcatcher_linefacts.pipelines.v70_domainwriter.pipeline'

def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_new(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2)
def now():return datetime.now(timezone.utc).isoformat()
def status(root,**value):
    (root/'status.json').write_text(json.dumps(dict(updated_utc=now(),**value),indent=2)+'\n')


def audit(root,requests_path,approval_path,code):
    gen=root/'generation';requests=read(requests_path)
    if read(approval_path)!={'status':'reviewed_ready','identity':readiness_identity(requests_path)}:
        raise ValueError('postrun_source_or_identity_drift')
    rows=[];known_in=0;known_out=0;attempts=0;responses=0;unknown_attempts=0
    gate=load_checkpoint(gen/'admission_gate.json') if (gen/'admission_gate.json').exists() else None
    context_packets={};preflight=read(Path(__file__).with_name('preflight.json'))
    preflight_rows={r['case_id']:r for r in preflight['rows']}
    for request in requests:
        folder=gen/request['case_id'];response_path=folder/'shared_writer'/'response.json'
        response=read(response_path)if response_path.exists()else None
        record_rows=[]
        proposals=((response or {}).get('value')or{}).get('hypotheses',[])
        hypotheses,rejected,compilation=compile_and_admit(request,proposals,mode='writer')
        if response is not None:
            identity=read(folder/'shared_writer'/'request.json')
            actual_hash=hashlib.sha256(json.dumps(identity['messages'],sort_keys=True).encode()).hexdigest()
            if actual_hash!=preflight_rows[request['case_id']]['messages_sha256']:raise ValueError('actual_prompt_drift')
            tokens=read(folder/'shared_writer'/'tokenization.json')
            if tokens['count']!=preflight_rows[request['case_id']]['prompt_tokens']:raise ValueError('tokenization_drift')
            actual_tokens=(response.get('response')or{}).get('input_tokens')
            if actual_tokens is not None and actual_tokens!=tokens['count']:raise ValueError('server_prompt_usage_mismatch')
        compiled=folder/'writer_compilation.json'
        if compiled.exists() and load_checkpoint(compiled)!=compilation:raise ValueError('compilation_drift')
        checkpoint=folder/'construction.json'
        construction=load_checkpoint(checkpoint)if checkpoint.exists()else None
        if construction is not None:
            if construction['input_domain']!=public_domain(request):raise ValueError('domain_drift')
            context_packets[request['case_id']]=contexts(request,construction)
            for r in construction['records']:
                runs=r['runs']
                record_rows.append(dict(hypothesis_id=r['hypothesis']['id'],
                    public_status=r.get('public_consistency',{}).get('status','missing'),
                    public_executions=r.get('public_consistency',{}).get('native_executions',0),
                    public_failures=[{'example':x['example'],'program':x['program'],'normal':x['normal'],'matches':x['matches']}
                                     for x in r.get('public_consistency',{}).get('rows',[])if not x['matches']],
                    construction_status=r['construction'].get('status'),issues=r['construction'].get('issues',[]),
                    realized=sum(realized(x)for x in runs),sensitive=sum(realized(x)and x.get('output_sensitivity')is True for x in runs),
                    domain_valid=sum(check_domain(construction['input_domain'],ast.literal_eval(x['arguments']))['passed']for x in runs),
                    domain_pruned_shapes=r['construction'].get('domain_pruned_shapes',0),
                    domain_mismatches=r['construction'].get('domain_mismatches',0)))
        writer_folder=folder/'shared_writer'
        for path in sorted(writer_folder.glob('attempt_[0-9][0-9].json')):
            attempts+=1;receipt=path.with_name(path.stem+'_result.json')
            if not receipt.exists():unknown_attempts+=1;continue
            received=read(receipt)
            if received.get('status')=='received':
                responses+=1;r=received['response'];i=r.get('input_tokens');o=r.get('output_tokens')
                if type(i)is int:known_in+=i
                if type(o)is int:known_out+=o
            else:unknown_attempts+=1
        gate_row=next((x for x in (gate or {}).get('rows',[])if x['case_id']==request['case_id']),None)
        rows.append(dict(case_id=request['case_id'],writer_error=response.get('error')if response else 'not_completed',
                         received=response is not None,admitted=len(hypotheses),
                         rejected=rejected,writer_finish_reason=((response or {}).get('response')or{}).get('finish_reason'),
                         native_executions=construction.get('native_executions',0)if construction else None,
                         candidates=construction.get('candidates_tested',0)if construction else None,
                         hypotheses=record_rows,gate=gate_row))
    forbidden=[p for p in gen.rglob('response.json')if p.parent.name!='shared_writer']
    if forbidden:raise ValueError('unexpected_arm_generation')
    if attempts>12 or responses>6:raise ValueError('dispatch_cap_violation')
    source=json.loads((root/'frozen_before_dispatch.json').read_text())
    for path,digest in source['source_files'].items():
        if sha(REPO/path)!=digest:raise ValueError('frozen_source_drift')
    result=dict(stage='prepare_only',pipeline_exit_code=code,case_count=len(requests),rows=rows,
                completed=code==0 and gate is not None and len(gate['rows'])==6,
                gate_passed=(gate or {}).get('passed'),arm_calls=0,private_scoring=False,
                actual_dispatches=attempts,received_responses=responses,unknown_or_failed_attempts=unknown_attempts,
                known_input_tokens=known_in,known_output_tokens=known_out,
                input_expected_counts='not_scored',hypothesis_truth='unverified',
                prepared_contexts_are_not_dispatched_generator_prompts=True,
                sources_unchanged=True,requests_sha256=sha(requests_path),finished_utc=now())
    write_new(gen/'prepared_contexts.json',context_packets)
    write_new(gen/'prepare_summary.json',result)
    freeze={str(p.relative_to(gen)):sha(p)for p in sorted(gen.rglob('*.json'))}
    write_new(gen/'prepare_frozen.json',freeze)
    write_new(root/'terminal.json',dict(summary_sha256=sha(gen/'prepare_summary.json'),
                                     freeze_sha256=sha(gen/'prepare_frozen.json'),status='complete'if result['completed']else 'stopped',
                                     finished_utc=now()))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,required=True);a=p.parse_args()
    root=a.run_root.resolve();root.mkdir(parents=True,exist_ok=True)
    lock=(root/'.controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (root/'terminal.json').exists():raise ValueError('run_already_terminal')
    requests=root/'preparation'/'requests.json';approval=root/'reviewed_ready.json'
    validate_cohort(read(requests))
    if read(approval)!={'status':'reviewed_ready','identity':readiness_identity(requests)}:
        raise ValueError('fresh_readiness_required')
    manifest=read(root/'frozen_before_dispatch.json')
    for path,digest in manifest['source_files'].items():
        if sha(REPO/path)!=digest:raise ValueError('prelaunch_frozen_source_drift')
    generation=root/'generation';generation.mkdir(exist_ok=True)
    status(root,state='launching_prepare_only',arm_calls=0)
    command=[sys.executable,'-B','-m',MODULE,'--online','--prepare-only','--requests',str(requests),
             '--out',str(generation),'--approval',str(approval)]
    with (root/'pipeline.log').open('a') as log:
        child=subprocess.Popen(command,cwd=REPO,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        write_new(root/'child_process.json',dict(pid=child.pid,module=MODULE,started_utc=now(),prepare_only=True))
        status(root,state='prepare_only_running',pid=child.pid,arm_calls=0)
        try:code=child.wait(timeout=5400)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            code=124
    try:
        result=audit(root,requests,approval,code)
        status(root,state='complete'if result['completed']else 'stopped',gate_passed=result['gate_passed'],arm_calls=0)
        print(json.dumps({k:result[k]for k in ('completed','gate_passed','actual_dispatches','received_responses','known_input_tokens','known_output_tokens','arm_calls')}),flush=True)
    except Exception as exc:
        status(root,state='audit_failed',error_type=type(exc).__name__,arm_calls=0)
        raise

if __name__=='__main__':main()
