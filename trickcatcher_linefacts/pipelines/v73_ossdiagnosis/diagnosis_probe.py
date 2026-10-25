"""Four independent diagnosis calls on two public dev cases; no native/scorer work."""
import argparse
import copy
from datetime import datetime,timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sys

from .ngrok_client import NgrokClient
from .ngrok_run import call,read_record,write_new,digest
from .pipeline import source_identity,checkpoint,load_checkpoint,validate_cohort
from .semantic_contract import writer_packet
from .writer_compiler import compile_response

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SYSTEM='Return a JSON object. Separate spec requirements from observed behavior; unknown claims remain unknown.'
PREMISE='The target code is incorrect, as guaranteed by this frozen known-bug development cohort.'
SEED=20261024
MAX_TOKENS=1536


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def select_cases(requests):
    chosen=[];entries=set()
    for req in sorted(requests,key=lambda r:(len(r['source']),r['case_id'])):
        if req['entry']in entries:continue
        entries.add(req['entry']);chosen.append(req)
        if len(chosen)==2:break
    if len(chosen)!=2:raise ValueError('two_distinct_public_cases_required')
    return chosen


def packet(req,arm):
    if arm=='full_known':
        result=copy.deepcopy(writer_packet(req))
        result['known_bug_premise']=PREMISE
        return result
    if arm!='raw_known':raise ValueError('arm')
    return {**{key:req[key]for key in ('source','entry','spec','public_examples')},
            'known_bug_premise':PREMISE,
            'instruction':('Read the specification and code and explain the most plausible bug hypothesis and '
                'the conditions under which it would violate the specification. Describe the suspect code in '
                'ordinary prose. A redundant but correct branch is not by itself a bug. You may include a '
                'small candidate input if it follows from your reasoning; expected values are optional. '
                'Do not write a repair, replacement program, executable trigger, AST ID or predicate IR. '
                'Separate facts from guesses. If you cannot identify a credible hypothesis, explain your '
                'uncertainty in prose; a nonempty answer is not required to claim a bug. '
                'Return one JSON object with a single analysis string containing your explanation.'),
            'output_schema':{'analysis':'Prose hypothesis, failure condition and supporting reasoning, or explicit uncertainty.'}}


def messages(req,arm):
    return [{'role':'system','content':SYSTEM},
            {'role':'user','content':json.dumps(packet(req,arm),separators=(',',':'))}]


def identity(requests_path):
    import z3
    return {'sources':source_identity(),'config_sha256':sha(HERE/'config.json'),
            'protocol_sha256':sha(HERE/'PREREG_V72.md'),'review_sha256':sha(HERE/'REVIEW_V72.md'),
            'requests_sha256':sha(requests_path),'python':sys.version,'z3':z3.get_full_version()}


def prepare_plan(requests_path,out):
    if out.exists():raise ValueError('fresh_plan_folder_required')
    requests=read_record(requests_path);validate_cohort(requests);chosen=select_cases(requests)
    if [req['case_id']for req in chosen]!=['85','124']:raise ValueError('registered_selection_drift')
    previous=read_record(REPO/'trickcatcher_linefacts/analysis/v71_writercontract/CURRENT_RUN.json')
    old=Path(previous['run_root'])/'generation'
    previous_freeze=read_record(old/'prepare_frozen.json')
    for rel,h in previous_freeze.items():
        if sha(old/rel)!=h:raise ValueError('historical_freeze_mismatch')
    client=NgrokClient();metadata=client.metadata()
    if metadata['model']!='qwen2.5-coder-32b-instruct'or metadata['max_model_len']!=8192:
        raise ValueError('registered_model_context_mismatch')
    jobs=[];historical=[]
    for i,req in enumerate(chosen):
        before=old/req['case_id']/'shared_writer'
        old_request=read_record(before/'request.json');old_response=read_record(before/'response.json')
        expected={'messages':[{'role':'system','content':SYSTEM},
                    {'role':'user','content':json.dumps(writer_packet(req),separators=(',',':'))}],
                  'stage':'writer','seed':SEED,'max_tokens':MAX_TOKENS,'model':client.model,'provider':'ngrok'}
        if old_request!=expected or old_response['request_sha256']!=digest(expected):
            raise ValueError('historical_request_identity_mismatch')
        historical.append({'case_id':req['case_id'],'request':old_request,'response':old_response,
                           'response_sha256':sha(before/'response.json'),'prior_case_result':'historical_not_resampled'})
        order=('raw_known','full_known')if i==0 else ('full_known','raw_known')
        for arm in order:
            msgs=messages(req,arm);token=client.tokenize(msgs)
            if token['count']+MAX_TOKENS>token['max_model_len']:raise ValueError('preflight_context_budget')
            jobs.append({'case_id':req['case_id'],'arm':arm,'messages':msgs,'tokenization':token,
                         'messages_sha256':digest(msgs),'seed':SEED,'max_tokens':MAX_TOKENS})
    out.mkdir(parents=True,exist_ok=False)
    plan={'identity':identity(requests_path),'metadata':metadata,'requests':chosen,'jobs':jobs,
          'historical':historical,'new_logical_calls':4,'max_dispatches':8,'native_calls':0,
          'created_utc':datetime.now(timezone.utc).isoformat()}
    checkpoint(out/'plan.json',plan)
    print(json.dumps({'prepared':True,'case_ids':[r['case_id']for r in chosen],
                     'new_calls':4,'prompt_tokens':[j['tokenization']['count']for j in jobs]}),flush=True)


def summarize(req,arm,response):
    if arm=='full_known':
        accepted,rejected,compilation=compile_response(req,response)
        return {'compiler_admitted':len(accepted),'compiler_rejected':rejected,
                'response_contract':compilation['response_contract'],
                'semantic_status':'unreviewed','compiled':compilation}
    value=response.get('value');valid=(response.get('error')is None and isinstance(value,dict)
                                      and set(value)=={'analysis'}and isinstance(value['analysis'],str))
    return {'simple_schema_valid':valid,'analysis':value.get('analysis')if isinstance(value,dict)else None,
            'semantic_status':'unreviewed'}


def run(requests_path,out):
    plan=load_checkpoint(out/'plan.json')
    if identity(requests_path)!=plan['identity']:raise ValueError('plan_source_or_request_drift')
    lock=(out/'.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if(out/'frozen.json').exists():raise ValueError('run_already_terminal')
    client=NgrokClient();metadata=client.metadata()
    if metadata!=plan['metadata']:raise ValueError('metadata_drift')
    rows=[]
    for job in plan['jobs']:
        req=next(r for r in plan['requests']if r['case_id']==job['case_id'])
        response=call(client,out/job['case_id']/job['arm'],job['messages'],job['arm'],SEED,MAX_TOKENS)
        if response.get('response')and response['response'].get('input_tokens')!=job['tokenization']['count']:
            raise ValueError('prompt_token_usage_mismatch')
        row={'case_id':job['case_id'],'arm':job['arm'],'error':response['error'],
             'assessment':summarize(req,job['arm'],response)}
        checkpoint(out/job['case_id']/job['arm']/'assessment.json',row);rows.append(row)
        print(json.dumps({'case_id':job['case_id'],'arm':job['arm'],'error':response['error']}),flush=True)
    attempts=list(out.glob('*/*/attempt_[0-9][0-9].json'))
    received=[];unknown=0
    for path in attempts:
        receipt=path.with_name(path.stem+'_result.json')
        if receipt.exists()and read_record(receipt).get('status')=='received':received.append(read_record(receipt)['response'])
        else:unknown+=1
    if len(attempts)>8 or len(received)>4:raise ValueError('dispatch_cap')
    if identity(requests_path)!=plan['identity']:raise ValueError('terminal_source_drift')
    result={'rows':rows,'actual_dispatches':len(attempts),'received_responses':len(received),
            'unknown_or_failed_attempts':unknown,'known_input_tokens':sum(r.get('input_tokens')or 0 for r in received),
            'known_output_tokens':sum(r.get('output_tokens')or 0 for r in received),'historical_responses_reused':2,
            'native_calls':0,'private_label_reads':0,'semantic_status':'awaits_public_source_review',
            'finished_utc':datetime.now(timezone.utc).isoformat()}
    checkpoint(out/'summary.json',result)
    checkpoint(out/'frozen.json',{str(p.relative_to(out)):sha(p)for p in sorted(out.rglob('*.json'))})
    print(json.dumps({k:v for k,v in result.items()if k!='rows'}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','run'))
    p.add_argument('--requests',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.command=='prepare':prepare_plan(a.requests,a.out)
    else:run(a.requests,a.out)


if __name__=='__main__':main()
