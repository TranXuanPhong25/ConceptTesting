"""v42 mutant-disagreement oracle questions: CPU ceiling (see PREREG.md). No LLM. Usage (repo root):
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v42_mutoracle/mutoracle.py

Tool side (PUT + public examples only): v41 sampled pool and PUT outcomes, v34 surviving mutants run on that pool,
inputs where the PUT and a mutant disagree -> binary questions -> package of <= 32 inputs.
Ceiling side (references + evaluator contract, only here): exposure, and whether the mutant output is the right answer.
"""
import hashlib
import json
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from trickcatcher_linefacts.analysis.v41_iorel import iorel
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, same
from trickcatcher_linefacts.pipelines.v34_ftplacebo.gen_inputs import sandbox
from trickcatcher_linefacts.pipelines.v34_ftplacebo.paths import CONFIG

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v42_mutoracle'
CHUNK = 10
MAX_TIMEOUTS = 2
CHUNK_TIMEOUT = 3600
MAX_INPUTS = 32
PER_MUTANT = 2
GATE_D1 = 17
GATE_LIFT = 2.0


def load_pool(cid, v41_row):
    """v41 frozen inputs + PUT outcomes; the input-set hash must match the v41 ceiling row."""
    base = iorel.OUT / 'cases' / cid / 'put'
    job = json.loads((base / 'job.json').read_text())
    res = json.loads((base / 'result.json').read_text())
    inputs = job['inputs']
    if hashlib.sha256(json.dumps(inputs).encode()).hexdigest() != v41_row['inputs_sha256']:
        raise ValueError('v41 input set hash mismatch')
    return inputs, res['put']


def batch(d, sources, order, entry, inputs):
    """One ft_worker process, cached by job content."""
    d.mkdir(parents=True, exist_ok=True)
    jp, op = d / 'job.json', d / 'result.json'
    job = dict(sources={k: sources[k] for k in order}, order=order, entry=entry, inputs=inputs, per_call_timeout=1,
               max_timeouts=MAX_TIMEOUTS)
    if op.exists() and jp.exists() and json.loads(jp.read_text()) == job:
        return json.loads(op.read_text())
    op.unlink(missing_ok=True)
    jp.write_text(json.dumps(job))
    return sandbox(CONFIG['V4_PYTHON'], iorel.WORKER, jp, op, CHUNK_TIMEOUT)


def run_mutants(cid, sources, names, entry, inputs):
    """Surviving mutants on the pool, <= CHUNK mutants per process; a failed chunk is retried one process per mutant
    (as v34 ft_run.execute), and a mutant failing alone counts as skipped. Returns (outcomes, chunk failures)."""
    out, failures = {}, 0
    for c in range(0, len(names), CHUNK):
        order = names[c:c + CHUNK]
        d = OUT / 'cases' / cid / f'chunk{c // CHUNK:03d}'
        try:
            out.update(batch(d, sources, order, entry, inputs))
        except RuntimeError:
            failures += 1
            for name in order:
                try:
                    out.update(batch(d / name, sources, [name], entry, inputs))
                except RuntimeError:
                    out[name] = [['skipped']] * len(inputs)
    return out, failures


def load_ref(case, inputs):
    """v41 frozen reference/contract batch; never re-run here (a differing job would overwrite the v41 cache)."""
    ref = case['reference']
    d = iorel.OUT / 'cases' / case['case_id'] / 'ref'
    job = dict(sources={'contract': ref['contract'], 'ref': ref['source']}, order=['contract', 'ref'], entry=ref['entry'],
               inputs=inputs, per_call_timeout=1, max_timeouts=iorel.MAX_TIMEOUTS)
    if not (d / 'result.json').exists() or json.loads((d / 'job.json').read_text()) != job:
        raise ValueError('v41 reference cache missing or differs')
    return json.loads((d / 'result.json').read_text())


def tool(case, run, v41_row):
    cid = case['case_id']
    inputs, put_raw = load_pool(cid, v41_row)
    job = json.loads((run.root / 'cases' / cid / 'tool' / 'phase2' / 'job.json').read_text())
    names = job['order'][1:]
    raw, chunk_failures = run_mutants(cid, job['sources'], names, case['entry'], inputs) if names else ({}, 0)
    put = [iorel.value(o) for o in put_raw]
    disagree, seen, collapsed, unusable = {}, set(), 0, 0
    for name in names:
        vec = [iorel.value(o) for o in raw[name]]
        if all(v is None for v in vec):
            unusable += 1
            continue
        key = json.dumps(vec, default=repr)
        if key in seen:
            collapsed += 1
            continue
        seen.add(key)
        comparable = [i for i, (a, b) in enumerate(zip(put, vec)) if a is not None and b is not None]
        d = [i for i in comparable if not same(put[i], vec[i])]
        if d:
            disagree[name] = dict(idx=sorted(d, key=lambda i: (len(inputs[i]), inputs[i])), share=len(d) / len(comparable),
                                  vec={i: vec[i] for i in d})
    order = sorted(disagree, key=lambda m: (disagree[m]['share'], m))
    chosen, questions, taken, pos = [], [], {m: 0 for m in order}, {m: 0 for m in order}
    while len(chosen) < MAX_INPUTS:
        progressed = False
        for m in order:
            if len(chosen) >= MAX_INPUTS or taken[m] >= PER_MUTANT:
                continue
            idx = disagree[m]['idx']
            while pos[m] < len(idx) and idx[pos[m]] in chosen:
                pos[m] += 1
            if pos[m] < len(idx):
                chosen.append(idx[pos[m]])
                questions.append((idx[pos[m]], m))
                taken[m] += 1
                progressed = True
        if not progressed:
            break
    per_input = {k: [m for m in order if k in disagree[m]['vec']] for k in chosen}
    skipped = {m: sum(o[0] in ('skipped', 'timeout') for o in raw[m]) for m in names}
    return dict(case_id=cid, inputs=inputs, put=put_raw, disagree=disagree, chosen=chosen, questions=questions,
                per_input=per_input, mutants=len(names), collapsed=collapsed, unusable=unusable,
                disagreeing_mutants=len(disagree), chunk_failures=chunk_failures,
                mutants_with_skips=sum(v > 0 for v in skipped.values()), skipped_calls={m: v for m, v in skipped.items() if v})


def main():
    run = ft_run.FTRun('vibepass_half')
    v41 = {r['case_id']: r for r in json.loads((iorel.OUT / 'ceiling.json').read_text())['rows']}

    def safe_tool(case):
        try:
            return tool(case, run, v41[case['case_id']])
        except Exception as exc:  # recorded, not fatal
            return dict(case_id=case['case_id'], error=f'{type(exc).__name__}: {exc}'[:300])
    with ThreadPoolExecutor(6) as pool:
        tools = {t['case_id']: t for t in pool.map(safe_tool, run.cases)}
    official = Reference(run)
    official.root = iorel.OUT / 'official'  # v41 cache, content-digest keyed and immutable
    rows, agree = [], [0, 0]
    split = dict(mutant_right=0, put_right=0, neither=0)
    for case in run.cases:
        cid = case['case_id']
        t = tools[cid]
        if 'error' in t:
            rows.append(dict(case_id=cid, error=t['error'], c1=False, d1=False, d2=False, random_k=0.0))
            continue
        try:
            res = load_ref(case, t['inputs'])
            valid, exposing, truth = set(), set(), {}
            for k in range(len(t['inputs'])):
                if res['contract'][k][0] != 'ok':
                    continue
                valid.add(k)
                a, b = iorel.value(t['put'][k]), iorel.value(res['ref'][k])
                truth[k] = b
                if a is not None and b is not None and not same(a, b):
                    exposing.add(k)
            shown = set(t['chosen'])
            confirmed = set()
            for k in sorted(shown | set(sorted(exposing)[:iorel.OFFICIAL_EXPOSING_RECHECK])):
                ok = iorel.official_exposes(official, case, t['inputs'][k])
                agree[0] += ok == (k in exposing)
                agree[1] += 1
                if ok and k in exposing:
                    confirmed.add(k)
        except Exception as exc:  # recorded, not fatal
            rows.append(dict(case_id=cid, error=f'ceiling: {type(exc).__name__}: {exc}'[:300], c1=False, d1=False, d2=False,
                             random_k=0.0))
            continue

        def mutant_right(k, m):
            v = t['disagree'][m]['vec'][k]
            return truth.get(k) is not None and v is not None and same(v, truth[k])
        d1_q = [(k, m) for k, m in t['questions'] if k in confirmed and mutant_right(k, m)]
        d1_uncapped = any(mutant_right(k, m) for m, d in t['disagree'].items() for k in d['idx'] if k in exposing)
        task_split = dict(mutant_right=0, put_right=0, neither=0)
        for k, m in t['questions']:
            if k not in valid or truth.get(k) is None:
                continue
            key = ('mutant_right' if mutant_right(k, m) else
                   'put_right' if same(iorel.value(t['put'][k]), truth[k]) else 'neither')
            task_split[key] += 1
        for key in split:
            split[key] += task_split[key]
        n, e, k = len(t['inputs']), len(exposing), len(shown)
        lift = ((len(shown & exposing) / k) / (e / n) if k else 0.0) if e else None
        rows.append(dict(case_id=cid, inputs=n, valid_inputs=len(valid), exposing_batch=e, mutants=t['mutants'],
                         collapsed=t['collapsed'], disagreeing_mutants=t['disagreeing_mutants'],
                         unusable=t['unusable'], chunk_failures=t['chunk_failures'], skipped_calls=t['skipped_calls'],
                         mutants_with_skips=t['mutants_with_skips'], package_inputs=k, v41_c1=v41[cid]['c1'], package_questions=len(t['questions']),
                         package_valid=len(shown & valid), package_exposing_batch=len(shown & exposing),
                         c1=bool(confirmed), d1=bool(d1_q), d1_uncapped_batch=d1_uncapped, d2=bool(confirmed & shown),
                         d1_questions=len(d1_q), question_split=task_split, random_k=round(iorel.random_k(n, e, k), 4),
                         lift=lift))
    ok_rows = [r for r in rows if 'error' not in r]
    d1, d2 = sum(r['d1'] for r in rows), sum(r['d2'] for r in rows)
    e_random = sum(r['random_k'] for r in rows)
    lifts = [r['lift'] for r in ok_rows if r['c1'] and r['lift'] is not None]
    median_lift = statistics.median(lifts) if lifts else 0.0
    lifts_v41 = [r['lift'] for r in ok_rows if r['v41_c1'] and r['lift'] is not None]
    summary = dict(n=len(rows), errors=len(rows) - len(ok_rows), c1=sum(r['c1'] for r in rows), d1=d1, d2=d2,
                   d1_uncapped_batch=sum(r.get('d1_uncapped_batch', False) for r in rows),
                   expected_random_k_d2=round(e_random, 2), median_lift=round(median_lift, 3), question_split=split,
                   median_lift_over_v41_c1=round(statistics.median(lifts_v41), 3) if lifts_v41 else None, v41_c1=22,
                   unusable=sum(r['unusable'] for r in ok_rows), chunk_failures=sum(r['chunk_failures'] for r in ok_rows),
                   package_valid_share=round(sum(r['package_valid'] for r in ok_rows) / max(1, sum(r['package_inputs'] for r in ok_rows)), 3),
                   mutants=sum(r['mutants'] for r in ok_rows), collapsed=sum(r['collapsed'] for r in ok_rows),
                   mutants_with_skips=sum(r['mutants_with_skips'] for r in ok_rows), official_agreement=f'{agree[0]}/{agree[1]}',
                   verdict='go' if d1 >= GATE_D1 and d2 > e_random and median_lift >= GATE_LIFT else 'no-go')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'ceiling.json').write_text(json.dumps(dict(summary=summary, rows=rows), indent=1) + '\n')
    (OUT / 'packages.json').write_text(json.dumps({k: dict(questions=[(v['inputs'][i], m) for i, m in v['questions']],
                                                           disagreeing_per_input={v['inputs'][i]: ms for i, ms in v['per_input'].items()})
                                                   if 'error' not in v else dict(error=v['error'])
                                                   for k, v in tools.items()}, indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
