"""Public-only task preparation. Evaluation payloads are loaded only by scoring."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from .paths import HERE, REPO, CONFIG
from . import provenance, preconditions, v4_runtime, spec_facts, facts
from .combined_facts import merge
from .ft_tools import public_inputs, build as fault_build

HE_ROOT=REPO/'trickcatcher_linefacts/pipelines/v11_fair/out/humaneval'
VP_ROOT=REPO/'trickcatcher_linefacts/out/heldout_vibepass_real/he'


def cohort(name):
    if name=='humaneval':
        rows=provenance.read(HE_ROOT/'tasks_hybrid.json')['tasks']
        rows=[t for t in rows if t['split']=='dev']
        if len(rows)!=113: raise ValueError('dev_cohort_drift')
        keep=json.loads((HERE/'COHORT.json').read_text())['task_ids']
        rows=[t for t in rows if t['task'] in keep]
        if len(rows)!=28:raise ValueError('quarter_cohort_drift')
        return deepcopy(rows)
    if name!='vibepass_half': raise ValueError('unregistered_dataset')
    keep=json.loads((HERE/'vibepass_half.json').read_text())['tasks']
    public={int(r['task_id'].split('/')[1]):r for r in map(json.loads,provenance.verify_file(VP_ROOT/'humaneval_mbpp.jsonl').read_text().splitlines())}
    rows=[]
    for n in keep:
        h=public[n]; src=provenance.verify_file(VP_ROOT/f'PUTs/HumanEval_{n}/put0.py').read_text()
        task=dict(task=n,entry=h['entry_point'],put=src,base=h['test'],split='heldout',facts_version='v4',doc_fail=False,
                  concept_meta=[],placebo_meta=[],concept_facts=[],placebo_facts=[],tool_inputs=[])
        if 'exec(' in task['base'] or 'is_valid_test' in task['base']:
            raise ValueError('private_evaluator_in_public_base')
        # No model mining or hidden contract. A public-only type strategy feeds
        # the unchanged v4 Hypothesis/fuzz/coverage machinery.
        seeds=public_inputs(task)
        valid='def valid(*args):\n    return True\n'
        strategies=[]
        def strategy(v):
            if type(v) is bool:return 'st.booleans()'
            if type(v) is int:return 'st.integers(min_value=-10, max_value=200)'
            if type(v) is str:return 'st.text(alphabet='+repr(''.join(sorted(set(v))) or 'ab01')+', max_size=24)'
            if type(v) is list:return 'st.lists('+strategy(v[0] if v else 0)+', max_size=12)'
            if type(v) is tuple:return 'st.tuples('+', '.join(strategy(x) for x in v)+')'
            return 'st.just('+repr(v)+')'
        if not seeds: raise ValueError('public_seeds_required')
        for v in seeds[0]: strategies.append(strategy(v))
        code='def strategy():\n    return st.one_of(st.sampled_from('+repr(seeds)+'), st.tuples('+', '.join(strategies)+'))\n'
        task.update(mined_valid_src=valid,valid_sha256=preconditions.sha(valid),strategy_src=code,
                    strategy_sha256=preconditions.sha(code),strategy_fallback=True,
                    mining_summary=dict(origin='deterministic_public_examples',spec_validity='unknown'))
        rows.append(task)
    if len(rows)!=33: raise ValueError('vp_cohort_drift')
    return rows


def prepare_one(name, task, directory, python, *, fault_enabled=True):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    n=task['task']
    if name=='humaneval':
        fr=provenance.read(HE_ROOT/f'facts/{n}.json')
        full=fr['facts'][:]
        # v7 adds SPEC only when no ranked code facts exist.
        if task.get('spec_facts') or not task['concept_meta']:
            full+=task['concept_meta']
    else:
        public={int(r['task_id'].split('/')[1]):r for r in map(json.loads,(VP_ROOT/'humaneval_mbpp.jsonl').read_text().splitlines())}
        manifest=json.loads((HERE/'INPUTS.json').read_text())
        fr=provenance.read(REPO/manifest['v7vp_public_facts_root']/f'{n}.json')
        v4_runtime.immutable(directory/'v7_public_facts.json',fr)
        for f in fr['facts']+fr['placebo3']:
            if f['kind']=='MUTANT' and 'mutant_src' not in f:
                src,line,before,after,_=facts.make_mutant(task['put'],f['k'],source=True)
                if line!=f['line'] or facts.t_mutant(line,before,after,f['family'],f in fr['placebo3'])!=f['text']:
                    raise ValueError('legacy_mutant_reconstruction_drift')
                f['mutant_src']=src
        full=fr['facts'][:]; top=[full[i] for i in fr['top3']]
        plc=fr['placebo3']
        if not top:
            spec,_,params=preconditions.specification(task)
            job=dict(entry=task['entry'],base=public_inputs(task),params=[a.arg for a in params.posonlyargs+params.args],valid_src=task['mined_valid_src'])
            from .llm_client import atomic_json
            atomic_json(directory/'spec.job.json',job)
            # Executes only the public validator inside the isolated worker.
            spec_res=v4_runtime.isolated('spec',job,directory/'spec',python)
            top=spec_res['facts'][:3];plc=spec_res['placebo'][:3];full+=spec_res['facts']
        task=dict(task,concept_meta=top,concept_facts=[f['text'] for f in top],placebo_meta=plc,
                  placebo_facts=[f['text'] for f in plc],tool_inputs=[f['witness_call'] for f in top if f.get('witness_call')])
    if not fault_enabled:
        return dict(baseline=task,combined=merge(task,full,[],[],enabled=False))
    historical=False
    if name=='vibepass_half':
        ft=fault_build(task,directory/'ft',python,historical=True);historical=True
    else: ft=fault_build(task,directory/'ft',python)
    combined=merge(task,full,ft['facts'],ft['template_inputs'])
    return dict(baseline=task,combined=combined,tool_audit=dict(historical=historical,mutants=ft['mutants'],survivors=ft['survivors']))
