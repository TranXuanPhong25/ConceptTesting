"""Prospective saved-execution diagnostic: no model-bound concepts or new PUT calls."""
import argparse
import ast
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
from . import identify_tools as t
from .d1_client import Client, TransportStop
from .flow_common import digest, immutable, strict_json, write_json
from .paths import CONFIG, DATA_OUT

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = DATA_OUT / 'binding8'
OLD = REPO / 'trickcatcher_linefacts/out/pipelines/v40_concept_agent/humaneval/d1_retry3_20261021'
QUOTA = REPO / 'trickcatcher_linefacts/analysis/astra_concept_design_20261020/quota_guard.py'
TOOLS = ['contrast', 'compare_bindings', 'return_dependencies']


def read(p):
    return strict_json(Path(p).read_text(), max_bytes=16*1024*1024)


def sources():
    return {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.rglob('*')) if p.is_file() and p.suffix != '.pyc'
            and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}


def old_verify():
    for name in ('d1', 'd1_retry_20261021', 'd1_retry2_20261021', OLD.name):
        folder = OLD.with_name(name)
        assert read(folder/'terminal_inventory.json') == {
            str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file() and p.name != 'terminal_inventory.json'}, 'old_inventory_drift'


def deps():
    return {'python': sys.version, 'libraries': {x: importlib.metadata.version(x) for x in ('httpx','jsonschema','jinja2')},
            'quota_sha256': hashlib.sha256(QUOTA.read_bytes()).hexdigest()}


def parent_inventories():
    return {name:hashlib.sha256((OLD.with_name(name)/'terminal_inventory.json').read_bytes()).hexdigest()
            for name in ('d1','d1_retry_20261021','d1_retry2_20261021',OLD.name)}


def prepare():
    old_verify()
    for ep in [f'E{i}' for i in range(1,9)]:
        original = read(OLD/'prepared'/f'{ep}.json')
        observations = original['public']['initial_observations'] + [original['injection']]
        for path in sorted((OLD/'events').glob(ep+'__*.json')):
            observations += read(path)['feedback']
        by_input = {}
        for row in observations:
            if row.get('native_checked') is not True or row.get('domain_filter') != 'accepted':
                continue
            compact = {k: row[k] for k in ('input','execution_status','exception_type','output','output_capture')}
            if compact['input'] in by_input:
                assert by_input[compact['input']] == compact, 'conflicting_observations'
            by_input[compact['input']] = compact
        rows = [dict(by_input[x], id=f'O{i+1}') for i,x in enumerate(sorted(by_input, key=lambda x:(len(x),x)))]
        source = original['public']['code']
        function = ast.parse(source).body[0]
        immutable(ROOT/'prepared'/f'{ep}.json', {'episode':ep,'spec':original['public']['spec'],
                  'code':source,'parameters':[x.arg for x in function.args.args], 'rows':rows,
                  'pool_origin':'ALL native-checked shared+all-arm query/final observations in frozen v40 retry3; no gold filtering'})
    immutable(ROOT/'freeze.json', {'sources':sources(),'dependencies':deps(),
              'parent_inventories':parent_inventories(),
              'old_terminal_inventory_sha256':hashlib.sha256((OLD/'terminal_inventory.json').read_bytes()).hexdigest(),
              'prepared':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'prepared').glob('*.json'))}})


def verify():
    frozen=read(ROOT/'freeze.json')
    assert frozen['sources']==sources() and frozen['dependencies']==deps(), 'source_or_dependency_drift'
    assert frozen['parent_inventories']==parent_inventories(), 'frozen_parent_inventory_drift'
    assert frozen['prepared']=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'prepared').glob('*.json'))}, 'pool_drift'
    old_verify()


def schema(initial):
    binding={'type':'object','additionalProperties':False,'required':['id','concept','relation','arguments','spec_quote'],
             'properties':{'id':{'type':'string','minLength':1,'maxLength':16},'concept':{'enum':t.CONCEPTS},
                           'relation':{'enum':list(t.RELATIONS)},'arguments':{'type':'array','maxItems':2,'items':{'type':'string','maxLength':30}},
                           'spec_quote':{'type':'string','maxLength':300}}}
    props = {'bindings':{'type':'array','maxItems':3,'items':binding},
             'tools':{'type':'array','uniqueItems':True,'maxItems':3,'items':{'enum':TOOLS}}} if initial else {
                 'selected':{'type':'array','uniqueItems':True,'maxItems':3,'items':{'type':'string','maxLength':16}},
                 'implementation_judgment':{'enum':['observed_mismatch','no_observed_mismatch','unknown']},
                 'reason':{'type':'string','maxLength':1000},'evidence':{'type':'array','maxItems':8,'items':{'type':'string','maxLength':30}}}
    return {'type':'object','additionalProperties':False,'required':list(props),'properties':props}


def decode(response, initial):
    assert response['finish_reason']=='stop', 'incomplete_response'
    text=response['text'].strip()
    if text.startswith('```json\n') and text.endswith('\n```') and text.count('```')==2:
        text=text[8:-4]
    value=strict_json(text)
    Draft202012Validator(schema(initial)).validate(value)
    if initial:
        ids=[x['id'] for x in value['bindings']]
        assert len(ids)==len(set(ids)), 'duplicate_binding_id'
    return value


def quota():
    done=subprocess.run([sys.executable,str(QUOTA),'check'],capture_output=True,text=True,timeout=30,check=True)
    snapshot=strict_json(done.stdout);write_json(ROOT/'quota_latest.json',snapshot)
    if snapshot['should_stop']:
        raise TransportStop('quota_at_or_below15')


def complete(client, slot, packet, initial, allowed_ids=None, evidence_ids=None):
    verify();quota()
    if not (ROOT/'transport/calls'/slot/'attempt.json').exists() and len(list((ROOT/'transport/calls').glob('*/attempt.json'))) >=24:
        raise TransportStop('diagnostic24call_cap')
    messages=[{'role':'system','content':'Return exactly one JSON object. No external tools. Bind concepts from spec; observed behavior is not normative truth.'},
              {'role':'user','content':json.dumps(packet,ensure_ascii=False)}]
    immutable(ROOT/'requests'/f'{slot}.json',messages)
    response=client.complete(slot,messages)
    artifact={'raw':response}
    try:
        value=decode(response,initial)
        if not initial:
            if set(value['selected'])-set(allowed_ids):
                raise ValueError('undefined_selected_binding')
            if set(value['evidence'])-set(evidence_ids):
                raise ValueError('undefined_evidence_id')
        artifact.update(state='valid',parsed=value)
    except Exception as exc:
        value=None;artifact.update(state='invalid',error_type=type(exc).__name__)
    immutable(ROOT/'artifacts'/f'{slot}.json',artifact)
    print(slot,artifact['state'],flush=True)
    return value


def run():
    verify()
    approval=read(ROOT/'approval.json')
    assert approval['passed'] and approval['sources']==sources() and approval['freeze_hash']==digest(read(ROOT/'freeze.json')), 'independent_audit_required'
    state={'state':'running','model':CONFIG['model'],'pid':os.getpid()};write_json(ROOT/'status.json',state)
    client=None
    try:
        quota();client=Client(ROOT/'transport')
        for i in (3,6,2,8,4,1,5,7):
            row=read(ROOT/'prepared'/f'E{i}.json')
            packet={'instruction':'Propose up to3 fallible spec bindings from GLOBAL vocabulary; quote exact spec. Choose any of3 tools. Unknown binding is allowed. No human per-task binding is given.',
                    'spec':row['spec'],'code':row['code'],'parameters':row['parameters'],
                    'concepts':t.CONCEPTS,'relations':t.RELATIONS,'available_tools':TOOLS,'reply_schema':schema(True)}
            proposal=complete(client,f'E{i}__initial',packet,True)
            if proposal is None:
                immutable(ROOT/'blocked'/f'E{i}.json',{'final_raw':'initial_invalid','final_tool':'initial_invalid'})
                continue
            feedback=t.tools(proposal['bindings'],row['rows'],row['parameters'],row['code'],proposal['tools'])
            immutable(ROOT/'tool_results'/f'E{i}.json',feedback)
            for arm in (('raw','tool') if i%2 else ('tool','raw')):
                final_packet={'instruction':'Choose which candidate bindings are justified by SPEC, not agreement with code. Empty selected means normative unknown. Judge observed code mismatch separately; observations are finite. Do not invent missing spec rules. Evidence IDs: original_spec, source_return, and observation O IDs.',
                              'spec':row['spec'],'code':row['code'],'parameters':row['parameters'],
                              'relations':t.RELATIONS,'initial_proposal':proposal,'observations':row['rows'],
                              'tool_feedback':feedback if arm=='tool' else None,'reply_schema':schema(False)}
                answer=complete(client,f'E{i}__final_{arm}',final_packet,False,
                                allowed_ids=[x['id'] for x in proposal['bindings']],
                                evidence_ids=['original_spec','source_return']+[x['id'] for x in row['rows']])
                if answer is not None:
                    invalid=set(answer['selected'])-{x['id'] for x in proposal['bindings']}
                    immutable(ROOT/'selection_checks'/f'E{i}__{arm}.json',{'unknown_selected_ids':sorted(invalid)})
        immutable(ROOT/'generation_frozen.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for name in ('prepared','requests','artifacts','blocked','tool_results','selection_checks','transport')
                  for p in sorted((ROOT/name).rglob('*')) if p.is_file()})
        state['state']='complete'
    except Exception as exc:
        state.update(state='stopped',error_type=type(exc).__name__,reason=str(exc) if isinstance(exc,TransportStop) else 'controller_failure')
    finally:
        if client:client.close()
        write_json(ROOT/'status.json',state)
        print(json.dumps(state),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','verify','run']);args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.command=='run' and (ROOT/'status.json').exists():
            prior=read(ROOT/'status.json')
            if prior.get('state') != 'stopped' or prior.get('reason') != 'quota_at_or_below15':
                raise SystemExit('already_consumed_no_automatic_retry')
        {'prepare':prepare,'verify':verify,'run':run}[args.command]()
