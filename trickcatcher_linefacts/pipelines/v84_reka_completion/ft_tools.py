"""CPU v31 tool construction and SHA-checked historical phase reuse, no model/scorer."""
import ast
import json
from pathlib import Path
from . import ft_concepts, gen_inputs, v4_runtime
from .paths import CONFIG, HERE, REPO
from .combined_facts import fault_facts
from .llm_client import atomic_json


def public_inputs(task):
    rows=[]
    for node in ast.walk(ast.parse(task['base'])):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('candidate',task['entry']) and not node.keywords:
            try: args=tuple(ast.literal_eval(a) for a in node.args)
            except (ValueError,SyntaxError): continue
            if args not in rows: rows.append(args)
    return rows[:20]


def execute(directory,sources,entry,inputs,python):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    job=dict(sources=sources,entry=entry,inputs=[repr(x) for x in inputs],order=list(sources),per_call_timeout=1,max_timeouts=2)
    v4_runtime.immutable(directory/'job.json',job)
    if not (directory/'result.json').exists():
        gen_inputs.sandbox(python,HERE/'ft_worker.py',directory/'job.json',directory/'result.json',600)
    return json.loads((directory/'result.json').read_text())


def reused(task):
    from .provenance import verify_file
    manifest=json.loads((HERE/'INPUTS.json').read_text())
    root=REPO/manifest['v31_root']; cid=str(task['task'])
    rel=f'cases/{cid}/tool'
    for suffix in ('/phase1/job.json','/phase1/result.json','/phase2/job.json','/phase2/result.json'):
        verify_file(root/(rel+suffix))
    verify_file(root/f'cases/{cid}/tool.json')
    other=REPO/manifest['v34_root']
    for suffix in ('/phase1/job.json','/phase1/result.json','/phase2/job.json','/phase2/result.json'):
        verify_file(other/(rel+suffix))
        if (root/(rel+suffix)).read_bytes()!=(other/(rel+suffix)).read_bytes():
            raise ValueError('historical_v31_v34_phase_disagreement')
    verify_file(other/'generation_frozen.json')
    frozen=json.loads((root/'generation_frozen.json').read_text())
    from .provenance import sha
    if frozen.get(f'cases/{cid}/tool.json')!=sha(root/f'cases/{cid}/tool.json'):
        raise ValueError('historical_tool_not_frozen')
    verify_file(root/'generation_frozen.json')
    # Compare all public sources/inputs before trusting any phase output.
    j1=json.loads((root/rel/'phase1/job.json').read_text())
    j2=json.loads((root/rel/'phase2/job.json').read_text())
    if j1['sources']['put']!=task['put'] or j1['inputs']!=[repr(a) for a in public_inputs(task)] or j2['sources']['put']!=task['put']:
        raise ValueError('historical_tool_public_context_mismatch')
    p1=json.loads((root/rel/'phase1/result.json').read_text()); p2=json.loads((root/rel/'phase2/result.json').read_text())
    if any(x.get('_error') for x in (p1,p2)):
        raise ValueError('historical_phase_error')
    return j1,j2,p1,p2


def build(task,directory,python,*,historical=False):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    if historical:
        j1,j2,p1,p2=reused(task)
        # Re-enumeration recovers the exact mutmut operator metadata; sources must
        # equal the pinned historical enumeration before reuse is allowed.
    from .v4_tools import enumerate_mutants
    mutants=enumerate_mutants(task['put'],directory)
    lines=task['put'].splitlines()
    for m in mutants: m['type']=ft_concepts.fault_type(m,lines[m['line']-1])
    sources={'put':task['put'],**{f"m{m['k']}":m['mutant_src'] for m in mutants}}
    if historical:
        if sources!=j1['sources']: raise ValueError('historical_mutation_enumeration_drift')
    else:
        p1=execute(directory/'phase1',sources,task['entry'],public_inputs(task),python)
    survivors=[]
    for m in mutants:
        pairs=[(a,b) for a,b in zip(p1['put'],p1[f"m{m['k']}"]) if a[0] in ('ok','exception')]
        if pairs and all(a==b for a,b in pairs):
            survivors.append(m)
    survivors=survivors[:200]
    consts=sorted({c for m in survivors if m['type']=='BOUNDARY' for c in ft_concepts.site_constants(task['put'],m['line'])},key=lambda c:(abs(c),c))[:8] or [0,1]
    from ..v31_faulttemplate.chain_inputs import literal_for_transport
    candidates=[]
    for c in ft_concepts.templates(public_inputs(task),{'BOUNDARY':consts}):
        try: literal_for_transport(c['args'])
        except (ValueError,TypeError,RecursionError): continue
        candidates.append(c)
    selected_sources={'put':task['put'],**{f"m{m['k']}":m['mutant_src'] for m in survivors}}
    if historical:
        if selected_sources!=j2['sources'] or [repr(c['args']) for c in candidates]!=j2['inputs']:
            raise ValueError('historical_phase2_request_drift')
    else:
        p2=execute(directory/'phase2',selected_sources,task['entry'],[c['args'] for c in candidates],python)
    mout={m['k']:p2[f"m{m['k']}"] for m in survivors}
    groups=ft_concepts.rank(survivors,candidates,p2['put'],mout,lines)
    facts=fault_facts(groups,candidates,p2['put'],mout,task['entry'])
    record=dict(facts=facts,template_inputs=[c['args'] for c in candidates],historical=historical,
                mutants=len(mutants),survivors=len(survivors))
    v4_runtime.immutable(directory/'fault_bundle.json',record)
    return record
