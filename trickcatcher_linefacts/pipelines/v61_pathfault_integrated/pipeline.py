"""Integrated public-only writer→construction→generator→final realization lifecycle.

No private evaluator imports. Model dispatch uses reviewed bounded ngrok transport.
Prepared comparisons still require prospective protocol/review before real model runs.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
import fcntl
import time
from .ngrok_client import NgrokClient
from .ngrok_run import call,write_new,read_record
from .semantic_contract import writer_packet,admit
from .joint_constructor import construct_case,verify_input
from .predicates import evaluate
from .construction import replay

HERE=Path(__file__).resolve().parent
ARMS=('plain','explicit_pattern','concept','equal_evidence_raw','inputs_only')
SEEDS=(20261024,20261025)


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def source_identity():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))}


def checkpoint(path,value):
    write_new(path,value)
    write_new(path.with_suffix('.sha256.json'),{'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})


def load_checkpoint(path):
    receipt=path.with_suffix('.sha256.json')
    if not receipt.exists()or read_record(receipt)!={'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}:
        raise ValueError('checkpoint_integrity')
    return read_record(path)


def readiness_identity(requests_path):
    import z3
    config=read_record(HERE/'config.json')
    from .baseline_adapter import prompt_artifact
    return {'sources':source_identity(),'author_baseline_sha256':prompt_artifact()[1],'requests_sha256':hashlib.sha256(requests_path.read_bytes()).hexdigest(),
            'config_sha256':hashlib.sha256((HERE/'config.json').read_bytes()).hexdigest(),
            'python':sys.version,'z3':z3.get_full_version(),'fixed_ids':config['pathfault_complete']['case_ids']}


def validate_cohort(requests):
    from .deep_run import validate_request
    ids=read_record(HERE/'config.json')['pathfault_complete']['case_ids']
    if not isinstance(requests,list)or [r.get('case_id')for r in requests]!=ids:raise ValueError('fixed_cohort_mismatch')
    if len(set(ids))!=len(ids):raise ValueError('duplicate_case_id')
    for r in requests:validate_request(r)


def check_freeze(root):
    for rel,h in read_record(root/'generation_frozen.json').items():
        path=(root/rel).resolve()
        if root.resolve()not in path.parents or not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=h:
            raise ValueError('generation_freeze_mismatch')


def contexts(request,construction):
    evidence=[];inputs=[]
    for record in construction['records']:
        witnesses=[r for r in record['runs'] if r.get('stable') and r.get('normal') and r.get('site_realized')
                   and r.get('predicate_realized') and r.get('event_realized') and not r.get('event_unknown')][:2]
        evidence.append({'hypothesis':record['hypothesis'],'construction':record['construction'],
                         'witnesses':[dict({k:v for k,v in r.items()if k!='observations'},observed_outputs={name:obs.get('output')for name,obs in r['observations'][0].items()if isinstance(obs,dict)})for r in witnesses]})
        inputs.extend(r['arguments'] for r in witnesses)
    common={k:request[k] for k in ('source','entry','public_examples')}
    common['spec']=request.get('spec','')
    common['known_bug_premise']='The target code is incorrect, as guaranteed by this frozen known-bug development cohort.'
    note='Compute expected outputs from specification; observed PUT/alternative outputs are not oracle answers. Respect original domain.'
    from .baseline_adapter import adapt
    pattern=adapt(request)
    return {
        'plain':dict(common,instruction='Generate valid tests. '+note),
        'explicit_pattern':dict({k:v for k,v in common.items()if k not in ('source','spec')},instruction=pattern['prompt']+' '+note,baseline_provenance={k:v for k,v in pattern.items()if k!='prompt'}),
        'concept':dict(common,instruction='Use source-bound concept obligations and verify reach/local distinction/propagation. '+note,evidence=evidence),
        'equal_evidence_raw':dict(common,instruction='Use the complete tool evidence to generate tests. '+note,evidence=evidence),
        'inputs_only':dict(common,instruction='Consider supplied input candidates when generating valid tests. '+note,inputs=list(dict.fromkeys(inputs))),
    }


def final_audit(request,tests,hypotheses,max_executions=96):
    """Recheck changed final inputs; a prior witness certificate never transfers."""
    rows=[];executions=0
    for index,item in enumerate(tests[:6]):
        row={'position':index,'raw':item,'realization':[]}
        try:
            args=ast.literal_eval(item['arguments']);ast.literal_eval(item['expected'])
            if type(args)is not tuple:raise ValueError('argument_tuple')
        except (TypeError,KeyError,ValueError,SyntaxError):
            row['status']='malformed';rows.append(row);continue
        row['status']='parsed'
        for h in hypotheses:
            try:condition=evaluate(h['trigger'],args) is True
            except (TypeError,ValueError,IndexError,ZeroDivisionError):condition=False
            r={'hypothesis_id':h['id'],'predicate_realized':condition,'site_realized':'unknown','output_sensitivity':'unknown'}
            needed=8 if h['alternative']is not None else 4
            if condition and executions+needed<=max_executions:
                verified=verify_input(request,h,args,{'repeat_seeds':SEEDS,'repeats_per_program_seed':2},time.monotonic()+8)
                executions+=verified['native_executions'];r.update({k:v for k,v in verified.items()if k not in ('observations','arguments')})
                r['scope']='rechecked_final_input_exact_site_event_repeatability_and_alternative'
            elif condition:r['scope']='final_audit_budget_exhausted'
            row['realization'].append(r)
        rows.append(row)
    return {'rows':rows,'native_executions':executions,'private_data_used':False}


def generate_case(client,request,out):
    identity={'request':request,'model':client.model,'sources':source_identity(),'python':sys.version}
    out.mkdir(parents=True,exist_ok=True)
    protocol=out/'case_protocol.json'
    if protocol.exists():
        if read_record(protocol)!=identity:raise ValueError('case_protocol_drift')
    else:write_new(protocol,identity)
    done=out/'result.json'
    if done.exists():return load_checkpoint(done)
    system='Return a JSON object. Separate spec requirements from observed behavior; unknown claims remain unknown.'
    writer=writer_packet(request)
    response=call(client,out/'shared_writer',[{'role':'system','content':system},{'role':'user','content':json.dumps(writer)}],'writer',20261024,1536)
    proposals=(response.get('value')or{}).get('hypotheses',[])
    hypotheses,rejected=admit(request,proposals)
    cpu=out/'construction.json'
    if cpu.exists():construction=load_checkpoint(cpu)
    else:
        construction=construct_case(request,hypotheses,{'max_case_seconds':120,'repeat_seeds':SEEDS,'repeats_per_program_seed':2})
        checkpoint(cpu,construction)
    arm_context=contexts(request,construction)
    assert arm_context['concept']['evidence']==arm_context['equal_evidence_raw']['evidence']
    arms={}
    schema={'tests':[{'arguments':'Python positional tuple literal','expected':'Python literal'}],'reason':'brief'}
    # Deep/raw/input packages allocate the shared writer as their planning call.
    # Plain/pattern receive an actually usable planning call under the same cap.
    for arm in ARMS:
        history=[]
        stages=['probe1','probe2','final'] if arm in ('concept','equal_evidence_raw','inputs_only') else ['plan','probe1','probe2','final']
        for i,stage in enumerate(stages):
            feedback_path=out/arm/stage/'feedback.json'
            if feedback_path.exists():history.append(load_checkpoint(feedback_path));continue
            content={'context':arm_context[arm],'earlier_feedback':history,'output_schema':schema,
                     'instruction':'Return up to six tests with expected outputs from spec.'}
            record=call(client,out/arm/stage,[{'role':'system','content':system},{'role':'user','content':json.dumps(content)}],stage,20261024+i,1536)
            tests=(record.get('value')or{}).get('tests',[])
            if not isinstance(tests,list):tests=[]
            feedback=[]
            if stage!='final':
                for item in tests[:6]:
                    try:
                        args=ast.literal_eval(item['arguments'])
                        if type(args)is not tuple or len(repr(args))>4000:raise ValueError('arguments')
                        obs=replay(request['source'],request['entry'],args,None,seed=SEEDS[0])
                        observation=obs.get('put',{'status':'unresolved'})
                        feedback.append({'arguments':item['arguments'],'put_observation':{k:observation[k]for k in ('status','output','reason')if k in observation}})
                    except (ValueError,TypeError,KeyError,SyntaxError):feedback.append({'status':'malformed'})
            stage_record={'stage':stage,'response_error':record['error'],'feedback':feedback,
                          'final_tests':tests[:6] if stage=='final' else []}
            checkpoint(feedback_path,stage_record);history.append(stage_record)
        final=history[-1]['final_tests']
        arms[arm]={'stages':history,'final_realization':final_audit(request,final,hypotheses)}
    result={'case_id':request['case_id'],'hypotheses':hypotheses,'rejected':rejected,'arms':arms,
            'construction_status':construction,'private_data_used':False,
            'budget':'4logicalcallsperarm;sharedwriterallocatedtodeep/raw/input;18physicalslotspercase'}
    checkpoint(done,result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--requests',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--approval',type=Path)
    p.add_argument('--online',action='store_true');a=p.parse_args()
    if not a.online:raise SystemExit('Explicit --online requires reviewed prospective run protocol; use offline tests for engineering.')
    requests=read_record(a.requests)
    validate_cohort(requests)
    if not a.approval or read_record(a.approval)!={'status':'reviewed_ready','identity':readiness_identity(a.requests)}:
        raise ValueError('reviewed_readiness_identity_required')
    a.out.mkdir(parents=True,exist_ok=True)
    lock=(a.out/'.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    freeze=a.out/'generation_frozen.json'
    if freeze.exists():check_freeze(a.out);print('verified_existing_generation');return
    client=NgrokClient();metadata=client.metadata()
    protocol={'metadata':metadata,'sources':source_identity(),'requests_sha256':hashlib.sha256(a.requests.read_bytes()).hexdigest(),
              'arms':ARMS,'logical_slots_per_arm':4,'physical_slots_per_case':18,'max_transport_attempts_per_slot':2}
    if (a.out/'protocol.json').exists():
        # JSON tuples serialize as arrays.
        if read_record(a.out/'protocol.json')!=json.loads(json.dumps(protocol)):raise ValueError('protocol_drift')
    else:write_new(a.out/'protocol.json',protocol)
    for request in requests:
        cid=str(request['case_id'])
        if not cid.replace('_','').replace('-','').isalnum():raise ValueError('case_id')
        generate_case(client,request,a.out/cid)
    write_new(freeze,{str(f.relative_to(a.out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(a.out.rglob('*.json'))})
    print('generation_frozen_for_independent_scoring')


if __name__=='__main__':main()
