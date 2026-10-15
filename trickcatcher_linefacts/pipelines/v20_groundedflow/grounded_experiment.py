"""CPU-only fixture gate and all20 inventory. No canonical/reference/model API imports."""
import argparse
import hashlib
import json
from pathlib import Path
from . import grounded as g,grounded_fixtures as fixtures,paths,gen_inputs,v4_runtime
from .llm_client import atomic_json
HERE=Path(__file__).resolve().parent
ROOT=paths.DATA_OUT/'grounded_cpu'
PARENT=HERE.parent/'v18_modelselect/out/humaneval/behavior_smoke'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def freeze():
    protocol=dict(sources={p.name:digest(p) for p in sorted(HERE.glob('*.py'))},config=digest(HERE/'config.json'),prereg=digest(HERE/'PREREG.md'),scope='CPU multiplicity; no D_IO, model API or trusted inferred specs')
    v4_runtime.immutable(ROOT/'protocol.json',protocol)
    return protocol


def isolated(source,entry,args,requirement,directory,valid=None):
    g.checked_input(args)  # Before serialization, not after alias topology is lost.
    directory.mkdir(parents=True,exist_ok=True)
    jp=directory/'job.json';op=directory/'result.json'
    job=dict(source=source,entry=entry,input_repr=repr(args),requirement=requirement)
    if valid:job['mined_valid_src']=valid
    v4_runtime.immutable(jp,job)
    if op.exists():return json.loads(op.read_text())
    return gen_inputs.sandbox(v4_runtime.interpreter(),HERE/'grounded_worker.py',jp,op,15)


def run_fixtures():
    freeze();results=[]
    for case in fixtures.cases():
        r=isolated(case['source'],'f',case['args'],case['requirement'],ROOT/'fixtures'/case['id'])
        errors={k:dict(expected=v,actual=r.get(k)) for k,v in case['expect'].items() if r.get(k)!=v}
        events=r.get('observed',{}).get('events',[])
        if case['id']=='untaken_operation' and events:errors['activation']='untaken set has events'
        if case['id']=='exception_uncommitted' and any(x['phase']=='committed' for x in events):errors['exception']='uncommitted operation recorded committed'
        if case['id'] in ('same_line_sets','nested_sets') and len({x['node_id'] for x in events})!=2:errors['node_ids']='two operations not distinguished'
        results.append(dict(id=case['id'],passed=not errors,errors=errors,complete_evidence=r.get('complete_evidence'),review_status=r.get('requirement_review_status')))
    gate=dict(cases=len(results),passed=sum(r['passed'] for r in results),gate_passed=all(r['passed'] for r in results),rows=results,scope='known authored design fixtures; finite implementation checks, not benchmark gain')
    v4_runtime.immutable(ROOT/'fixture_gate.json',gate);print(json.dumps(gate,indent=2));return gate


def proposal(t,candidate):
    if not candidate.get('pool'):return None,'no_parent_candidate'
    model=next(r['model'] for r in candidate['pool'] if r['id']==candidate['rule_first'])
    if model['template']!='FILTER':return None,'outside_multiplicity_candidate_family'
    p=model['params']
    if p['index']!='all' or p['predicate'] not in ('all','length_even','positive') or p['component'] is not None:return None,'candidate_relation_unsupported'
    text=t['put'];import ast
    spec=ast.get_docstring(ast.parse(text).body[0],clean=False) or ''
    if not spec:return None,'missing_quote'
    # Entire original docstring is a provenance quote, NOT semantic entailment/review.
    return dict(mode='unique' if p['distinct'] else 'preserve',eligibility=p['predicate'],element_type='str' if p['predicate']=='length_even' else 'int',argument=p['argument'],review_status='unreviewed',provenance='frozen_v18_rule_first_not_semantic_proof',spec=spec,quote=spec,span=[0,len(spec)]),None


def constructors(r):
    atoms=['a','aa','b','bb'] if r['element_type']=='str' else [-1,0,1,2]
    yield ([],)
    for x in atoms:yield ([x],);yield ([x,x],)
    for x,y in zip(atoms,atoms[1:]):yield ([x,y,x],)


def inventory():
    freeze();gate=json.loads((ROOT/'fixture_gate.json').read_text())
    if not gate['gate_passed']:raise RuntimeError('fixture gate failed; inventory stopped')
    src=HERE.parent/'v11_fair/out/humaneval/tasks_hybrid.json';data=json.loads(src.read_text())['tasks'];byid={t['task']:t for t in data}
    rows=[];parent_provenance={}
    for tid in paths.CONFIG['behavior']['task_ids']:
        t=byid[tid];ir=g.analyze(t['put'],t['entry']);row=dict(task=tid,known_design=tid in (149,110,152),supported=ir['supported'],operations=len(ir.get('operations',[])),reasons=ir['reasons'],complete_evidence_inputs=0,grounded_reviewed=0,worker_calls=0,native_executions_upper_bound=0,confirmed_bug=None)
        if ir['supported']:
            cp=PARENT/'selection_pilot/prepared'/str(tid)/'candidates_result.json';candidate=json.loads(cp.read_text());parent_provenance[str(tid)]=digest(cp)
            snapshot=json.loads((PARENT/'selection_pilot/selection_frozen.json').read_text())
            if digest(cp)!=snapshot['tasks'][str(tid)]['candidates']:raise RuntimeError('parent candidate snapshot changed')
            req,reason=proposal(t,candidate);row['requirement_status']='unreviewed' if req else 'unavailable'
            if reason:row['reasons'].append(reason)
            if req:
                for i,args in enumerate(constructors(req)):
                    if i>=paths.CONFIG['grounded_flow']['max_inputs']:break
                    if req['argument']!=0 or len(ir['parameters'])!=1:
                        row['reasons'].append('constructor_arity');break
                    r=isolated(t['put'],t['entry'],args,req,ROOT/'inventory'/str(tid)/str(i),t['mined_valid_src'])
                    row['worker_calls']+=1;row['native_executions_upper_bound']+=2
                    row['complete_evidence_inputs']+=bool(r.get('complete_evidence'));row['grounded_reviewed']+=bool(r.get('grounded_reviewed'))
        rows.append(row)
    report=dict(scope='all20 known dev; CPU source/candidate inventory only; no independent spec or bug confirmation',tasks=len(rows),supported=sum(r['supported'] for r in rows),rows=rows,task_bundle_sha256=digest(src),parent_candidate_sha256=parent_provenance,native_executions_upper_bound=sum(r['native_executions_upper_bound'] for r in rows),model_requests=0,D_IO=None)
    v4_runtime.immutable(ROOT/'inventory.json',report);print(json.dumps(report,indent=2));return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['fixtures','inventory']);a=p.parse_args()
    if a.stage=='fixtures':run_fixtures()
    else:inventory()


if __name__=='__main__':main()
