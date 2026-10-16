"""Bounded literal execution interface; unsupported operation claims remain unknown."""
import json
from pathlib import Path
from .chain_inputs import parse_arguments,literal_for_transport
from .chain import sha
from .gen_inputs import sandbox
from .llm_client import atomic_json
from .paths import CONFIG
from .chain_protocol import fingerprint
HERE=Path(__file__).resolve().parent


def observe(task,requests,ordinary,traced):
    keys=('status','exception_type','exception_module','output_capture','output_signature','input_before','input_after','output_aliases')
    checked=ordinary.get('status') in ('ok','exception') and all(ordinary.get(k)==traced.get(k) for k in keys) and ordinary.get('input_before') is not None and ordinary.get('input_after') is not None and traced.get('trace_complete',False)
    if ordinary.get('status')=='ok' and (ordinary.get('output_capture')!='literal' or ordinary.get('output_signature') is None):checked=False
    result={k:ordinary.get(k) for k in ('status','exception_type','exception_module','output_capture','output_repr')};result['native_checked']=checked
    result['worker_details']={mode:{k:r[k] for k in ('status','reason','validity_checks','validity_provenance','trace_complete') if k in r} for mode,r in [('ordinary',ordinary),('traced',traced)]}
    if not checked:result['verification_reason']='unresolved_worker_or_missing_or_mismatched_observable_signature'
    nodes={n['id']:n for n in task['nodes']};statements={}
    for n in task['nodes']:
        if n['is_statement']:statements.setdefault(n['span'][0],[]).append(n['id'])
    observations=[]
    for request in requests:
        uid=request['source_id'];kind=request['kind'];node=nodes.get(uid)
        row=dict(source_id=uid,kind=kind,status='unknown',events=[],omitted_events=0)
        if not checked:row['reason']='execution_not_verified'
        elif kind=='function_output' and uid==task['entry_source_id']:row.update(status='observed',reason='whole_function_output_not_local_effect')
        elif kind=='statement_reach' and node and node['is_statement'] and node['execution_scope']=='function_body' and len(statements.get(node['span'][0],[]))==1:
            values=[r for r in traced['events'] if r['event']=='line' and r['line']==node['span'][0]]
            row.update(status='observed' if values else 'not_observed',events=values if len(values)<=2 else [values[0],values[-1]],omitted_events=max(0,len(values)-2),reason='statement_line_reach_in_completed_trace')
        else:row['reason']='unsupported_exact_observation'
        observations.append(row)
    result['observations']=observations;return result


def execute(task,input_repr,requests,directory):
    args=parse_arguments(input_repr,task['arity']);literal=literal_for_transport(args)
    key=sha(dict(source_hash=task['source_hash'],valid_code=task.get('valid_code'),input_repr=literal,adapter_protocol=fingerprint(),limits=CONFIG['chain']));root=Path(directory)/key;root.mkdir(parents=True,exist_ok=True)
    results={}
    for mode in ('ordinary','traced'):
        job=dict(source=task['source_original'],entry=task['entry'],input_repr=literal,mode=mode,valid_code=task.get('valid_code'))
        jp=root/(mode+'_job.json');op=root/(mode+'_result.json')
        if jp.exists() and json.loads(jp.read_text())!=job:raise ValueError('execution_cache_drift')
        if not jp.exists():atomic_json(jp,job)
        if op.exists():result=json.loads(op.read_text())
        else:
            try:result=sandbox(CONFIG['V4_PYTHON'],HERE/'execution_worker.py',jp,op,8)
            except RuntimeError as exc:result=dict(status='unresolved',reason='isolated_worker_failed',events=[]);atomic_json(op,result)
        results[mode]=result
    return observe(task,requests,results['ordinary'],results['traced'])
