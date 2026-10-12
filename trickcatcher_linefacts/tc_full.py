"""Faithful TrickCatcher arm with Qwen; gen makes calls, run is CPU-only."""
from __future__ import annotations
import argparse
import ast
import hashlib
import itertools
import json
import math
import random
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from trickcatcher_linefacts import gen_inputs, v4_runtime
from trickcatcher_linefacts.llm_client import Client, atomic_json

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
HEP = gen_inputs.CONTRACTS
ARM = 'tc-full'
MODEL = 'qwen2.5-coder-7b-instruct'
COMMIT = 'a0d285a77efff7c93fc280d606497d9de5e1defe'
SHA = {
    'genprog_tc_sys': '5d38456f5861453a96ebb691f1794876913f08688392fd3a5626907cba5471ad',
    'genprog_tc_usr': 'ce7b4adbf8d6c00a4f855191256c76ef7bf7dbad18362a8e0f73b1d3e3129317',
    **dict(zip(('geninput_generator_sys', 'geninput_usr'),
               ('4c9164d6fabaebe04301471c690cfa927eef4b2e39d80561b6125da06c35017d',
                'ce7b4adbf8d6c00a4f855191256c76ef7bf7dbad18362a8e0f73b1d3e3129317'))),
}
PARAMS = dict(temperature=1.0, top_p=1.0, max_tokens=2048)
TIMEOUTS = dict(load_timeout=5, base_timeout=20, call_timeout=1)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def templates(directory=None):
    directory = Path(directory) if directory else HERE / 'tc_templates'
    result = {}
    for name, expected in SHA.items():
        raw = (directory / name).read_bytes()
        if sha(raw) != expected:
            raise ValueError(f'TrickCatcher template {name} failed SHA256 verification')
        result[name] = raw.decode()
    return result


def seed(task, stage, index, rq2=False):
    # Stable, independent 32-bit seeds; rq2 has a separate stream.
    return int(sha(f'tc-full/20261011/{int(task)}/{int(rq2)}/{stage}/{index}'.encode())[:8], 16)


def messages(task, stage, template):
    sysname, usrname = ('genprog_tc_sys', 'genprog_tc_usr') if stage == 'variant' else ('geninput_generator_sys', 'geninput_usr')
    return [dict(role='system', content=template[sysname]),
            dict(role='user', content=template[usrname].format(function_and_docstring=task['put']))]


def source(text):
    blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', text, re.S)
    return '\n'.join(blocks) if blocks else text.strip()


def read_hep(path=HEP):
    return {int(r['task_id'].split('/')[1]): r for r in map(json.loads, Path(path).read_text().splitlines())}


def load_tasks(path=None, ids=None, rq2=False, hep=HEP):
    path = Path(path) if path else next((p for p in (OUT/'tasks_v4_all.json', OUT/'tasks_v3m_all.json') if p.exists()))
    data = json.loads(path.read_text())
    tasks = data['tasks'] if isinstance(data, dict) else data
    design = set(data.get('design_excluded', [])) if isinstance(data, dict) else {22, 33, 111, 122, 123, 139}
    tasks = sorted((t for t in tasks if t['task'] not in design), key=lambda t: t['task'])
    if ids is not None:
        wanted = set(ids)
        tasks = [t for t in tasks if t['task'] in wanted]
        if {t['task'] for t in tasks} != wanted:
            raise ValueError('requested task missing or design-excluded')
    elif len(tasks) != 133:
        raise ValueError(f'expected 133 non-design tasks, got {len(tasks)}')
    if rq2:
        canonical = read_hep(hep)
        tasks = [dict(t, put=canonical[t['task']]['prompt'] + canonical[t['task']]['canonical_solution']) for t in tasks]
    return dict(facts_version='tc-full', tasks=tasks, rq2=rq2, source_tasks=str(path.resolve()),
                source_tasks_sha256=sha(path.read_bytes()), design_excluded=sorted(design))


def put_json(path, data):
    v4_runtime.immutable(path, data)


def put_lines(path, rows):
    path = Path(path)
    text = ''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in rows)
    if path.exists():
        if path.read_text() != text:
            raise ValueError(f'artifact changed; use a fresh directory: {path}')
    else:
        temp = path.with_suffix('.jsonl.tmp')
        temp.write_text(text)
        temp.replace(path)


def generation_manifest(bundle):
    return dict(method=ARM, artifact_commit=COMMIT, template_sha256=SHA, parameters=PARAMS,
                n_variants=10, n_generators=4, draws_per_generator=100,
                seed_scheme='sha256(tc-full/20261011/task/rq2/stage/index)[:8]', rq2=bundle['rq2'],
                task_ids=[t['task'] for t in bundle['tasks']], tasks_sha256=sha(json.dumps(bundle, sort_keys=True).encode()))


def generate(bundle, out, *, client=None, workers=16):
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=True)
    template = templates()
    put_json(out/'tasks.json', bundle)
    manifest = generation_manifest(bundle)
    if (out/'generation_manifest.json').exists():
        old = json.loads((out/'generation_manifest.json').read_text())
        if {k: v for k, v in old.items() if k != 'model'} != manifest:
            raise ValueError('generation manifest changed; use a fresh directory')
        if all((out/'generation'/f"{t['task']}.json").exists() for t in bundle['tasks']):
            return out/'generation'
    client = client or Client(out/'cache', workers=workers)
    if client.model.lower().replace('_', '-').split('/')[-1] != MODEL:
        raise ValueError('tc-full requires Qwen2.5-Coder-7B-Instruct')
    put_json(out/'generation_manifest.json', dict(manifest, model=client.model))

    def task_job(task):
        path = out/'generation'/f"{task['task']}.json"
        if path.exists():
            return
        records = []
        for stage, n in (('variant', 10), ('generator', 4)):
            for i in range(n):
                request_seed = seed(task['task'], stage, i, bundle['rq2'])
                response = client.chat(messages(task, stage, template), request_seed, **PARAMS)
                records.append(dict(stage=stage, index=i, seed=request_seed, src=source(response['text']),
                                    **{k: v for k, v in response.items() if k != 'cache_hit'}))
        put_json(path, dict(task=task['task'], responses=records))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(task_job, bundle['tasks']))
    return out/'generation'


def isolated(mode, job, directory, python, timeout):
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory/'job.json', directory/'result.json'
    put_json(jp, dict(job, mode=mode))
    if not op.exists():
        result = gen_inputs.sandbox(python, HERE/'tc_full_worker.py', jp, op, timeout)
    else:
        result = json.loads(op.read_text())
    return result


def subset_scores(records, survivors, ks):
    """Analysis/utils.py:ep_compute_res(tc), retaining all maximal-vote ties."""
    result = {}
    for requested in ks:
        k = min(requested, len(survivors))
        total = math.comb(len(survivors), k) if k else 1
        tp = fp = emitting = 0
        for combo in itertools.combinations(survivors, k):
            chosen = set(combo); candidates = []
            for record in records:
                groups = [(len(chosen.intersection(g['members'])), g) for g in record['groups']]
                best = max((n for n, _ in groups), default=0)
                candidates.extend(g for n, g in groups if best and n == best)
            if candidates:
                fraction = sum(g['tp'] for g in candidates) / len(candidates)
                tp += fraction; fp += 1 - fraction; emitting += 1
        result[str(requested)] = dict(k=requested, effective_k=k, total=total, TP=tp, FP=fp,
                                      TP_rate=tp/total, FP_rate=fp/total,
                                      precision=tp/(tp+fp) if tp+fp else None,
                                      emitting_subsets=emitting)
    return result


def row_metrics(assertions):
    tp = sum(a['canon'] == 'ok' for a in assertions)
    return dict(assertions=len(assertions), TP=tp, FP=len(assertions)-tp,
                precision=tp/len(assertions) if assertions else None,
                detection=any(a['canon'] == 'ok' and a['put'] != 'ok' for a in assertions))


def execute_task(task, responses, out, python, hep, *, rq2=False, samples=3, subsets=True):
    tid = task['task']; work = Path(out)/'cpu'/str(tid)
    filtered = isolated('filter', dict(entry=task['entry'], base=task['base'], **TIMEOUTS,
                                     variants=[dict(index=r['index'], src=r['src']) for r in responses if r['stage']=='variant']),
                        work/'filter', python, 260)
    pool, generators = [], []
    for response in (r for r in responses if r['stage'] == 'generator'):
        i = response['index']; directory = work/'generators'/str(i)
        path = directory/'generated.json'
        if path.exists():
            generated = json.loads(path.read_text())
        else:
            try:
                code = gen_inputs.extract_generator(response['src'])
                generated = gen_inputs.generate_candidates(code, task, python, directory,
                    seed(tid, 'draw', i, rq2), n=100, per_call_timeout=1, total_timeout=120)
            except (SyntaxError, ValueError) as exc:
                generated = dict(attempted=0, returned=0, candidates=[], errors=[type(exc).__name__])
            put_json(path, generated)
        generators.append(dict(index=i, **{k: v for k, v in generated.items() if k != 'candidates'}))
        # The official input file includes duplicates. Restore worker multiplicities.
        for candidate in generated['candidates']:
            pool.extend([dict(input_repr=candidate['input_repr'], generator=i)] * candidate.get('occurrences', 1))
    put_json(work/'pool.json', pool)
    canonical = hep['prompt'] + hep['canonical_solution']
    survivors = [v['index'] for v in filtered['survivors']]
    # Results for repeated identical values are retained at distinct pool positions.
    rows, paper, all_records = [], [], []
    for s in range(samples):
        sample_seed = seed(tid, 'resample', s, rq2)
        positions = random.Random(sample_seed).sample(range(len(pool)), min(100, len(pool)))
        evidence = isolated('execute', dict(entry=task['entry'], put=task['put'], canon=canonical,
                    contract_src=hep['prompt'] + hep['contract'], variants=filtered['survivors'],
                    pool=[pool[i] for i in positions], **TIMEOUTS), work/'execute'/str(s), python,
                    max(120, len(positions)*(len(survivors)+3)*TIMEOUTS['call_timeout']+60))
        records = evidence['records']; all_records.extend(records)
        assertions = [r['assertion'] for r in records if 'assertion' in r]
        metrics = row_metrics(assertions)
        rows.append(dict(task=tid, split=task['split'], arm=ARM, sample=s, asserts=assertions, rq2=rq2,
                         metrics=metrics, sample_seed=sample_seed, sampled_indices=positions,
                         n_inputs=len(positions), n_pool=len(pool), n_survivors=len(survivors), doc_fail=task.get('doc_fail', False)))
        ks = range(2, 11) if subsets else [len(survivors)]
        paper.append(dict(task=tid, split=task['split'], sample=s, emitted=metrics,
                          subset_metrics=subset_scores(records, survivors, ks)))
    calls = dict(logical_calls=len(responses), variant_calls=10, generator_calls=4,
                 n_in=sum(r['n_in'] for r in responses), n_out=sum(r['n_out'] for r in responses),
                 transport_attempts=sum(r['transport_attempts'] for r in responses))
    return dict(rows=rows, paper=paper, summary=dict(task=tid, split=task['split'], n_pool=len(pool),
                n_unique_inputs=len({p['input_repr'] for p in pool}), survivors=survivors,
                base_results=filtered['base_results'], generators=generators, calls=calls,
                put_crashes=sum(r['put_status']!='ok' for r in all_records),
                variant_crashes=sum(v['status']!='ok' for r in all_records for v in r['variants']),
                serialization_errors=sum('emit_error' in r for r in all_records)))


def aggregate(rows, paper, summaries, rq2=False):
    result = {}
    for split in ['all'] + sorted({r['split'] for r in rows}):
        rs = [r for r in rows if split == 'all' or r['split'] == split]
        ps = [r for r in paper if split == 'all' or r['split'] == split]
        ss = [r for r in summaries if split == 'all' or r['split'] == split]
        tids = {r['task'] for r in rs}; n = len(rs)
        assertions = [a for r in rs for a in r['asserts']]
        metrics = row_metrics(assertions)
        metrics.update(tasks=len(tids), samples=n, detecting_samples=sum(r['metrics']['detection'] for r in rs),
                       detection_per_sample=sum(r['metrics']['detection'] for r in rs)/max(1,n),
                       any_of_K=sum(any(r['metrics']['detection'] for r in rs if r['task']==t) for t in tids),
                       false_alarm_rate=metrics['FP']/len(assertions) if assertions else 0,
                       assertions_per_sample=len(assertions)/max(1,n),
                       short_pools=sum(r['n_pool']<100 for r in ss))
        paper_metrics = {}
        for k in sorted({k for p in ps for k in p['subset_metrics']}, key=int):
            # Notebook aggregation within each resample, followed by K averaging.
            repeat_metrics = []
            for s in sorted({p['sample'] for p in ps}):
                subset = [p['subset_metrics'][k] for p in ps if p['sample']==s and k in p['subset_metrics']]
                recall = sum(v['TP_rate'] for v in subset)/max(1,len(tids))
                precisions = [v['precision'] for v in subset if v['precision'] is not None]
                precision = sum(precisions)/len(precisions) if precisions else None
                repeat_metrics.append(dict(sample=s, recall=recall, precision=precision,
                    F1=2*precision*recall/(precision+recall) if precision is not None and precision+recall else 0,
                    expected_FP_programs=sum(v['FP_rate'] for v in subset)))
            paper_metrics[k] = {key: sum(v[key] for v in repeat_metrics if v[key] is not None)/
                                max(1,sum(v[key] is not None for v in repeat_metrics))
                                for key in ('recall','F1','expected_FP_programs')}
            defined = [v['precision'] for v in repeat_metrics if v['precision'] is not None]
            paper_metrics[k].update(precision=sum(defined)/len(defined) if defined else None,
                                   repeats=repeat_metrics)
        usage = {key: sum(s['calls'][key] for s in ss) for key in ('logical_calls','variant_calls','generator_calls','n_in','n_out','transport_attempts')}
        result[split] = dict(metrics=metrics, paper=paper_metrics, llm=usage)
        if rq2:
            result[split]['rq2'] = dict(correct_programs=len(tids),
                programs_with_reported_test=sum(any(r['asserts'] for r in rs if r['task']==t) for t in tids),
                programs_with_contract_invalid_report=sum(any(not a['input_valid'] for r in rs if r['task']==t for a in r['asserts']) for t in tids))
    return result


def run(out, python=None, *, hep=HEP, samples=None, workers=8, subsets=True):
    out = Path(out).resolve()
    bundle = json.loads((out/'tasks.json').read_text())
    templates()  # CPU/resume paths verify the original templates too.
    expected = generation_manifest(bundle)
    manifest = json.loads((out/'generation_manifest.json').read_text())
    if {k: v for k,v in manifest.items() if k != 'model'} != expected:
        raise ValueError('generation manifest does not match tasks/settings')
    rq2 = bundle['rq2']; samples = samples or (1 if rq2 else 3)
    if rq2 and samples != 1:
        raise ValueError('RQ2 uses one seeded resample')
    python = v4_runtime.interpreter(python)
    he = read_hep(hep)
    put_json(out/'cpu_manifest.json', dict(python=str(python), samples=samples, subsets=subsets, timeouts=TIMEOUTS,
        hep_path=str(Path(hep).resolve()), hep_sha256=sha(Path(hep).read_bytes()),
        sources={name: sha((HERE/name).read_bytes()) for name in ('tc_full.py','tc_full_worker.py','gen_inputs.py','generator_worker.py')}))
    environment = isolated('environment', {}, out/'cpu'/'environment', python, 30)
    if environment['cyaron'] != '0.7.0':
        raise ValueError(f'expected v4 cyaron 0.7.0, got {environment["cyaron"]}')

    def one(task):
        path = out/'results'/f"{task['task']}.json"
        if path.exists():
            return json.loads(path.read_text())
        responses = json.loads((out/'generation'/f"{task['task']}.json").read_text())['responses']
        if [(r['stage'],r['index']) for r in responses] != [('variant',i) for i in range(10)] + [('generator',i) for i in range(4)]:
            raise ValueError('incomplete generation artifact')
        value = execute_task(task, responses, out, python, he[task['task']], rq2=rq2, samples=samples, subsets=subsets)
        put_json(path, value)
        return value
    with ThreadPoolExecutor(max_workers=workers) as pool:
        values = list(pool.map(one, bundle['tasks']))
    rows = [r for v in values for r in v['rows']]
    paper = [r for v in values for r in v['paper']]
    summaries = [v['summary'] for v in values]
    put_lines(out/'eval.jsonl', rows)
    put_json(out/'paper_metrics.json', paper)
    put_json(out/'task_summary.json', summaries)
    report = aggregate(rows, paper, summaries, rq2)
    log = out/'cache'/'calls.jsonl'
    physical = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    report['physical_llm'] = dict(successful_cache_misses=sum(not r.get('cache_hit') and 'n_in' in r for r in physical),
                                cache_hits=sum(bool(r.get('cache_hit')) for r in physical),
                                failed_transport_attempts=sum('error' in r for r in physical))
    # Physical cache-hit logs may grow on a partial generation resume; this report
    # is a current diagnostic, not a frozen task/result artifact.
    atomic_json(out/'report.json', report)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cmd', choices=('gen','run','rq2'))
    ap.add_argument('--stage', choices=('gen','run','both'), default='both', help='rq2 only; run is CPU-only')
    ap.add_argument('--tasks', type=Path, help='default: tasks_v4_all.json, falling back to tasks_v3m_all.json')
    ap.add_argument('--ids', help='comma-separated smoke task subset; default all 133')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--hep', type=Path, default=HEP)
    ap.add_argument('--python', type=Path, help='dedicated v4 venv interpreter, or V4_PYTHON')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--samples', type=int, help='default 3 main, 1 RQ2')
    ap.add_argument('--no-subsets', action='store_true', help='omit k=2..10 averaging; keep all-survivor paper metrics')
    a = ap.parse_args()
    if a.workers < 1 or (a.samples is not None and a.samples < 1):
        ap.error('workers/samples must be positive')
    rq2 = a.cmd == 'rq2'; out = a.out or OUT/('tcfull_qwen7b_rq2' if rq2 else 'tcfull_qwen7b')
    do_gen = a.cmd == 'gen' or rq2 and a.stage in ('gen','both')
    do_run = a.cmd == 'run' or rq2 and a.stage in ('run','both')
    if do_gen:
        ids = list(map(int,a.ids.split(','))) if a.ids else None
        bundle = load_tasks(a.tasks, ids, rq2, a.hep)
        generate(bundle, out, workers=a.workers)
        print(f'Generated {len(bundle["tasks"])} tasks; expected logical calls {14*len(bundle["tasks"])}')
    if do_run:
        if json.loads((out/'tasks.json').read_text())['rq2'] != rq2:
            ap.error('main/RQ2 output mismatch')
        report = run(out, a.python, hep=a.hep, samples=a.samples, workers=a.workers, subsets=not a.no_subsets)
        print(json.dumps(report['all'], indent=2))


if __name__ == '__main__':
    main()
