"""v41 observed input->output relations: CPU ceiling (see PREREG.md). No LLM. Usage (repo root):
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v41_iorel/iorel.py

Tool side (PUT + public examples only): Hypothesis sampling inferred from the public example values, metamorphic
transformations of each sample, outcome relation per pair, minority categories -> shown package.
Ceiling side (references + evaluator contract, only here): which inputs expose PUT != reference.
"""
import hashlib
import json
import math
import random
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import hypothesis
from hypothesis import HealthCheck, Phase, given, settings, strategies as st

from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_concepts, ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.hypothesis_replay import freeze_local_constants
from trickcatcher_linefacts.pipelines.v34_ftplacebo.chain_inputs import parse_literal, typed_value
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, same
from trickcatcher_linefacts.pipelines.v34_ftplacebo.gen_inputs import sandbox
from trickcatcher_linefacts.pipelines.v34_ftplacebo.paths import CONFIG

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v41_iorel'
WORKER = ft_run.HERE / 'ft_worker.py'
N = 300
MAX_LEN = 30
MINORITY = 0.25
MAX_RELATIONS = 8
WITNESSES_PER_RELATION = 2
MAJORITY = 0.5
GATE_C2 = 17
GATE_LIFT = 2.0
MAX_TIMEOUTS = 200
OFFICIAL_EXPOSING_RECHECK = 20


# ---- sampling (public examples only) ----------------------------------------------------------------------------
def is_int(v):
    return type(v) is int


def strategy_for(values):
    """Hypothesis strategy for one argument position, inferred from the public example values at that position."""
    if values and all(type(v) is bool for v in values):
        return st.booleans()
    if values and all(is_int(v) for v in values):
        lo, hi = min(values), max(values)
        lower = 1 if lo >= 1 else 0 if lo >= 0 else min(2 * lo, lo - 10)
        return st.integers(lower, max(2 * hi, hi + 10))
    if values and all(type(v) in (int, float) and type(v) is not bool for v in values):
        lo, hi = min(values), max(values)
        lower = 0.0 if lo >= 0 else min(2 * lo, lo - 10)
        return st.floats(lower, max(2 * hi, hi + 10), allow_nan=False, allow_infinity=False)
    if values and all(type(v) is str for v in values):
        alphabet = sorted(set(''.join(values))) or ['a', 'b']
        lens = [len(v) for v in values]
        return st.text(alphabet=alphabet, min_size=min(lens), max_size=max(min(lens), min(2 * max(lens) + 2, MAX_LEN)))
    if values and all(type(v) in (list, tuple) for v in values):
        elems = [x for v in values for x in v]
        elem = strategy_for(elems) if elems else st.integers(0, 10)
        lens = [len(v) for v in values]
        lists = st.lists(elem, min_size=min(lens), max_size=max(min(lens), min(2 * max(lens) + 2, MAX_LEN)))
        return lists.map(tuple) if all(type(v) is tuple for v in values) else lists
    return st.sampled_from(values) if values else st.none()


def sample(seeds, n=N):
    freeze_local_constants()  # Hypothesis would otherwise mine literals from imported repo modules
    arity = len(seeds[0])
    strategy = st.tuples(*[strategy_for([s[i] for s in seeds if len(s) == arity]) for i in range(arity)])
    out, seen = [], set()

    @settings(max_examples=n, derandomize=True, database=None, phases=[Phase.generate], deadline=None,
              suppress_health_check=list(HealthCheck))
    @given(strategy)
    def collect(args):
        key = repr(args)
        if key not in seen:
            seen.add(key)
            out.append(args)

    collect()
    return out


# ---- transformations (public examples only) ---------------------------------------------------------------------
def profile(seeds):
    """Per position: public integer lower bound (if every public number is >= 0 / >= 1), min length, example chars."""
    prof = []
    for i in range(len(seeds[0])):
        vals = [s[i] for s in seeds]
        nums = [x for v in vals for x in (v if type(v) in (list, tuple) else [v]) if is_int(x)]
        lens = [len(v) for v in vals if type(v) in (list, tuple, str)]
        chars = sorted(set(''.join(v for v in vals if type(v) is str)))
        lower = 1 if nums and min(nums) >= 1 else 0 if nums and min(nums) >= 0 else None
        prof.append(dict(lower=lower, min_len=min(lens) if lens else 0, chars=chars))
    return prof


def transforms(x, prof):
    """(name, T(x)) for one-position metamorphic transformations; T(x) == x is skipped."""
    out = []
    rng = random.Random(hashlib.sha256(repr(x).encode()).hexdigest())
    for i, v in enumerate(x):
        p = prof[i]
        cand = []
        if type(v) is list:
            cand += [('reverse', v[::-1]), ('shuffle', rng.sample(v, len(v)))]
            try:
                cand.append(('sort', sorted(v)))
            except TypeError:
                pass
            if v and all(is_int(e) for e in v):
                cand += [('append_max+1', v + [max(v) + 1]), ('prepend_max+1', [max(v) + 1] + v),
                         ('append_low', v + [p['lower'] if p['lower'] is not None else min(v)])]
            if len(v) - 1 >= p['min_len']:
                cand.append(('drop_last', v[:-1]))
            if 0 < len(v) and 2 * len(v) <= MAX_LEN:
                cand.append(('duplicate', v + v))
        elif is_int(v):
            cand.append(('+1', v + 1))
            if p['lower'] is None or v - 1 >= p['lower']:
                cand.append(('-1', v - 1))
        elif type(v) is str:
            cand.append(('reverse', v[::-1]))
            if p['chars']:
                cand.append(('append_char', v + p['chars'][0]))
            if len(v) - 1 >= p['min_len']:
                cand.append(('drop_last', v[:-1]))
        for name, nv in cand:
            y = x[:i] + (nv,) + x[i + 1:]
            if y != x:
                out.append((f'arg{i}:{name}', y))
    return out


# ---- execution --------------------------------------------------------------------------------------------------
def run_batch(directory, sources, entry, inputs, timeout=3600):
    """Batch execution cached by job content (a changed job never reuses an old result)."""
    directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory / 'job.json', directory / 'result.json'
    job = dict(sources=sources, order=list(sources), entry=entry, inputs=inputs, per_call_timeout=1, max_timeouts=MAX_TIMEOUTS)
    if op.exists() and jp.exists() and json.loads(jp.read_text()) == job:
        return json.loads(op.read_text())
    op.unlink(missing_ok=True)
    jp.write_text(json.dumps(job))
    return sandbox(CONFIG['V4_PYTHON'], WORKER, jp, op, timeout)


def value(o):
    """ft_worker outcome -> comparable observation, or None (timeout / skipped / unparseable)."""
    if not o or o[0] == 'exception':
        return ('exception', o[1]) if o else None
    if o[0] != 'ok':
        return None
    try:
        return ('ok', typed_value(parse_literal(o[1], output=True)))
    except (ValueError, TypeError, SyntaxError, RecursionError):
        return None


def category(a, b):
    if a is None or b is None:
        return None
    if a[0] == 'exception' or b[0] == 'exception':
        return 'equal' if a == b else 'exception_differs'
    if same(a, b):
        return 'equal'
    (ta, va), (tb, vb) = a[1], b[1]  # typed_value: (type name, payload); containers hold a tuple of typed items
    if ta in ('int', 'float') and tb in ('int', 'float'):  # bool is its own type name -> 'changed'
        return 'equal' if va == vb else 'increase' if vb > va else 'decrease'
    if ta in ('list', 'tuple', 'str') and tb in ('list', 'tuple', 'str') and len(va) != len(vb):
        return 'increase' if len(vb) > len(va) else 'decrease'
    return 'changed'


def tool(case):
    """Tool side for one case: no reference. Returns pairs, relations and the shown package."""
    cid = case['case_id']
    seeds = ft_run.base_inputs(case, 'vibepass_half')
    assert all(type(v) not in (tuple, float) for s in seeds for v in s), 'v41 transforms cover list/int/str/bool args only'
    domain = ft_concepts.domain_profile(seeds)
    xs = [x for x in sample(seeds) if ft_concepts.in_domain(x, domain)]
    prof = profile(seeds)
    pairs = [(xi, name, y) for xi, x in enumerate(xs) for name, y in transforms(x, prof) if ft_concepts.in_domain(y, domain)]
    inputs = sorted({repr(x) for x in xs} | {repr(y) for _, _, y in pairs})
    index = {lit: k for k, lit in enumerate(inputs)}
    res = run_batch(OUT / 'cases' / cid / 'put', {'put': case['source']}, case['entry'], inputs)
    put = [value(o) for o in res['put']]
    rel = {}
    for xi, name, y in pairs:
        c = category(put[index[repr(xs[xi])]], put[index[repr(y)]])
        if c is not None:
            rel.setdefault(name, []).append((c, repr(xs[xi]), repr(y)))
    relations = []
    for name, rows in rel.items():
        counts = {}
        for c, _, _ in rows:
            counts[c] = counts.get(c, 0) + 1
        total = len(rows)
        minority = {c: n for c, n in counts.items() if n / total <= MINORITY}
        if not minority or max(counts.values()) / total < MAJORITY:
            continue
        # <= 2 witness pairs per relation, rarest minority category first (first pairs = simplest Hypothesis inputs)
        witnesses, left = {}, WITNESSES_PER_RELATION
        for c in sorted(minority, key=lambda c: (minority[c], c)):
            take = [(x, y) for cc, x, y in rows if cc == c][:left]
            if take:
                witnesses[c] = take
                left -= len(take)
            if not left:
                break
        relations.append(dict(transform=name, pairs=total, counts=counts, min_share=min(minority.values()) / total,
                              witnesses=witnesses,
                              all_minority_inputs=sorted({v for cc, x, y in rows if cc in minority for v in (x, y)})))
    relations.sort(key=lambda r: (r['min_share'], r['transform']))
    shown = relations[:MAX_RELATIONS]
    return dict(case_id=cid, samples=len(xs), pairs=len(pairs), inputs=inputs, put=res['put'], relations=relations,
                timeouts=sum(o[0] == 'timeout' for o in res['put']), skipped=sum(o[0] == 'skipped' for o in res['put']),
                inputs_sha256=hashlib.sha256(json.dumps(inputs).encode()).hexdigest(),
                shown=[{k: v for k, v in r.items() if k != 'all_minority_inputs'} for r in shown],
                shown_inputs=sorted({v for r in shown for ws in r['witnesses'].values() for x, y in ws for v in (x, y)}))


# ---- ceiling (references only here) -----------------------------------------------------------------------------
def exposure(case, t):
    ref = case['reference']
    res = run_batch(OUT / 'cases' / case['case_id'] / 'ref', {'contract': ref['contract'], 'ref': ref['source']},
                    ref['entry'], t['inputs'])
    exposing, valid = set(), set()
    for k, lit in enumerate(t['inputs']):
        if res['contract'][k][0] != 'ok':
            continue
        valid.add(lit)
        a, b = value(t['put'][k]), value(res['ref'][k])
        if a is not None and b is not None and not same(a, b):
            exposing.add(lit)
    return exposing, valid


def official_put(official, case, lit):
    r = official._run(case['source'], case['entry'], lit)
    if r.get('status') == 'exception':
        return ('exception', r['exception_type'])
    if r.get('status') == 'ok' and r.get('output_repr') is not None:
        return ('ok', typed_value(parse_literal(r['output_repr'], output=True)))
    return None


def official_exposes(official, case, lit):
    """Official per-input path (fresh flow_worker process per input) for contract, PUT and reference."""
    if not official.contract_valid(case, lit):
        return False
    a, b = official_put(official, case, lit), official(case, lit)
    return a is not None and b is not None and not same(a, b)


def random_k(n, e, k):
    """Exact chance that k inputs drawn without replacement from n (e exposing) contain >= 1 exposing input."""
    if k <= 0 or e <= 0:
        return 0.0
    return 1.0 - math.comb(n - e, k) / math.comb(n, k) if n - e >= k else 1.0


def main():
    run = ft_run.FTRun('vibepass_half')
    cases = run.cases
    if any(c['reference'].get('kind') == 'fixture' or not c['reference'].get('contract') for c in cases):
        raise SystemExit('v41 batch reference expects VibePass references with a contract')

    def safe_tool(case):
        try:
            return tool(case)
        except Exception as exc:  # recorded, not fatal
            return dict(case_id=case['case_id'], error=f'{type(exc).__name__}: {exc}'[:300])
    freeze_local_constants()
    with ThreadPoolExecutor(6) as pool:
        tools = {t['case_id']: t for t in pool.map(safe_tool, cases)}
    official = Reference(run)
    official.root = OUT / 'official'
    rows, agree = [], [0, 0]
    for case in cases:
        t = tools[case['case_id']]
        if 'error' in t:
            rows.append(dict(case_id=case['case_id'], error=t['error'], c1=False, c2=False, random_k=0.0))
            continue
        try:
            exposing, valid = exposure(case, t)
        except Exception as exc:  # recorded, not fatal
            rows.append(dict(case_id=case['case_id'], error=f'exposure: {type(exc).__name__}: {exc}'[:300], c1=False, c2=False, random_k=0.0))
            continue
        shown = set(t['shown_inputs'])
        checked = sorted(shown | set(sorted(exposing)[:OFFICIAL_EXPOSING_RECHECK]))
        confirmed, official_only = set(), set()
        try:
            for lit in checked:
                ok = official_exposes(official, case, lit)
                agree[0] += ok == (lit in exposing)
                agree[1] += 1
                if ok and lit in exposing:  # batch AND official, so C2, random-k and lift rest on the same inputs
                    confirmed.add(lit)
                elif ok:
                    official_only.add(lit)
        except Exception as exc:  # recorded, not fatal
            rows.append(dict(case_id=case['case_id'], error=f'official: {type(exc).__name__}: {exc}'[:300], c1=False, c2=False,
                             random_k=0.0))
            continue
        minority_all = {v for r in t['relations'] for v in r['all_minority_inputs']}
        n, e, k = len(t['inputs']), len(exposing), len(shown)
        shown_exp = exposing & shown
        lift = ((len(shown_exp) / k) / (e / n) if k else 0.0) if e else None  # empty package with C1 -> lift 0
        valid_shown = valid & shown
        lift_valid = ((len(shown_exp) / len(valid_shown)) / (e / len(valid)) if valid_shown else 0.0) if e else None
        rows.append(dict(case_id=case['case_id'], samples=t['samples'], pairs=t['pairs'], inputs=n, valid_inputs=len(valid),
                         timeouts=t['timeouts'], skipped=t['skipped'], exposing_batch=e, relations=len(t['relations']),
                         shown_relations=len(t['shown']), shown_inputs=k, shown_valid=len(valid_shown),
                         shown_exposing_batch=len(shown_exp), shown_exposing_official=len(confirmed & shown),
                         minority_all_exposing_batch=len(exposing & minority_all), official_only_exposing=len(official_only),
                         c1=bool(confirmed), c2=bool(confirmed & shown),
                         c2_uncapped_batch=bool(exposing & minority_all), random_k=round(random_k(n, e, k), 4),
                         lift=lift, lift_valid=lift_valid, inputs_sha256=t['inputs_sha256']))
    ok_rows = [r for r in rows if 'error' not in r]
    c2 = sum(r['c2'] for r in rows)
    e_random = sum(r['random_k'] for r in rows)
    lifts = [r['lift'] for r in ok_rows if r['c1'] and r['lift'] is not None]
    lifts_valid = [r['lift_valid'] for r in ok_rows if r['c1'] and r['lift_valid'] is not None]
    median_lift = statistics.median(lifts) if lifts else 0.0
    summary = dict(n=len(rows), errors=len(rows) - len(ok_rows), c1=sum(r['c1'] for r in rows), c2=c2,
                   c2_uncapped_batch=sum(r.get('c2_uncapped_batch', False) for r in rows), expected_random_k_c2=round(e_random, 2),
                   median_lift=round(median_lift, 3), median_lift_valid=round(statistics.median(lifts_valid), 3) if lifts_valid else None,
                   pooled_base_exposure_rate=round(sum(r['exposing_batch'] for r in ok_rows) / sum(r['inputs'] for r in ok_rows), 4),
                   validity_rate=round(sum(r['valid_inputs'] for r in ok_rows) / sum(r['inputs'] for r in ok_rows), 3),
                   shown_valid_share=round(sum(r['shown_valid'] for r in ok_rows) / max(1, sum(r['shown_inputs'] for r in ok_rows)), 3),
                   official_agreement=f'{agree[0]}/{agree[1]}', timeouts=sum(r.get('timeouts', 0) for r in ok_rows),
                   skipped=sum(r.get('skipped', 0) for r in ok_rows), hypothesis=hypothesis.__version__,
                   template_pool_c1_v35=17,
                   verdict='go' if c2 >= GATE_C2 and c2 > e_random and median_lift >= GATE_LIFT else 'no-go')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'ceiling.json').write_text(json.dumps(dict(summary=summary, rows=rows), indent=1) + '\n')
    (OUT / 'packages.json').write_text(json.dumps({k: dict(shown=v.get('shown'), error=v.get('error')) for k, v in tools.items()}, indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
