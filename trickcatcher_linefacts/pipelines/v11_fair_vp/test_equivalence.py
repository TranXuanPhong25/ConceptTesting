"""CPU equivalence against v11_fair, with frozen flags on; never writes the reference copy.

Check a rebuilds both HumanEval bundles in this copy's output. Check b recomputes
all seven arms' first request hashes and replays tasks 0/4/16 against the same
historical cache in both copies. New strict requests may miss: equal misses are
reported as a replay limit, never filled with invented responses.
"""
import argparse
import ast
import contextlib
import json
import socket
from pathlib import Path
from unittest.mock import patch
from ..v11_fair import paths as reference_paths, run as reference_run
from . import paths, run, v4_runtime
from .offline_client import OfflineClient, CacheMiss, request


def normalized(row):
    # Timing and source-derived provenance differ by construction.
    if isinstance(row, dict):
        return {k: normalized(v) for k, v in row.items()
                if k not in ('seconds', 'run_id', 'elapsed', 'wall_seconds')}
    if isinstance(row, list): return [normalized(v) for v in row]
    return row


def first_keys(package, tasks, layout, python, timeout):
    import importlib
    rv = importlib.import_module(package + '.run_v4')
    gp = importlib.import_module(package + '.gen_prompts')
    pr = importlib.import_module(package + '.prompts')
    vp = importlib.import_module(package + '.v4_prompts')
    gi = importlib.import_module(package + '.gen_inputs')
    keys = {}
    for t in tasks:
        candidates = [dict(input_repr=repr(tuple(ast.literal_eval(x['input_repr']))))
                      for x in gi.witness_candidates(t)]
        directory=layout.root/'first_requests'/str(t['task'])
        saved=directory/'classify_result.json'
        if saved.exists():
            # Resume only observations produced by this equivalence check, never historical outputs.
            flagged=json.loads(saved.read_text())
        else:
            native=rv.v4_runtime.isolated
            def bounded(*args,**kwargs):
                kwargs['timeout']=timeout
                return native(*args,**kwargs)
            with patch.object(rv.v4_runtime,'isolated',side_effect=bounded):
                flagged=rv.classify(t,directory,python,candidates=candidates)
        if flagged['summary'].get('classification_error'):
            print(package,t['task'],flagged['summary']['classification_error'],flush=True)

        selected = [r for r in flagged['records'] if r['valid']][:3]
        for sample in range(3):
            for arm in vp.ARMS:
                alias = {'plain-hybrid':'plain', 'concept-hybrid':'concept'}.get(arm, arm)
                if alias in ('plain', 'concept', 'placebo-hybrid'):
                    kind = 'placebo' if alias == 'placebo-hybrid' else alias
                    messages = gp.messages(*pr.build(kind, t)); stage = 0
                elif alias == 'gen-plain':
                    messages = gp.generator_messages(alias,t); stage = 1
                else:
                    messages = gp.oracle_messages(t,selected); stage = 2
                keys[f"{t['task']}/{arm}/{sample}"] = request(messages,vp.seed(t['task'],alias,sample,stage))[0]
    return keys


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checks',default='a,b'); ap.add_argument('--workers',type=int,default=1)
    ap.add_argument('--classification-timeout',type=int,default=45,help='CPU check only, not production timeout')
    a=ap.parse_args()
    paths.set_dataset('humaneval')
    layout=run.Layout(root=paths.DATA_OUT/'equivalence')
    layout.root.mkdir(parents=True,exist_ok=True)
    python=v4_runtime.interpreter()
    original=paths.REPO/'trickcatcher_linefacts/out'
    for name in ('precond_qwen7b_v4','strategy_qwen7b_v4c','facts_v6','spec_facts_v7'):
        run.seed_reuse(layout,original/name)
    summary={'flags_equal': all(paths.CONFIG[k] is True and paths.CONFIG[k]==reference_paths.CONFIG[k]
                              for k in paths.FAIR_FLAGS)}
    with patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')), \
         patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
        if 'a' in a.checks.split(','):
            actual=run.bundle(layout)
            ref_layout=run.Layout(root=paths.DATA_OUT/'equivalence_reference_bundle')
            for name in ('precond_qwen7b_v4','strategy_qwen7b_v4c','facts_v6','spec_facts_v7'):
                run.seed_reuse(ref_layout,original/name)
            expected=reference_run.bundle(ref_layout)
            summary['a']={'tasks':len(actual[1]['tasks']), 'all_equal':actual[0]==expected[0],
                          'hybrid_equal':actual[1]==expected[1]}
            print('a:',summary['a'],flush=True)
        if 'b' in a.checks.split(','):
            tasks=json.loads(layout.hybrid.read_text())['tasks']
            old=first_keys('trickcatcher_linefacts.pipelines.v11_fair',tasks,
                           run.Layout(root=paths.DATA_OUT/'first_reference'),python,a.classification_timeout)
            new=first_keys(__package__,tasks,layout,python,a.classification_timeout)
            summary['b']={'first_requests':len(new),'first_request_keys_equal':old==new,
                          'classification_timeout':a.classification_timeout}
            from ..v11_fair import run_v4 as ref_rv
            from . import run_v4 as new_rv
            replays=[]
            for rv,name in ((ref_rv,'reference'),(new_rv,'copy')):
                destination=layout.root/('replay_'+name)
                if destination.exists():
                    import shutil
                    shutil.rmtree(destination)
                client=OfflineClient(original/'gen2_qwen7b_v7hyb_v4_r2/cache')
                error=None
                with patch.object(reference_paths,'DATA_OUT',paths.DATA_OUT):
                    try: rv.run([t for t in tasks if t['task'] in (0,4,16)],destination,
                                python,k=1,workers=1,client=client)
                    except CacheMiss as exc: error=str(exc)
                rows=[json.loads(p.read_text()) for p in sorted((destination/'artifacts').glob('*/*/*/result.json'))]
                replays.append(dict(hits=client.hits,misses=client.misses,error=error,rows=normalized(rows)))
            summary['b'].update(replay_equal=replays[0]==replays[1],completed_rows=len(replays[1]['rows']),
                                cache_hits=len(replays[1]['hits']),cache_misses=replays[1]['misses'],
                                replay_limit=replays[1]['error'])
            print('b:',summary['b'],flush=True)
    (layout.root/'equivalence.json').write_text(json.dumps(summary,indent=2)+'\n')
    ok=summary['flags_equal'] and all(summary.get('a',{}).get(k,True) for k in ('all_equal','hybrid_equal'))
    ok &= all(summary.get('b',{}).get(k,True) for k in ('first_request_keys_equal','replay_equal'))
    raise SystemExit(0 if ok else 1)

if __name__=='__main__': main()
