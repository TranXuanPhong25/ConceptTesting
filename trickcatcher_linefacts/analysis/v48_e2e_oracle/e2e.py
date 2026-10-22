"""v48 saved-input selection -> tc program oracle. References enter only score.
PYTHONPATH=. $V4_PYTHON .../e2e.py status|execute|score [execute --tasks 3,46]
"""
import argparse
import ast
import collections
import hashlib
import itertools
import json
import math
import random
import sys
from contextlib import contextmanager
from pathlib import Path

sys.dont_write_bytecode = True
from trickcatcher_linefacts import tc_full
from trickcatcher_linefacts.analysis.v41_iorel import iorel
from trickcatcher_linefacts.analysis.v46_mutoracle_fixed import oracle
from trickcatcher_linefacts.analysis.v47_concept_select import select_run as select
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_run, source_view
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import digest, immutable
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, same
from trickcatcher_linefacts.pipelines.v34_ftplacebo.paths import CONFIG, REPO

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v48_e2e_oracle'
SPLIT = ft_run.HERE / 'vibepass_half.json'
DATA = REPO / CONFIG['vibepass']['root']
EXACT_MAX = 20000
DRAWS = 2000
PRIORITY = ('coverage', 'mutation', 'boundary', 'class', 'spec_range', 'value_biased')
METRICS = ('correct_assertions', 'confirmed_tasks', 'fa_tests', 'fa_tasks', 'unconfirmed', 'tests', 'put_exception_inputs')


class Inventory:
    def __init__(self):
        self.files = {}

    def add(self, path):
        path = Path(path).resolve()
        key = str(path.relative_to(REPO))
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if key in self.files and self.files[key] != sha:
            raise ValueError('input artifact changed during run: ' + key)
        self.files[key] = sha
        return path

    def read(self, path):
        path = self.add(path)
        return json.loads(path.read_text())

    def tree(self, root):
        for path in sorted(Path(root).rglob('*.json')):
            self.add(path)

    def finish(self):
        for mod in list(sys.modules.values()):
            p = getattr(mod, '__file__', None)
            if p and Path(p).suffix == '.py' and Path(p).resolve().is_relative_to(REPO):
                self.add(p)
        for p in (HERE / 'PREREG.md', ft_run.HERE / 'config.json', iorel.WORKER, ft_run.HERE / 'flow_worker.py'):
            self.add(p)
        for name in list(self.files):
            self.add(REPO / name)
        return dict(sorted(self.files.items()))


def planned(inv):
    tasks = [str(n) for n in inv.read(SPLIT)['tasks']]
    inv.add(oracle.QUESTIONS)
    questions = oracle.load_questions()
    program_tasks = {q['case_id'] for q in questions}
    if not program_tasks <= set(tasks):
        raise ValueError('questions outside the registered cohort')
    return tasks, program_tasks


def status(inv=None, tasks=None):
    inv = inv or Inventory()
    cohort, program_tasks = planned(inv)
    wanted = set(cohort if tasks is None else tasks)
    if not wanted <= set(cohort):
        raise ValueError('unknown task(s): ' + ','.join(sorted(wanted - set(cohort))))
    prepared = inv.read(select.OUT / 'prepared.json')
    missing_prep = sorted(wanted - set(prepared), key=int)
    calls, programs, skipped, bad = [], [], [], []
    for cid in cohort:
        if cid not in wanted:
            continue
        p = prepared.get(cid, {})
        for arm in select.ARMS:
            if cid not in prepared:
                calls.append(select.OUT / 'calls' / cid / f'{arm}.json')
            elif 'error' in p or not p.get('menus', {}).get(arm, {}).get('items'):
                skipped.append([cid, arm])
            else:
                calls.append(select.OUT / 'calls' / cid / f'{arm}.json')
        if cid in program_tasks:
            programs.extend(oracle.OUT / 'programs' / 'tc' / cid / f'{i}.json' for i in range(oracle.NPROG))

    def count(paths, program=False):
        present, overflow, empty, missing = 0, 0, 0, []
        for path in paths:
            if not path.is_file():
                missing.append(str(path.relative_to(REPO)))
                continue
            present += 1
            try:
                r = inv.read(path)
                if not isinstance(r.get('text'), str) or 'finish_reason' not in r:
                    raise ValueError('record schema')
                if program and not r.get('digest'):
                    raise ValueError('missing digest')
                overflow += r['finish_reason'] == 'context_overflow'
                empty += not r['text'].strip() and r['finish_reason'] != 'context_overflow'
            except (ValueError, TypeError, AttributeError) as exc:
                bad.append(dict(path=str(path.relative_to(REPO)), error=str(exc)))
        return dict(planned=len(paths), present=present, missing=missing,
                    context_overflow=overflow, empty_non_overflow=empty)

    v47, v46 = count(calls), count(programs, True)
    return dict(tasks=len(wanted), program_tasks=len(wanted & program_tasks),
                abstaining_tasks=sorted(wanted - program_tasks, key=int), v47=v47, v46_tc=v46,
                skipped_v47=skipped, missing_prepared=missing_prep, bad_records=bad,
                complete=not (missing_prep or bad or v47['missing'] or v46['missing']))


def tool_cases(inv, tasks):
    """Only the public example file and PUTs; FTRun loads evaluator data, so is score-only."""
    public_path = inv.add(DATA / 'humaneval_mbpp.jsonl')
    public = {str(int(r['task_id'].split('/')[1])): r['test']
              for r in map(json.loads, public_path.read_text().splitlines())}
    out = {}
    for cid in tasks:
        path = inv.add(DATA / 'PUTs' / f'HumanEval_{cid}' / 'put0.py')
        source = path.read_text()
        funcs = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)]
        entry = funcs[-1].name
        case = dict(case_id=cid, source=source, entry=entry, base=public[cid], valid_code=None)
        if 'exec(' in case['base'] or 'is_valid_test' in case['base']:
            raise ValueError('public test guard: ' + cid)
        out[cid] = case
    return out


def task_view(case):
    return source_view.prepare(case['source'], case['entry'], case['base'], valid_code=None)


def pool_inputs(inv, cid):
    return inv.read(iorel.OUT / 'cases' / cid / 'put' / 'job.json')['inputs']


def pool_subset(inputs, cid):
    return random.Random(f'v48/pool/{cid}').sample(list(dict.fromkeys(inputs)), min(600, len(set(inputs))))


def item_inputs(prep, items):
    return set(lit for it in items for lit in prep['kinds'][it['kind']][it['instance']])


def all_inputs(prep):
    return set().union(*(item_inputs(prep, prep.get('menus', {}).get(a, {}).get('items', [])) for a in select.ARMS))


def ordered(inputs):
    return sorted(set(inputs), key=lambda lit: (hashlib.sha256(lit.encode()).hexdigest(), lit))


def emitted(inputs, rows, rule='vote', cap=20):
    found = [lit for lit in ordered(inputs) if rows[lit][rule] is not None]
    return found if cap is None else found[:cap]


def vote(put_raw, program_raw):
    put = iorel.value(put_raw)
    if put is None or put[0] != 'ok':
        return None, None
    vals = [iorel.value(o) for o in program_raw]
    groups = []
    for v in vals:
        if v is None or v[0] != 'ok' or same(v, put):
            continue
        g = next((g for g in groups if same(g[0], v)), None)
        if g is None:
            groups.append([v, 1])
        else:
            g[1] += 1
    chosen = max(groups, key=lambda g: g[1])[0] if groups else None
    consensus = vals[0] if len(vals) >= 3 and all(v is not None and v[0] == 'ok' for v in vals) \
        and all(same(vals[0], v) for v in vals) and not same(vals[0], put) else None
    return chosen, consensus


def raw_votes(put_raw, program_raw):
    """Persist worker reprs, not typed tuples: JSON lists would change v46's typed equality."""
    def raw(value):
        if value is None:
            return None
        return next(o for o in program_raw if iorel.value(o) is not None and same(iorel.value(o), value))
    v, c = vote(put_raw, program_raw)
    return raw(v), raw(c)


@contextmanager
def execution_root(root):
    old = oracle.OUT
    oracle.OUT = root
    try:
        yield
    finally:
        oracle.OUT = old


def checked_programs(inv, case):
    templates = tc_full.templates()
    for name in tc_full.SHA:
        inv.add(tc_full.HERE / 'tc_templates' / name)
    msgs = oracle.tc_messages(case, 'tc', [], templates)
    overflow = []
    for i in range(oracle.NPROG):
        rec = inv.read(oracle.OUT / 'programs' / 'tc' / case['case_id'] / f'{i}.json')
        seed = int(hashlib.sha256(f"v46/{case['case_id']}/tc/{i}".encode()).hexdigest()[:8], 16)
        if rec['digest'] != oracle.digest(msgs, dict(seed=seed, **tc_full.PARAMS)):
            raise ValueError(f"v46 prompt/params digest differs: {case['case_id']}/{i}")
        if rec['finish_reason'] == 'context_overflow':
            overflow.append(i)
    srcs = oracle.programs(case, 'tc', None)
    for i in overflow:
        srcs[i] = ''
    return srcs, overflow


def execute_case(inv, case, prep, program_tasks, root):
    cid = case['case_id']
    for path in (Path(__file__), Path(oracle.__file__), Path(iorel.__file__), Path(ft_run.__file__),
                 iorel.WORKER, ft_run.HERE / 'config.json'):
        inv.add(path)
    inputs = ordered(all_inputs(prep) | set(pool_subset(pool_inputs(inv, cid), cid)))
    srcs, overflow = checked_programs(inv, case) if cid in program_tasks else ([], [])
    seeds = [repr(x) for x in ft_run.base_inputs(case, 'vibepass_half')]
    with execution_root(root):
        base = oracle.run_programs(case, 'tc', srcs, seeds, 'base') if srcs else {}
        base_put = oracle.run_programs(case, 'put', [case['source']], seeds, 'base')['p0'] if seeds else []
        valid = []
        for i in range(len(srcs)):
            n = f'p{i}'
            if i in overflow:
                continue
            vals = [iorel.value(o) for o in base[n]]
            pairs = [(a, b) for a, b in zip(map(iorel.value, base_put), vals) if a is not None]
            if pairs and all(b is not None and same(a, b) for a, b in pairs):
                valid.append(i)
        put = oracle.run_programs(case, 'put', [case['source']], inputs, 'inputs')['p0']
        outputs = oracle.run_programs(case, 'tc_valid', [srcs[i] for i in valid], inputs, 'inputs')
    rows = {}
    for j, lit in enumerate(inputs):
        progs = [outputs[f'p{i}'][j] for i in range(len(valid))]
        v, c = raw_votes(put[j], progs)
        rows[lit] = dict(put=put[j], programs={f'p{i}': o for i, o in zip(valid, progs)}, vote=v, consensus=c)
    inv.tree(root / 'exec' / cid)
    record = dict(case_id=cid, planned_programs=bool(srcs), valid_programs=valid, context_overflow=overflow,
                  base_inputs=seeds, base_put=base_put, base_programs=base, inputs=rows,
                  input_sha256=digest(inputs))
    record['artifact_sha256'] = inv.finish()
    immutable(root / 'tasks' / f'{cid}.json', json.loads(json.dumps(record)))
    return dict(case_id=cid, inputs=len(inputs), valid_programs=len(valid), context_overflow=len(overflow),
                vote_tests=sum(r['vote'] is not None for r in rows.values()),
                consensus_tests=sum(r['consensus'] is not None for r in rows.values()),
                put_exception_inputs=sum(r['put'][0] in ('exception', 'timeout') for r in rows.values()))


def execute(tasks=None):
    inv = Inventory()
    state = status(inv, tasks)
    if not state['complete']:
        print(json.dumps(dict(status=state, refused='planned records incomplete'), indent=2))
        return 1
    cohort, programs = planned(inv)
    wanted = cohort if tasks is None else [cid for cid in cohort if cid in tasks]
    prepared = inv.read(select.OUT / 'prepared.json')
    root = OUT if tasks is None else OUT / 'smoke' / hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    summaries = []
    for cid in wanted:
        # A per-task inventory remains stable when unrelated upstream records arrive.
        task_inv = Inventory()
        for p in (SPLIT, oracle.QUESTIONS, select.OUT / 'prepared.json'):
            task_inv.add(p)
        case = tool_cases(task_inv, [cid])[cid]
        summaries.append(execute_case(task_inv, case, prepared[cid], programs, root))
        print(json.dumps(summaries[-1]), flush=True)
    name = 'execution.json' if tasks is None else 'execution_' + '_'.join(wanted) + '.json'
    immutable(root / name, dict(tasks=wanted, smoke=tasks is not None, rows=summaries))
    return 0


def random3(items):
    return itertools.combinations(items, min(3, len(items)))


def kind_matched(items, picked):
    counts = collections.Counter(it['kind'] for it in picked)
    groups = [itertools.combinations([it for it in items if it['kind'] == k], n) for k, n in sorted(counts.items())]
    return (tuple(itertools.chain.from_iterable(g)) for g in itertools.product(*groups))


def count_matched(universe, n, seed, exact_max=EXACT_MAX, draws=DRAWS):
    universe = ordered(universe)
    if not 0 <= n <= len(universe):
        raise ValueError(f'cannot draw {n} distinct inputs from {len(universe)}')
    total = math.comb(len(universe), n)
    if total <= exact_max:
        return dict(method='exact', subsets=total, N=len(universe), n=n), itertools.combinations(universe, n)
    rng = random.Random(seed)
    return dict(method='seeded_draws', subsets=total, draws=draws, seed=seed, N=len(universe), n=n), \
        (tuple(rng.sample(universe, n)) for _ in range(draws))


def selections(inv, case, prep, pool):
    cid = case['case_id']
    menus = {a: prep.get('menus', {}).get(a, {}).get('items', []) for a in select.ARMS}
    picked, usage = {}, {}
    for a in select.ARMS:
        items = menus[a]
        if 'error' in prep or not items:
            picked[a], usage[a] = [], dict(calls=0, input_tokens=0, output_tokens=0, parsed=False)
            continue
        rec = inv.read(select.OUT / 'calls' / cid / f'{a}.json')
        msgs = select.prompt(task_view(case), case, items, a)
        if rec.get('prompt_sha256') != hashlib.sha256(json.dumps(msgs, sort_keys=True).encode()).hexdigest():
            raise ValueError('v47 prompt digest differs: ' + cid + '/' + a)
        ids = select.parse_picks(rec['text'], items)
        picked[a] = [it for it in items if it['id'] in ids]
        usage[a] = dict(calls=1, input_tokens=rec.get('input_tokens'), output_tokens=rec.get('output_tokens'),
                        parsed=bool(ids), picks=ids)
    items = menus['spec+code']
    code = item_inputs(prep, picked['spec+code'])
    heur = [next(it for it in items if it['kind'] == k) for k in PRIORITY if any(it['kind'] == k for it in items)][:3]
    fixed = dict(llm_code=code, llm_spec=item_inputs(prep, picked['spec-only']),
                 first3=item_inputs(prep, items[:3]), heuristic=item_inputs(prep, heur), all_menu=item_inputs(prep, items))
    choices = {a: (dict(method='fixed', draws=1), iter([u])) for a, u in fixed.items()}
    for a, batches in (('random3', random3(items)), ('kind_matched', kind_matched(items, picked['spec+code']))):
        choices[a] = (dict(method='exact'), (item_inputs(prep, batch) for batch in batches))
    for a, u in (('menu_matched', fixed['all_menu']), ('pool_matched', pool)):
        choices[a] = count_matched(u, len(code), f'v48/{a}/{cid}')
    return choices, usage


def metric(inputs, rows, labels, rule, cap):
    tests = emitted(inputs, rows, rule, cap)
    correct = sum(labels[lit][rule] == 'confirmed' for lit in tests)
    fa = len(tests) - correct
    return dict(correct_assertions=correct, confirmed_tasks=int(correct > 0), fa_tests=fa, fa_tasks=int(fa > 0),
                unconfirmed=sum(labels[lit][rule] == 'unconfirmed' for lit in tests), tests=len(tests),
                put_exception_inputs=sum(rows[lit]['put'][0] in ('exception', 'timeout') for lit in set(inputs)))


def expectation(batches, rows, labels):
    sums = {rule: {mode: collections.Counter() for mode in ('capped', 'uncapped')} for rule in ('vote', 'consensus')}
    count = 0
    for inputs in batches:
        count += 1
        for rule in sums:
            for mode, cap in (('capped', 20), ('uncapped', None)):
                sums[rule][mode].update(metric(inputs, rows, labels, rule, cap))
    if not count:
        raise ValueError('empty control enumeration')
    return count, {r: {m: {k: s[k] / count for k in METRICS} for m, s in modes.items()} for r, modes in sums.items()}


def judge(value, contract, ref, put, official_exposes):
    if contract[0] != 'ok' or ref is None or value is None or not same(value, ref):
        return 'fa'
    return 'confirmed' if put is not None and not same(put, ref) and official_exposes() else 'unconfirmed'


def decomposition(inputs, rows, truth, valid_programs):
    inputs = set(inputs)
    exposing = {lit for lit in inputs if truth[lit]['exposing']}
    common = bool(exposing) and all(all(iorel.value(o) is not None and same(iorel.value(o), iorel.value(rows[lit]['put']))
                                                    for o in rows[lit]['programs'].values()) for lit in exposing)
    vote_miss = [lit for lit in ordered(exposing) if any(iorel.value(o) is not None and same(iorel.value(o), truth[lit]['ref'])
                                             for o in rows[lit]['programs'].values())
                 and rows[lit]['vote'] is not None and not same(iorel.value(rows[lit]['vote']), truth[lit]['ref'])]
    wrong = [lit for lit in emitted(inputs, rows, cap=None) if truth[lit]['ref'] is None
             or not same(iorel.value(rows[lit]['vote']), truth[lit]['ref'])]
    splits = {}
    for mode, cap in (('capped', 20), ('uncapped', None)):
        split = collections.Counter()
        for lit in emitted(inputs, rows, cap=cap):
            t = truth[lit]
            if t['vote'] == 'confirmed':
                continue
            if not t['valid']:
                split['invalid_input'] += 1
            elif t['ref'] is None or iorel.value(rows[lit]['put']) is None:
                split['unresolved_output'] += 1
            elif same(iorel.value(rows[lit]['put']), t['ref']):
                split['put_right'] += 1
            elif not same(iorel.value(rows[lit]['vote']), t['ref']):
                split['put_wrong_wrong_value'] += 1
            else:
                split['unconfirmed_official'] += 1
        splits[mode] = dict(split)
    return dict(a_no_exposing_input=not exposing, b_common_mode=common and bool(valid_programs),
                c_vote_wrong=vote_miss, d_emitted_wrong_value=wrong, e_no_valid_program=not valid_programs,
                exposing_inputs=len(exposing), fa_split=splits, flags_may_overlap=True)


def reference_truth(inv, case, record, official):
    cid, rows = case['case_id'], record['inputs']
    pool = pool_inputs(inv, cid)
    # load_ref verifies the frozen v41 job; it never writes to v41.
    for name in ('job.json', 'result.json'):
        inv.add(iorel.OUT / 'cases' / cid / 'ref' / name)
    rr = oracle.mutoracle.load_ref(case, pool)
    raw = {lit: (rr['contract'][i], rr['ref'][i]) for i, lit in enumerate(pool) if lit in rows}
    new = ordered(set(rows) - set(pool))
    if new:
        ref = case['reference']
        generated = iorel.run_batch(OUT / 'references' / cid / 'generated',
                                    {'contract': ref['contract'], 'ref': ref['source']}, ref['entry'], new)
        inv.tree(OUT / 'references' / cid)
        raw.update({lit: (generated['contract'][i], generated['ref'][i]) for i, lit in enumerate(new)})
    truth = {}
    for lit, row in rows.items():
        contract, ref_raw = raw[lit]
        ref, put = iorel.value(ref_raw), iorel.value(row['put'])
        cache = []

        def exposes():
            if not cache:
                cache.append(iorel.official_exposes(official, case, lit))
            return cache[0]

        # Diagnostic reach also requires the official path, independent of whether a vote exists.
        exposing = contract[0] == 'ok' and put is not None and ref is not None and not same(put, ref) and exposes()
        truth[lit] = dict(valid=contract[0] == 'ok', ref=ref, exposing=exposing,
                          **{rule: judge(iorel.value(row[rule]), contract, ref, put, exposes) for rule in ('vote', 'consensus')})
    return truth


def aggregate(rows, common):
    result = {}
    for arm in rows[0]['arms']:
        result[arm] = {}
        for rule in ('vote', 'consensus'):
            result[arm][rule] = {}
            for mode in ('capped', 'uncapped'):
                totals = {k: sum(r['arms'][arm][rule][mode][k] for r in rows) for k in METRICS}
                totals['confirmed_tasks_33'] = totals['confirmed_tasks']
                totals['confirmed_tasks_31'] = sum(r['arms'][arm][rule][mode]['confirmed_tasks'] for r in rows if r['case_id'] in common)
                totals['precision'] = totals['correct_assertions'] / totals['tests'] if totals['tests'] else None
                result[arm][rule][mode] = totals
    return result


def decision(arms):
    a = {k: v['vote']['capped'] for k, v in arms.items()}
    tests = {k: a['llm_code']['confirmed_tasks'] >= a[k]['confirmed_tasks'] + margin
             for k, margin in (('random3', 3), ('menu_matched', 3), ('pool_matched', 3), ('kind_matched', 2), ('heuristic', 2))}
    tests['fa_vs_random3'] = a['llm_code']['fa_tests'] <= a['random3']['fa_tests']
    return dict(verdict='GO' if all(tests.values()) else 'NO-GO', checks=tests)


def score():
    inv = Inventory()
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        state = status(inv)
        missing = [cid for cid in planned(inv)[0] if not (OUT / 'tasks' / f'{cid}.json').is_file()]
        if not state['complete'] or missing:
            result = dict(verdict='incomplete', status=state, missing_execution=missing)
            (OUT / 'score_incomplete.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result, indent=2))
            return 1
        cohort, common = planned(inv)
        prep = inv.read(select.OUT / 'prepared.json')
        cases = tool_cases(inv, cohort)
        records, arm_choices, usage = {}, {}, {}
        # Verify every execution inventory and all pick digests before loading any reference.
        for cid in cohort:
            record = inv.read(OUT / 'tasks' / f'{cid}.json')
            for name, sha in record['artifact_sha256'].items():
                p = inv.add(REPO / name)
                if inv.files[str(p.relative_to(REPO))] != sha:
                    raise ValueError('execution input changed: ' + name)
            checked_programs(inv, cases[cid]) if cid in common else None
            expected = ordered(all_inputs(prep[cid]) | set(pool_subset(pool_inputs(inv, cid), cid)))
            if set(record['inputs']) != set(expected) or record['input_sha256'] != digest(expected):
                raise ValueError('execution input set differs: ' + cid)
            records[cid] = record
            arm_choices[cid], usage[cid] = selections(inv, cases[cid], prep[cid], pool_subset(pool_inputs(inv, cid), cid))
        run = ft_run.FTRun('vibepass_half')
        for name in ('humaneval_mbpp_plus.jsonl', 'humaneval_mbpp.jsonl', 'tasks.json'):
            inv.add(DATA / name)
        official = Reference(run)
        official.root = OUT / 'references' / 'official'
        refs = {c['case_id']: c for c in run.cases}
        rows = []
        for cid in cohort:
            record = records[cid]
            truth = reference_truth(inv, refs[cid], record, official)
            arms, controls = {}, {}
            for arm, (method, batches) in arm_choices[cid].items():
                count, arms[arm] = expectation(batches, record['inputs'], truth)
                controls[arm] = dict(method, evaluated=count)
            for arm in arms.values():
                for rule in arm.values():
                    for m in rule.values():
                        m['precision'] = m['correct_assertions'] / m['tests'] if m['tests'] else None
            selected = selections(inv, cases[cid], prep[cid], pool_subset(pool_inputs(inv, cid), cid))[0]
            failures = {arm: decomposition(next(selected[arm][1]), record['inputs'], truth, record['valid_programs'])
                        for arm in ('all_menu', 'llm_code')}
            rows.append(dict(case_id=cid, valid_programs=record['valid_programs'], arms=arms, controls=controls,
                             selection_usage=usage[cid], failures=failures))
        totals = aggregate(rows, common)
        program_usage = [inv.read(oracle.OUT / 'programs' / 'tc' / cid / f'{i}.json') for cid in sorted(common, key=int)
                         for i in range(oracle.NPROG)]
        def tokens(recs):
            return {k: sum(r.get(k) or 0 for r in recs) for k in ('input_tokens', 'output_tokens')} | \
                dict(calls=len(recs), unknown_input_tokens=sum(r.get('input_tokens') is None for r in recs))
        pick_usage = {a: tokens([r[a] for r in usage.values() if r[a]['calls']]) for a in select.ARMS}
        inv.tree(OUT / 'exec')
        inv.tree(OUT / 'references')
        per_arm_usage = {a: dict(calls=0, input_tokens=0, output_tokens=0) for a in totals}
        per_arm_usage.update(llm_code=pick_usage['spec+code'], llm_spec=pick_usage['spec-only'],
                             kind_matched=pick_usage['spec+code'])
        summary = dict(tasks=len(rows), common_tasks=len(common), arms=totals, decision=decision(totals),
                       upstream=dict(shared_tc=tokens(program_usage), picks=pick_usage,
                                     per_arm_pick_calls=per_arm_usage,
                                     note='Other controls use no picks; pool_matched + tc is TC-full-style, not complete TC-full.'),
                       exact_max=EXACT_MAX, seeded_draws=DRAWS)
        result = dict(summary=summary, rows=rows, artifact_sha256=inv.finish())
        immutable(OUT / 'score.json', result)
        print(json.dumps(summary, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        result = dict(verdict='incomplete', error=f'{type(exc).__name__}: {exc}', artifact_sha256=dict(sorted(inv.files.items())))
        (OUT / 'score_incomplete.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=('status', 'execute', 'score'))
    ap.add_argument('--tasks', help='execute engineering smoke only, e.g. 3,46')
    args = ap.parse_args()
    if args.tasks is not None and args.command != 'execute':
        ap.error('--tasks is restricted to execute smoke')
    if args.command == 'status':
        print(json.dumps(status(), indent=2))
        return 0
    if args.command == 'execute':
        return execute(args.tasks.split(',') if args.tasks is not None else None)
    return score()


if __name__ == '__main__':
    raise SystemExit(main())
