"""Offline registered final comparison (PREREG 2026-10-13/14, ref-only amendment).

Example (run from trickcatcher_linefacts):
  python -B analysis/final_protocol.py --run out/gen2_qwen7b_v7hyb_v4_r2 \
    --oracle out/oracle_v7hyb --dataset humaneval \
    --output analysis/final_protocol_smoke_v7.md

--run accepts either a generation directory or its parent dataset run directory.
--baselines accepts zero or more single-arm directories with eval.jsonl + oracle/.
For held-out data pass --dataset-root <builder root or he/>; --clusters question
reads question_id from tasks or the builder manifest's puts. Default split is dev
if present, otherwise heldout. Pilot is never silently pooled with dev/heldout.

No clients, generation, collect(), score(), or oracle-directory writes. Ref
programs and trusted canonical/contract sources come from cached execution jobs
(or the supplied dataset root). Historical non-tolerant executions are replayed
with v11_fair's worker/scorer. Witness execution always has its own temporary
output directory. Temporary files are deleted; only the report and JSON persist.
Metrics follow oracle_b01.fairness_metrics: D_I distinct calls per sample, D_IO
oracle-emitted assertions with correct expected values on D_I inputs. Replacement
oracles emit one assertion per distinct call. Undefined rates are JSON null.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
from math import comb
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

HOME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HOME.parent))
from . import oracle_b01 as ob, scorer

SEED, DRAWS = 20261013, 100
# Legacy task 58 has two string-set orderings with different recorded outcomes.
# The old worker did not record its random hash seed. Seed 12 reproduces both
# archived orderings; freeze it for all replays, not just this task or dataset.
HASH_SEED = 12
ARMS = ('plain', 'concept', 'toolinput', 'gen-plain', 'concept-hybrid',
        'placebo-hybrid', 'plain-hybrid')


def read_json(path):
    return json.loads(Path(path).read_text())


def task_id(value):
    return int(str(value).split('/')[-1])


def normalize_call(source):
    try:
        return ast.unparse(ast.parse(source, mode='eval').body)
    except (SyntaxError, TypeError, ValueError):
        return None


def calls_of(row, task):
    return list(dict.fromkeys(c for a in row['asserts']
                             if (c := ob.call_of(a['src'], task['entry']))))


def load_run(directory, fallback=None):
    directory = Path(directory).resolve()
    if not (directory / 'eval.jsonl').exists() and (directory / 'generation').is_dir():
        directory /= 'generation'
    if (directory / 'tasks.json').exists():
        bundle = read_json(directory / 'tasks.json')
        tasks = {task_id(t['task']): t for t in (bundle['tasks'] if isinstance(bundle, dict) else bundle)}
    elif fallback is not None:
        tasks = fallback
    else:
        raise ValueError('Run needs tasks.json')
    rows = [json.loads(line) for line in (directory / 'eval.jsonl').read_text().splitlines() if line.strip()]
    seen = set()
    for r in rows:
        r['task'], r['sample'] = task_id(r['task']), int(r['sample'])
        r.setdefault('split', tasks[r['task']].get('split', 'heldout'))
        key = (r['task'], r['arm'], r['sample'])
        if key in seen:
            raise ValueError(f'Duplicate row: {key}')
        seen.add(key)
    return directory, tasks, rows


def metadata(run, tasks, dataset, root=None):
    """Trusted dataset rows, task atols, and builder question mapping."""
    data, questions, atols = {}, {}, {}
    roots = []
    if root:
        p = Path(root).resolve()
        roots += [p, p / 'he', p.parent if p.name == 'he' else p]
    elif Path(dataset).is_dir():
        p = Path(dataset).resolve()
        roots += [p, p / 'he']
    roots += [run, run.parent]
    if dataset.lower() in ('humaneval', 'human-eval'):
        path = ob.HEP
        if path.exists():
            data = {task_id(r['task_id']): r for r in map(json.loads, path.read_text().splitlines())}
            atols.update(scorer.task_atols(path))
    for p in dict.fromkeys(roots):
        for name in ('humaneval_mbpp_plus.jsonl', 'humaneval_plus.jsonl'):
            path = p / name
            if path.exists():
                values = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
                data.update({task_id(r['task_id']): r for r in values})
                atols.update(scorer.task_atols(path))
        for name in ('manifest.json', 'tasks.json'):
            path = p / name
            if not path.exists():
                continue
            obj = read_json(path)
            records = obj if isinstance(obj, list) else obj.get('puts', obj.get('tasks', []))
            for r in records:
                if isinstance(r, dict) and 'question_id' in r:
                    t = r.get('task', r.get('task_id', r.get('vibepass_row')))
                    if t is not None:
                        t = task_id(t)
                        q = str(r['question_id'])
                        if t in questions and questions[t] != q:
                            raise ValueError(f'Conflicting question_id for task {t}')
                        questions[t] = q
    for t, r in data.items():
        if 'question_id' in r:
            questions[t] = str(r['question_id'])
    for t, r in tasks.items():
        if 'atol' in r:
            atols[t] = r['atol']
        if 'question_id' in r:
            q = str(r['question_id'])
            if t in questions and questions[t] != q:
                raise ValueError(f'Conflicting question_id for task {t}')
            questions[t] = q
    return data, atols, questions


def full_available(oracle):
    # Do not relabel ref as full in a ref-only run. Both full stages must exist.
    return all((oracle / name).exists() for name in ('post_responses.json', 'judge_responses.json'))


def cached_judges(oracle):
    p = oracle / 'judge_responses.json'
    return {(str(r['task']), r['call']): r for r in read_json(p)} if p.exists() else {}


def execute_records(tasks, rows, oracle, data, atols, temporary, workers=4, witnesses=None):
    """Read shared executions; replay old jobs/missing calls in isolated temp workers.

    Never trust old Boolean comparisons: raw outcomes are absent from those caches,
    so recomputing from cached programs is necessary. Cached ref programs are the
    exact same ones as in the run. Witness mode executes only bundle witnesses.
    """
    oracle, temporary = Path(oracle), Path(temporary)
    temporary.mkdir(parents=True, exist_ok=True)
    wanted = defaultdict(dict)
    if witnesses is not None:
        for t, calls in witnesses.items():
            wanted[t].update(dict.fromkeys(calls))
    else:
        for r in rows:
            wanted[r['task']].update(dict.fromkeys(calls_of(r, tasks[r['task']])))
    full = full_available(oracle)
    refs = ob.by_task(oracle, 'ref', ob.code_block)
    posts = ob.by_task(oracle, 'post', ob.post_of) if full else {}
    # facts/tracer imports and mutant construction install signal handlers and
    # must happen on the main thread, as in the original oracle execute().
    fallback_mutants = {t: ob.mutants(tasks[t], t) for t in wanted
                        if full and not (oracle/'exec'/f'{t}.job.json').exists()}

    def work(t):
        calls = list(wanted[t])
        if not calls:
            return t, dict(calls={})
        jp, rp = oracle / 'exec' / f'{t}.job.json', oracle / 'exec' / f'{t}.json'
        job = read_json(jp) if jp.exists() else None
        atol = atols.get(t, (job or {}).get('atol'))
        if atol is None:
            raise ValueError(f'No trusted atol for task {t}; supply --dataset-root')
        if (witnesses is None and job and rp.exists() and job.get('shared_scorer') is True
                and job.get('atol', 0) == atol and job.get('python_hash_seed') == HASH_SEED):
            record = read_json(rp)
            if job['put'] != tasks[t]['put']:
                raise ValueError(f'PUT mismatch in oracle task {t}')
            if all(c in record['calls'] and 'd_i' in record['calls'][c] for c in calls):
                return t, record
        if job is None:
            if t not in data:
                raise ValueError(f'No cached job or trusted dataset source for task {t}')
            h, task = data[t], tasks[t]
            # The refs mapping is loaded before dispatch below, never via a client.
            job = dict(entry=task['entry'], put=task['put'], base=task['base'],
                       canon=h['prompt'] + h['canonical_solution'],
                       contract=h['prompt'] + h['contract'] + '\n    pass\n',
                       spec=ob.preconditions.specification(task)[0], ref=refs.get(str(t), []),
                       post=posts.get(str(t), []), mutants=fallback_mutants.get(t, []))
        if job['put'] != tasks[t]['put']:
            raise ValueError(f'PUT mismatch in oracle task {t}')
        job = dict(job, calls=calls, atol=atol, shared_scorer=True, python_hash_seed=HASH_SEED,
                   dpp=[], tc=[], b1={}, o0={})
        if not full:
            job.update(post=[], mutants=[])
        job_path, result_path = temporary / f'{t}.job.json', temporary / f'{t}.json'
        job_path.write_text(json.dumps(job))
        env = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
               'PYTHONHASHSEED': str(HASH_SEED),
               'LINEFACTS_FAIR_FLAGS': json.dumps({'shared_scorer': True})}
        # -I implies -E and ignores PYTHONHASHSEED. Use -s -P with this
        # whitelisted environment instead: no user site or unsafe sys.path entry,
        # and the same network/process isolation as the original oracle worker.
        result = subprocess.run(['timeout', '-k', '5', '3000', 'unshare', '-rn',
                                 sys.executable, '-s', '-P', '-B', str(Path(ob.__file__)),
                                 'worker', str(job_path), str(result_path)],
                                env=env, capture_output=True, timeout=3010)
        if result.returncode or not result_path.exists():
            # Do not print worker output: generated programs may print arbitrary data.
            raise RuntimeError(f'Isolated oracle worker failed for task {t} (exit {result.returncode})')
        record = read_json(result_path)
        if set(calls) - set(record['calls']):
            raise ValueError(f'Unexecuted calls for task {t}')
        return t, record

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return {str(t): r for t, r in pool.map(work, sorted(wanted))}


def call_score(record, mode, judge=None):
    emit, cok, pok = ob.decide(mode, record, judge)
    valid = record.get('valid', False)
    return dict(emitted=bool(emit), d_i=bool(record.get('d_i', False)),
                d_io=bool(emit and valid and record.get('d_i', False) and cok),
                detecting=bool(emit and valid and cok and not pok),
                failing=bool(emit and not pok), correct_failing=bool(emit and not pok and valid and cok),
                flag_correct=bool(emit and (not cok or not valid)))


def score_samples(tasks, rows, executions, judges, mode):
    result = {}
    for r in rows:
        t, s = r['task'], r['sample']
        calls = calls_of(r, tasks[t])
        records = executions.get(str(t), {}).get('calls', {})
        if set(calls) - set(records):
            raise ValueError(f'Missing oracle records for {t}/{s}')
        scores = [call_score(records[c], mode, judges.get((str(t), c))) for c in calls]
        result[t, s] = dict(calls=calls, scores=scores,
                           detecting=any(x['detecting'] for x in scores),
                           d_i_sample=any(x['d_i'] for x in scores),
                           d_io_sample=any(x['d_io'] for x in scores),
                           flag_correct=any(x['flag_correct'] for x in scores),
                           generated_assertions=len(r['asserts']),
                           **{k: r.get(k) for k in ('llm_calls', 'n_in', 'n_out')})
    return result


def summarize(samples, k):
    rs = list(samples.values())
    assertions = [a for r in rs for a in r['scores']]
    counts = {name: sum(a[name] for a in assertions) for name in
              ('d_i', 'd_io', 'failing', 'correct_failing', 'emitted', 'flag_correct')}
    failing, correct = counts['failing'], counts['correct_failing']
    n = len(rs)
    def average(key):
        return sum(r[key] for r in rs) / n if n and all(r[key] is not None for r in rs) else None
    return dict(samples=n, tasks=len({t for t, s in samples}), K=k,
                detecting_samples=sum(r['detecting'] for r in rs),
                bug_per_run=sum(r['detecting'] for r in rs) / k,
                D_I=counts['d_i'], D_IO=counts['d_io'],
                D_I_samples=sum(r['d_i_sample'] for r in rs),
                D_IO_samples=sum(r['d_io_sample'] for r in rs),
                failing=failing, correct_failing=correct, false_alarms=failing-correct,
                precision=correct/failing if failing else None,
                false_alarm_rate=(failing-correct)/failing if failing else None,
                percent_samples_flagging_correct=100*sum(r['flag_correct'] for r in rs)/n if n else None,
                llm_calls_per_sample=average('llm_calls'), tokens_in_per_sample=average('n_in'),
                tokens_out_per_sample=average('n_out'),
                tokens_per_sample=(average('n_in')+average('n_out'))
                if average('n_in') is not None and average('n_out') is not None else None,
                assertions_per_sample=counts['emitted']/n if n else None,
                generated_assertions_per_sample=average('generated_assertions'),
                distinct_calls_per_sample=len(assertions)/n if n else None,
                # Historical witness_only.txt uses all emitted false alarms, not
                # the registered failing-assertion denominator. Keep this audit.
                emitted_false_alarms_per_sample=counts['flag_correct']/n if n else None)


def sign_test(wins, losses):
    n = wins + losses
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(wins, losses)+1)) / 2**n) if n else 1.0


def cut(scores, n, rng):
    hits = [x['detecting'] for x in scores]
    if n >= len(hits):
        return float(any(hits))
    if not any(hits) or n == 0:
        return 0.0
    return sum(any(hits[i] for i in rng.sample(range(len(hits)), n)) for _ in range(DRAWS))/DRAWS


def compare(a, b, clusters, k, mode, names, matched=False, metric='detecting'):
    # A task is paired only when both runs have all K samples. Never cherry-pick
    # available samples from partially completed baseline tasks.
    common = set(a) & set(b)
    ids = sorted(t for t in {t for t, s in common} if all((t, s) in common for s in range(k)))
    if not ids:
        return dict(first=names[0], second=names[1], skipped='No complete paired tasks')
    sums = defaultdict(lambda: [0.0, 0.0])
    rng = random.Random(f'{SEED}-{mode}-{names[0]}-{names[1]}')
    budget = 0
    for t in ids:
        for s in range(k):
            x, y = a[t, s], b[t, s]
            if matched:
                n = min(len(x['scores']), len(y['scores']))
                budget += n
                values = cut(x['scores'], n, rng), cut(y['scores'], n, rng)
            else:
                values = float(x[metric]), float(y[metric])
            for i, value in enumerate(values):
                sums[clusters[t]][i] += value
    wins = sum(x > y + 1e-9 for x, y in sums.values())
    losses = sum(y > x + 1e-9 for x, y in sums.values())
    return dict(first=names[0], second=names[1], metric=metric, tasks=len(ids),
                excluded_tasks=len({t for t, s in set(a) | set(b)})-len(ids),
                clusters=len(sums), wins=wins, losses=losses, ties=len(sums)-wins-losses,
                p_two_sided=sign_test(wins, losses),
                a_bug_per_run=sum(x for x, y in sums.values())/k,
                b_bug_per_run=sum(y for x, y in sums.values())/k,
                per_cluster={str(q): values for q, values in sorted(sums.items(), key=lambda x: str(x[0]))},
                matched=matched, matched_calls_per_sample=budget/(k*len(ids)) if matched else None)


def analyze(run, oracle, baselines, dataset, output, clusters='task', dataset_root=None,
            split='auto', workers=4):
    protected = [Path(run).resolve(), Path(oracle).resolve(),
                 *(Path(b).resolve() for b in baselines)]
    output = Path(output).resolve()
    if any(p == output or p in output.parents for p in protected):
        raise ValueError('Report output must be outside all input run/oracle directories')
    run, tasks, rows = load_run(run)
    oracle = Path(oracle).resolve()
    if split == 'auto':
        split = 'dev' if any(r['split'] == 'dev' for r in rows) else 'heldout'
    selected = [r for r in rows if r['split'] == split]
    if not selected:
        raise ValueError(f'No rows for split {split}')
    k = max(r['sample'] for r in selected)+1
    manifest = run/'manifest.json'
    if manifest.exists():
        k = int(read_json(manifest).get('k', k))
    ids = sorted(t for t, task in tasks.items() if task.get('split', split) == split)
    present = {(r['task'], r['arm'], r['sample']) for r in selected}
    expected = {(t, a, s) for t in ids for a in ARMS for s in range(k)}
    if present != expected:
        raise ValueError(f'Main run must have complete task x seven-arm x K cohort ({len(expected-present)} missing)')
    if any('tool_inputs' not in tasks[t] for t in ids):
        raise ValueError('Main task bundle needs tool_inputs to compute witness-only')
    data, atols, questions = metadata(run, tasks, dataset, dataset_root)
    if clusters == 'question' and set(ids)-set(questions):
        raise ValueError('Missing question_id; supply --dataset-root with held-out manifest/tasks')
    cluster_ids = questions if clusters == 'question' else {t: str(t) for t in ids}
    witness = {t: list(dict.fromkeys(c for src in tasks[t].get('tool_inputs', [])
                                    if (c := normalize_call(src)))) for t in ids}
    witness_rows = [dict(task=t, sample=s, asserts=[dict(src=f'assert {c} == None') for c in witness[t]],
                         llm_calls=0, n_in=0, n_out=0) for t in ids for s in range(k)]
    sources = {a: dict(tasks=tasks, rows=[r for r in selected if r['arm'] == a], oracle=oracle) for a in ARMS}
    skipped = []
    for baseline in baselines:
        directory = Path(baseline).resolve()
        name = directory.name
        if name in sources or name == 'witness-only':
            raise ValueError(f'Duplicate arm/baseline name: {name}')
        if not (directory/'eval.jsonl').exists() or not (directory/'oracle').is_dir():
            skipped.append(dict(baseline=name, reason='eval.jsonl or oracle/ absent'))
            continue
        bd, bt, br = load_run(directory, fallback=tasks)
        br = [r for r in br if r['split'] == split and r['task'] in ids]
        if not br:
            skipped.append(dict(baseline=name, reason=f'No overlapping {split} samples'))
            continue
        if len({r['arm'] for r in br}) != 1:
            raise ValueError(f'Baseline {name} must contain one arm')
        if any(r['sample'] not in range(k) for r in br):
            raise ValueError(f'Baseline {name} has incompatible K')
        for t in {r['task'] for r in br}:
            if bt[t]['put'] != tasks[t]['put']:
                raise ValueError(f'Baseline {name} PUT mismatch at task {t}')
        sources[name] = dict(tasks=bt, rows=br, oracle=directory/'oracle')
    modes = ['ref'] + (['full'] if full_available(oracle) else [])
    result = dict(dataset=dataset, split=split, interpretation='Development sanity; descriptive only'
                  if split in ('dev', 'pilot') else 'Held-out; confirmatory only if the real frozen protocol was followed',
                  tasks=len(ids), K=k, cluster_unit=clusters,
                  clusters=len({cluster_ids[t] for t in ids}), seed=SEED, draws=DRAWS,
                  replay_python_hash_seed=HASH_SEED,
                  skipped_baselines=skipped, baseline_status='No baselines supplied; comparisons skipped'
                  if not baselines else 'See skipped_baselines', oracles={},
                  scorer='pipelines/v11_fair_vp/scorer.py; rel_tol=1e-6, trusted task atol',
                  notes=['Precision and false-alarm rate share the failing-on-PUT assertion denominator.',
                         'Invalid inputs never detect and count as false alarms when failing on PUT.',
                         'Correct-program flags include all emitted wrong/invalid assertions, even PUT-passing ones.',
                         'Witness-only uses zero generation LLM calls/tokens; oracle costs are excluded for all arms.',
                         'Matched counts use distinct candidate calls before oracle abstention, as matched_subsets.py.',
                         'Baseline comparisons pair complete tasks with all K samples; excluded tasks are reported.',
                         'Full is included only when post and cached judge stages exist; no missing stages are generated.',
                         'D_I compares PUT against the trusted canonical reference, independent of oracle abstention.',
                         'Bug/run is contract-valid, oracle-correct assertions failing on PUT, divided by K.',
                         'Secondary D_I sign tests compare samples containing at least one D_I input.',
                         'CPU replays fix PYTHONHASHSEED=12 for every dataset. Historical caches omit hash seeds; task 58 string-set order affects detecting samples. Seed 12 was selected to reproduce its two archived string-set orderings in the witness cache. Executions without this recorded hash seed are replayed, including shared-scorer caches.',
                         'Assertions/sample means emitted replacement assertions; generated count is reported separately.'])
    with tempfile.TemporaryDirectory(prefix='final_protocol_') as tmp:
        tmp = Path(tmp)
        # Execute the main union once, rather than repeating every arm's calls.
        main_ex = execute_records(tasks, selected, oracle, data, atols, tmp/'arms', workers)
        witness_ex = execute_records(tasks, selected, oracle, data, atols, tmp/'witness', workers, witness)
        executions = {a: main_ex for a in ARMS}
        sources['witness-only'] = dict(tasks=tasks, rows=witness_rows, oracle=oracle)
        executions['witness-only'] = witness_ex
        for name, source in sources.items():
            if name in executions:
                continue
            # Baselines must use the same ref program pool as the main run.
            for t in {r['task'] for r in source['rows']}:
                def ref_sources(o):
                    p = o/'exec'/f'{t}.job.json'
                    return read_json(p)['ref'] if p.exists() else ob.by_task(o, 'ref', ob.code_block).get(str(t), [])
                if ref_sources(source['oracle']) != ref_sources(oracle):
                    raise ValueError(f'Baseline {name} ref program pool differs at task {t}')
            executions[name] = execute_records(source['tasks'], source['rows'], source['oracle'],
                                               data, atols, tmp/name, workers)
        for mode in modes:
            scores, metrics = {}, {}
            unavailable = []
            for name, source in sources.items():
                if mode == 'full' and not full_available(source['oracle']):
                    unavailable.append(name)
                    continue
                samples = score_samples(source['tasks'], source['rows'], executions[name],
                                        cached_judges(source['oracle']), mode)
                scores[name], metrics[name] = samples, summarize(samples, k)
            primary, secondary = [], []
            for name in ('plain-hybrid', 'toolinput', 'witness-only', *sorted(set(sources)-set(ARMS)-{'witness-only'})):
                if name not in scores:
                    continue
                primary.append(compare(scores['concept-hybrid'], scores[name], cluster_ids, k,
                                       mode, ('concept-hybrid', name)))
            controls = ('plain-hybrid', 'toolinput', 'witness-only', 'placebo-hybrid',
                        *sorted(set(sources)-set(ARMS)-{'witness-only'}))
            for name in controls:
                if name not in scores:
                    continue
                names = ('concept-hybrid', name)
                secondary.append(compare(scores[names[0]], scores[name], cluster_ids, k, mode, names,
                                         metric='d_i_sample'))
                secondary.append(compare(scores[names[0]], scores[name], cluster_ids, k, mode, names, matched=True))
            secondary.append(compare(scores['concept-hybrid'], scores['placebo-hybrid'], cluster_ids,
                                     k, mode, ('concept-hybrid', 'placebo-hybrid')))
            result['oracles'][mode] = dict(arms=metrics, primary=primary, secondary=secondary,
                                           unavailable_baselines=unavailable)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown(result))
    output.with_suffix('.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+'\n')
    return result


def markdown(result):
    def number(value, digits=2):
        return 'n/a' if value is None else f'{value:.{digits}f}'
    lines = ['# Final comparison protocol', '',
             f"Dataset: {result['dataset']}; split: {result['split']}; {result['tasks']} tasks; K={result['K']}; "
             f"sign tests by {result['cluster_unit']} ({result['clusters']} clusters).", '',
             result['interpretation']+'.', '', f"Scorer: {result['scorer']}.", '',
             f"Random subsets: seed {SEED}, {DRAWS} draws. {result['baseline_status']}.", '']
    lines += [f"- Skipped {s['baseline']}: {s['reason']}" for s in result['skipped_baselines']]
    for mode in ('ref', 'full'):
        if mode not in result['oracles']:
            continue
        section = result['oracles'][mode]
        lines += ['', f'## {mode} oracle', '',
                  '| Arm | Samples | Bug/run | D_I | D_IO | Precision | FA rate | Failing | Flag correct % | LLM calls/sample | Tokens in/out/sample | Assertions/sample |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for arm, m in sorted(section['arms'].items()):
            lines.append(f"| {arm} | {m['samples']} | {number(m['bug_per_run'],1)} | {m['D_I']} | {m['D_IO']} | "
                         f"{number(m['precision'],4)} | {number(m['false_alarm_rate'],4)} | {m['failing']} | "
                         f"{number(m['percent_samples_flagging_correct'])} | {number(m['llm_calls_per_sample'])} | "
                         f"{number(m['tokens_in_per_sample'])}/{number(m['tokens_out_per_sample'])} | {number(m['assertions_per_sample'])} |")
        lines += ['', '### Primary comparisons', '']
        for c in section['primary']:
            lines.append(comparison_line(c, number))
        lines += ['', '### Secondary comparisons', '']
        for c in section['secondary']:
            lines.append(comparison_line(c, number))
        lines += ['', '### Witness audit (same definitions as witness_only.txt)', '',
                  '| Arm | Bug/run | Distinct calls/sample | All emitted false alarms/sample |',
                  '|---|---:|---:|---:|']
        for arm in ('witness-only', 'toolinput', 'concept-hybrid', 'plain-hybrid'):
            m = section['arms'][arm]
            lines.append(f"| {arm} | {number(m['bug_per_run'],1)} | {number(m['distinct_calls_per_sample'],1)} | "
                         f"{number(m['emitted_false_alarms_per_sample'])} |")
        if section['unavailable_baselines']:
            lines += ['', 'Full unavailable for: '+', '.join(section['unavailable_baselines'])+'.']
    lines += ['', '## Definitions and limits', ''] + ['- '+n for n in result['notes']]
    return '\n'.join(lines)+'\n'


def comparison_line(c, number):
    label = f"{c['first']} vs {c['second']}"
    if 'skipped' in c:
        return f"- {label}: skipped ({c['skipped']})."
    metric = 'random matched detection' if c['matched'] else c['metric']
    return (f"- {label} ({metric}): {number(c['a_bug_per_run'])} vs {number(c['b_bug_per_run'])}; "
            f"wins/losses/ties {c['wins']}/{c['losses']}/{c['ties']}; two-sided p={number(c['p_two_sided'],6)}; "
            f"{c['tasks']} paired tasks, {c['clusters']} clusters, {c['excluded_tasks']} excluded tasks."
            + (f" Matched calls/sample={number(c['matched_calls_per_sample'])}." if c['matched'] else ''))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--oracle', type=Path, required=True)
    parser.add_argument('--baselines', type=Path, nargs='*', default=[])
    parser.add_argument('--dataset', required=True, help='Dataset name (or held-out root path)')
    parser.add_argument('--dataset-root', type=Path, help='Held-out builder root or he/ for atols/question ids')
    parser.add_argument('--clusters', choices=('question', 'task'), default='task')
    parser.add_argument('--split', choices=('auto', 'dev', 'pilot', 'heldout'), default='auto')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', type=Path, required=True, help='Markdown report; JSON written beside it')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('--workers must be positive')
    result = analyze(**vars(args))
    for mode, section in result['oracles'].items():
        print(f"[{mode}] " + ' | '.join(f"{a}: {section['arms'][a]['bug_per_run']:.1f}" for a in
                                       ('witness-only', 'toolinput', 'concept-hybrid', 'plain-hybrid')))
    print(f'Reports: {args.output}, {args.output.with_suffix(".json")}')


if __name__ == '__main__':
    main()
