"""CPU-only, read-only historical inputs; every output below out/pipelines/VERSION/."""
from __future__ import annotations
import argparse
import ast
import contextlib
import io
import json
import shutil
import socket
from pathlib import Path
from unittest.mock import patch
from . import paths
from .offline_client import OfflineClient, CacheMiss
from .run import Layout, bundle, seed_reuse


def load_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def differences(a, b, path=''):
    if type(a) != type(b): return [path + ':type']
    if isinstance(a, dict):
        out = [path + '/' + k + ':missing-key' for k in a.keys() ^ b.keys()]
        for k in a.keys() & b.keys(): out.extend(differences(a[k], b[k], path + '/' + k))
        return out
    if isinstance(a, list):
        out = [path + ':length'] if len(a) != len(b) else []
        for i, (x, y) in enumerate(zip(a, b)): out.extend(differences(x, y, path + '/' + str(i)))
        return out
    return [] if a == b else [path]


def check_a(layout, original):
    standard, hybrid = bundle(layout)
    results = {}
    for name, actual in [('tasks_v7_all.json', standard), ('tasks_v7hyb_v4.json', hybrid)]:
        expected = json.loads((original / name).read_text())
        diff = differences(actual, expected)
        results[name] = dict(tasks=len(actual['tasks']), equal=not diff, differences=diff)
    print('a:', json.dumps({k: {p: v for p, v in r.items() if p != 'differences'} for k, r in results.items()}), flush=True)
    return results


def check_b(layout, record, python):
    from . import gen_inputs, gen_prompts, prompts, run_v4, v4_prompts
    tasks = json.loads(layout.hybrid.read_text())['tasks']
    rows = {(r['task'], r['arm'], r['sample']): r for r in load_rows(record / 'gen.jsonl')}
    k = paths.CONFIG['K']
    client = OfflineClient(record / 'cache')
    checked = 0; wrong_keys = []; witness_diff = []; recorded_failures = []
    for t in tasks:
        # Recompute toolinput's first selection with the copied classifier, rather than adopting recorded selections.
        candidates = [dict(input_repr=repr(tuple(ast.literal_eval(x['input_repr'])))) for x in gen_inputs.witness_candidates(t)]
        flagged = run_v4.classify(t, layout.root / 'first_requests' / str(t['task']), python, candidates=candidates)
        selected = [r for r in flagged['records'] if r['valid']][:3]
        for sample in range(k):
            oracle_selected = selected
            recorded = rows[t['task'], 'toolinput', sample]
            if selected != recorded['selected_inputs']:
                witness_diff.append([t['task'], sample])
                error = recorded['stage1_summaries'][0].get('classification_error')
                if error:
                    # A wall-clock sandbox failure is execution state, not prompt logic.
                    # Replay that recorded error through the copy's unchanged fallback.
                    with patch.object(run_v4.v4_runtime, 'isolated', side_effect=RuntimeError(error)):
                        fallback = run_v4.classify(t, layout.root / 'recorded_failure', python, candidates=candidates)
                    assert fallback['summary'] == recorded['stage1_summaries'][0]
                    oracle_selected = [r for r in fallback['records'] if r['valid']][:3]
                    recorded_failures.append(dict(task=t['task'], sample=sample, error=error))
            for arm in v4_prompts.ARMS:
                alias = 'plain' if arm == 'plain-hybrid' else 'concept' if arm == 'concept-hybrid' else arm
                if alias in ('plain', 'concept', 'placebo-hybrid'):
                    kind = 'placebo' if alias == 'placebo-hybrid' else alias
                    messages = gen_prompts.messages(*prompts.build(kind, t)); stage = 0
                elif alias == 'gen-plain':
                    messages = gen_prompts.generator_messages(alias, t); stage = 1
                else:
                    messages = gen_prompts.oracle_messages(t, oracle_selected); stage = 2
                seed = v4_prompts.seed(t['task'], alias, sample, stage)
                try:
                    response = client.chat(messages, seed)
                    expected = rows[t['task'], arm, sample]['calls'][0]['key']
                    if response['key'] != expected: wrong_keys.append([t['task'], arm, sample])
                except CacheMiss: pass
                checked += 1
        if checked % 420 == 0: print(f'b: {checked} first requests checked', flush=True)
    result = dict(tasks=len(tasks), pilot=sum(t['split'] == 'pilot' for t in tasks),
                  dev=sum(t['split'] == 'dev' for t in tasks), arms=len(v4_prompts.ARMS), K=k,
                  logical_first_requests=checked, unique_keys=len(set(client.hits)),
                  hits=len(client.hits), misses=len(client.misses), miss_keys=client.misses,
                  mismatched_record_keys=wrong_keys, fresh_witness_selection_differences=witness_diff,
                  replayed_recorded_worker_failures=recorded_failures)
    print('b first requests:', json.dumps({p:v for p,v in result.items() if not isinstance(v,list)}), flush=True)
    subset = [t for t in tasks if t['task'] in (0, 4, 16)]
    replay_root=layout.root / 'replay_verified'
    if replay_root.exists(): shutil.rmtree(replay_root)
    replay_client = OfflineClient(record / 'cache')
    replay_error = None
    try:
        run_v4.run(subset, layout.root / 'replay_verified', python, k=1, workers=1, client=replay_client)
    except CacheMiss as exc:
        replay_error = str(exc)
    replay = [json.loads(p.read_text()) for p in sorted((layout.root / 'replay_verified/artifacts').glob('*/*/*/result.json'))]
    fields = ['assertions', 'selected_inputs', 'round1_assertions', 'round2_strategy_requests',
              'input_summary', 'stage1_summaries']
    mismatches = []
    for r in replay:
        saved = rows[r['task'], r['arm'], r['sample']]
        for key in fields:
            for diff in differences(r[key], saved[key], key): mismatches.append([r['task'], r['arm'], diff])
    result['end_to_end'] = dict(tasks=[t['task'] for t in subset], samples=1, rows=len(replay),
                                requests=len(replay_client.hits), misses=len(replay_client.misses), miss_keys=replay_client.misses,
                                incomplete_rows=len(subset)*len(v4_prompts.ARMS)-len(replay),
                                error=replay_error, differences=mismatches)
    print('b end-to-end:', json.dumps(result['end_to_end']), flush=True)
    return result


def check_c(layout, record, oracle, python, workers, resume=False):
    from . import evaluate, oracle_b01 as ob
    # Only inputs are copied. Evaluation and oracle execution results are recomputed.
    layout.generation.mkdir(parents=True, exist_ok=True)
    for f in ('tasks.json', 'gen.jsonl', 'manifest.json'): shutil.copyfile(record / f, layout.generation / f)
    if resume and (layout.generation / 'eval.jsonl').exists():
        print('c: resuming from this suite’s recomputed evaluation', flush=True)
    else:
        print('c: recomputing all evaluation rows', flush=True)
        evaluate.evaluate(layout.generation / 'tasks.json', layout.generation / 'gen.jsonl', layout.generation / 'eval.jsonl', python)
    actual, expected = load_rows(layout.generation / 'eval.jsonl'), load_rows(record / 'eval.jsonl')
    diff = differences(actual, expected)
    matching = sum(x == y for x, y in zip(actual, expected))
    result = dict(evaluation=dict(rows=len(actual), reference_rows=len(expected), matching_rows=matching,
                                  different_rows=len(actual)-matching, field_differences=diff))
    print('c evaluation:', len(actual), 'rows;', matching, 'identical;', len(diff), 'field differences', flush=True)
    layout.oracle.mkdir(parents=True, exist_ok=True)
    ob.collect(layout.generation, layout.oracle)
    calls = json.loads((layout.oracle / 'calls.json').read_text())
    expected_calls = json.loads((oracle / 'calls.json').read_text())
    clients = []
    def offline(directory, **kwargs):
        client = OfflineClient(oracle / 'cache', **kwargs); clients.append(client); return client
    # Directly replay every B1/ref/post request from the original cache; nothing is read from a live transport.
    with patch.object(ob, 'Client', offline):
        ob.llm(layout.generation, layout.oracle, workers=workers, stages=('b1', 'ref', 'post'))
        print('c: recomputing oracle workers and cached judges', flush=True)
        with contextlib.redirect_stdout(io.StringIO()):
            ob.score(layout.generation, layout.oracle, workers=workers, use_llm=True)
    report = (layout.oracle / 'report.txt').read_text()
    expected_report = (oracle / 'report.txt').read_text()
    lines, ref_lines = report.splitlines(), expected_report.splitlines()
    changed = [dict(line=i+1, actual=x, expected=y) for i,(x,y) in enumerate(zip(lines,ref_lines)) if x != y]
    result['oracle'] = dict(tasks=len(calls), unique_calls=sum(len(v) for v in calls.values()),
                            collected_calls_equal=calls == expected_calls,
                            cached_requests=sum(len(c.hits) for c in clients),
                            misses=sum(len(c.misses) for c in clients),
                            report_equal=report == expected_report, report_lines=len(lines),
                            reference_report_lines=len(ref_lines), different_lines=changed)
    for stage in ('b1', 'ref', 'post', 'judge'):
        a = json.loads((layout.oracle / f'{stage}_responses.json').read_text())
        b = json.loads((oracle / f'{stage}_responses.json').read_text())
        result['oracle'][stage] = dict(responses=len(a), equal=a == b, differences=differences(a,b))
    actual_exec = {p.stem:json.loads(p.read_text()) for p in (layout.oracle/'exec').glob('*.json') if '.job' not in p.name}
    exec_differences = {}
    for n, actual in actual_exec.items():
        diff = differences(actual,json.loads((oracle/'exec'/f'{n}.json').read_text()))
        if diff: exec_differences[n] = diff
    result['oracle']['execution_tasks'] = len(actual_exec)
    result['oracle']['execution_differences'] = exec_differences
    print('c oracle:', json.dumps({k:v for k,v in result['oracle'].items() if isinstance(v,(int,bool))}), flush=True)
    return result



def check_legacy_report(layout, record, oracle):
    from . import oracle_b01 as ob
    tasks,rows=ob.load_run(record)
    calls=json.loads((oracle/'calls.json').read_text())
    ex={n:json.loads((oracle/'exec'/f'{n}.json').read_text()) for n in calls}
    judges={(r['task'],r['call']):r for r in json.loads((oracle/'judge_responses.json').read_text())}
    out=layout.root/'legacy_report'; out.mkdir(parents=True,exist_ok=True)
    with patch.object(ob,'load_run',return_value=(tasks,rows)), \
         patch.object(ob,'execute',return_value=ex), \
         patch.object(ob,'judges',return_value=judges), \
         contextlib.redirect_stdout(io.StringIO()):
        ob.score(record,out,use_llm=False)
    actual=(out/'report.txt').read_text(); expected=(oracle/'report.txt').read_text()
    result=dict(report_equal=actual==expected,lines=len(actual.splitlines()),
                observation_source='historical CPU outcomes and cached judge decisions')
    assert result['report_equal'], 'all-flags-off report mismatch on identical observations'
    from ..v7 import v4_evaluation as baseline
    from . import v4_evaluation as actual
    expected_stdout, actual_stdout=io.StringIO(),io.StringIO()
    # Both functions run their real aggregation code; suppress their metrics-file
    # writes so the read-only historical generation directory stays untouched.
    with patch.object(baseline,'atomic_json'), contextlib.redirect_stdout(expected_stdout):
        expected_metrics=baseline.report(record/'tasks.json',record/'eval.jsonl')
    with patch.object(actual,'atomic_json'), contextlib.redirect_stdout(actual_stdout):
        actual_metrics=actual.report(record/'tasks.json',record/'eval.jsonl')
    result.update(evaluation_report_equal=expected_stdout.getvalue()==actual_stdout.getvalue(),
                  evaluation_metrics_equal=expected_metrics==actual_metrics)
    assert result['evaluation_report_equal'] and result['evaluation_metrics_equal']
    (out/'evaluation_report.txt').write_text(actual_stdout.getvalue())
    (out/'evaluation_metrics.json').write_text(json.dumps(actual_metrics,indent=2)+'\n')
    print('legacy report:',json.dumps(result),flush=True)
    return result


def check_d(layout, record, python, workers):
    from concurrent.futures import ThreadPoolExecutor
    from . import gen_inputs, evaluate, scorer
    atols=scorer.task_atols()
    tasks=json.loads((record/'tasks.json').read_text())['tasks']
    rows=load_rows(record/'gen.jsonl')
    he={int(r['task_id'].split('/')[1]):r for r in map(json.loads,evaluate.HEP.read_text().splitlines())}
    def one(task):
        n=task['task']; h=he[n]; directory=layout.root/'scorer_audit'/str(n)
        directory.mkdir(parents=True,exist_ok=True)
        job=dict(task=n,entry=task['entry'],put=task['put'],canon=h['prompt']+h['canonical_solution'],
                 atol=atols[n],rows=[r for r in rows if r['task']==n])
        jp,op=directory/'job.json',directory/'result.json'
        jp.write_text(json.dumps(job))
        return gen_inputs.sandbox(python,paths.HERE/'equality_audit.py',jp,op,1800)
    results=[]
    with ThreadPoolExecutor(workers) as pool:
        for result in pool.map(one,tasks):
            results.append(result)
            if len(results)%20==0: print('d:',len(results),'tasks audited',flush=True)
    changes=[c for r in results for c in r['changes']]
    result=dict(tasks=len(results),rows=len(rows),assertions=sum(r['assertions'] for r in results),
                unique_assertions=sum(r['unique_assertions'] for r in results),changed_assertions=len(changes),
                all_changes_involve_float=all(c['float_comparisons'] for c in changes))
    (layout.root/'scorer_changes.json').write_text(json.dumps(changes,indent=2)+'\n')
    lines=['\n## Shared scorer only: complete assertion verdict audit',
           '','Every assertion in all cached generation rows was scored with v7 equality and the shared scorer on identical CPU observations. Only `shared_scorer` was enabled. This isolates scoring from nondeterministic set order and deadlines.',
           '',json.dumps(result,sort_keys=True),'',
           '| Task | Arm | Sample | Assertion index (0-based) | Assertion | v7 → shared (canonical, PUT) |',
           '| --- | --- | --- | --- | --- | --- |']
    for c in changes:
        source=c['assertion'].replace('|',r'\|').replace('\n',' ')
        verdict=', '.join(k+': '+a+' → '+b for k,(a,b) in c['verdicts'].items())
        lines.append(f"| {c['task']} | {c['arm']} | {c['sample']} | {c['index']} | `{source}` | {verdict} |")
    doc=paths.HERE/'EQUIVALENCE.md'
    prefix=doc.read_text().split('\n## Shared scorer only:')[0]
    doc.write_text(prefix+'\n'.join(lines)+'\n')
    print('d:',json.dumps(result),flush=True)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checks',default='a,b,l,d')
    ap.add_argument('--workers',type=int,default=8)
    ap.add_argument('--output-name',default='equivalence')
    ap.add_argument('--resume',action='store_true')
    args=ap.parse_args()
    paths.set_dataset('humaneval')
    from . import v4_runtime
    original=paths.REPO/'trickcatcher_linefacts/out'
    record,oracle=original/'gen2_qwen7b_v7hyb_v4_r2',original/'oracle_v7hyb'
    layout=Layout(root=paths.DATA_OUT/args.output_name); layout.root.mkdir(parents=True,exist_ok=True)
    summary={}; dest=layout.root/'equivalence.json'
    if args.resume and dest.exists(): summary=json.loads(dest.read_text())
    with patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')), \
         patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')), \
         patch.dict(paths.CONFIG,{k:False for k in paths.FAIR_FLAGS}):
        python=v4_runtime.interpreter()
        for check in args.checks.split(','):
            if check=='a':
                for name in ('precond_qwen7b_v4','strategy_qwen7b_v4c','facts_v6','spec_facts_v7'):
                    seed_reuse(layout,original/name)
                summary['a']=check_a(layout,original)
            elif check=='b': summary['b']=check_b(layout,record,python)
            elif check=='l': summary['legacy_report']=check_legacy_report(layout,record,oracle)
            elif check=='c': summary['c']=check_c(layout,record,oracle,python,args.workers,args.resume)
            elif check=='d':
                with patch.dict(paths.CONFIG,shared_scorer=True):
                    summary['d']=check_d(layout,record,python,args.workers)
            else: ap.error('checks must be a,b,l,c,d')
            dest.write_text(json.dumps(summary,indent=2)+'\n')
    ok=all(r['equal'] for r in summary.get('a',{}).values())
    b=summary.get('b',{})
    ok &= not b.get('misses',0) and not b.get('mismatched_record_keys',[])
    ok &= not b.get('end_to_end',{}).get('misses',0) and not b.get('end_to_end',{}).get('differences',[])
    ok &= summary.get('legacy_report',{}).get('report_equal',True)
    ok &= summary.get('d',{}).get('all_changes_involve_float',True)
    c=summary.get('c',{})
    ok &= not c.get('evaluation',{}).get('field_differences',[]) and c.get('oracle',{}).get('report_equal',True)
    print('Equivalence results:',dest,flush=True)
    raise SystemExit(0 if ok else 1)


if __name__=='__main__': main()
