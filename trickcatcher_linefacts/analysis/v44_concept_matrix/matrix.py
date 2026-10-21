"""v44 concept taxonomy x tool method matrix (see PREREG.md). CPU only, no LLM. Usage (repo root):
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v44_concept_matrix/matrix.py

Tool side per kind: instances -> flagged inputs (PUT, public examples, spec text only; kinds 3 and 4 use the reference
only to pick the *accurate* relation, standing in for a correct LLM). Ceiling side: exposure with references, batch AND
official re-check (v41 functions).
"""
import ast
import hashlib
import json
import re
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from trickcatcher_linefacts.analysis.v41_iorel import iorel
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_concepts, ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_run import Reference, same
from trickcatcher_linefacts.pipelines.v34_ftplacebo.gen_inputs import sandbox
from trickcatcher_linefacts.pipelines.v34_ftplacebo.hypothesis_replay import freeze_local_constants
from trickcatcher_linefacts.pipelines.v34_ftplacebo.paths import CONFIG

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'out' / 'analysis' / 'v44_concept_matrix'
MUTORACLE = HERE.parents[1] / 'out' / 'analysis' / 'v42_mutoracle'
V34 = HERE.parents[1] / 'out' / 'pipelines' / 'v34_ftplacebo' / 'humaneval' / 'faulttemplate' / 'openrouter' / 'vibepass_half'
K = 32
BASE_SAMPLES = 40
MIN_MR_PAIRS = 10
MIN_PROP_INPUTS = 20
KINDS = ('class', 'boundary', 'metamorphic', 'property', 'coverage', 'mutation')
INPUT_KINDS = ('class', 'boundary', 'coverage', 'mutation')
ORACLE_KINDS = ('metamorphic', 'property')
CANDIDATE_SHARE = 0.75
GATE_UNION = 22
GATE_MARGIN = 3


# ---- shared helpers ---------------------------------------------------------------------------------------------
def literal(o):
    """Raw Python value of an ft_worker 'ok' outcome, or None."""
    if not o or o[0] != 'ok':
        return None
    try:
        return ast.literal_eval(o[1])
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None


def num(v):
    return type(v) in (int, float)


def numlist(v):
    return type(v) in (list, tuple) and bool(v) and all(num(e) for e in v)


def param_names(signature):
    tree = ast.parse('def ' + signature.split('->')[0].strip() + ': pass')
    return [a.arg for a in tree.body[0].args.args if a.arg != 'self']


NUMBER = r'-?\d+(?:\s*\*\s*10\s*\^\s*\d+)?(?:\s*\^\s*\d+)?'


def number(text):
    text = re.sub(r'\s', '', text)
    m = re.fullmatch(r'(-?)(\d+)(?:\*10\^(\d+))?(?:\^(\d+))?', text)
    if not m:
        return None
    sign, a, e10, p = m.groups()
    v = int(a)
    if p:
        v = v ** int(p)
    if e10:
        v = v * 10 ** int(e10)
    return -v if sign else v


def constraints(spec, names):
    """{(arg, 'length'|'elem'|'elem2'|'value'): (lo, hi)} parsed from the spec text (inclusive bounds)."""
    out = {}
    target = r'[A-Za-z_][\w]*(?:\.length|\[i\]\[j\]|\[i\])?'
    spec = re.sub(rf'(<=|<)\s*[A-Za-z_]\w*\s*==\s*({target})', r'\1 \2', spec)  # a <= n == x.length <= b
    pat = re.compile(rf'({NUMBER})\s*(<=|<)\s*({target}(?:\s*,\s*{target})*)\s*(<=|<)\s*({NUMBER})')
    for m in pat.finditer(spec):
        lo, op1, target, op2, hi = m.groups()
        lo, hi = number(lo), number(hi)
        if lo is None or hi is None:
            continue
        for t in [s.strip() for s in target.split(',')]:
            base = re.match(r'[A-Za-z_]\w*', t).group(0)
            if base not in names:
                continue
            kind = 'length' if t.endswith('.length') else 'elem2' if t.endswith('[i][j]') else 'elem' if t.endswith('[i]') else 'value'
            out[(names.index(base), kind)] = (lo + (op1 == '<'), hi - (op2 == '<'))
    return out


def run_inputs(case, name, inputs):
    """PUT + contract/reference batch on new inputs -> (put outcomes, contract outcomes, ref outcomes)."""
    ref = case['reference']
    put = iorel.run_batch(OUT / 'cases' / case['case_id'] / name / 'put', {'put': case['source']}, case['entry'], inputs)['put']
    rr = iorel.run_batch(OUT / 'cases' / case['case_id'] / name / 'ref', {'contract': ref['contract'], 'ref': ref['source']},
                         ref['entry'], inputs)
    return put, rr['contract'], rr['ref']


def exposing_set(inputs, put, contract, refo):
    exp, valid = set(), set()
    for k, lit in enumerate(inputs):
        if contract[k][0] != 'ok':
            continue
        valid.add(lit)
        a, b = iorel.value(put[k]), iorel.value(refo[k])
        if a is not None and b is not None and not same(a, b):
            exp.add(lit)
    return exp, valid


# ---- kind 1: input classes ----------------------------------------------------------------------------------------
def class_members(xs, prof, cons, seeds):
    maxlen = max([len(v) for s in seeds for v in s if type(v) in (list, str)] or [1])
    inst = {}
    for x in xs[:BASE_SAMPLES]:
        for i, v in enumerate(x):
            lo = cons.get((i, 'elem'), (prof[i]['lower'], None))[0]
            hi = cons.get((i, 'elem'), (None, None))[1]
            cand = []
            if type(v) is list and v:
                cand += [('singleton', [v[0]]), ('all_equal', [v[0]] * len(v)), ('many_duplicates', (v[:2] * len(v))[:len(v)])]
                try:
                    cand += [('sorted_asc', sorted(v)), ('sorted_desc', sorted(v, reverse=True))]
                    cand.append(('strictly_increasing', sorted(set(v))))
                except TypeError:
                    pass
                if all(iorel.is_int(e) for e in v):
                    if lo is not None:
                        cand.append(('contains_lower', v[:-1] + [lo]))
                    if hi is not None:
                        cand.append(('contains_upper', v[:-1] + [hi]))
                cand.append(('longest', (v * (2 * maxlen // len(v) + 2))[:min(2 * maxlen, iorel.MAX_LEN)]))
            elif type(v) is str and v:
                cand += [('repeated_char', v[0] * len(v)), ('sorted_chars', ''.join(sorted(v))),
                         ('palindrome', v[:15] + v[:15][::-1]), ('single_char', v[:1])]
            elif iorel.is_int(v):
                low = cons.get((i, 'value'), (prof[i]['lower'], None))[0]
                if low is not None:
                    cand += [('lower', low), ('lower+1', low + 1)]
            for name, nv in cand:
                y = x[:i] + (nv,) + x[i + 1:]
                if y != x:
                    inst.setdefault(f'arg{i}:{name}', []).append(repr(y))
    return {k: list(dict.fromkeys(v)) for k, v in inst.items()}


# ---- kind 2: boundary from spec constraints -------------------------------------------------------------------------
def boundary_members(xs, cons):
    inst = {}

    def put(name, y):
        inst.setdefault(name, []).append(repr(y))
    for x in xs[:BASE_SAMPLES]:
        for (i, kind), (lo, hi) in cons.items():
            if i >= len(x):
                continue
            v = x[i]
            if kind == 'length' and type(v) in (list, str) and v:
                for tag, L in (('len_min', lo), ('len_min+1', lo + 1)):
                    if 0 <= L <= iorel.MAX_LEN and L <= hi:
                        put(f'arg{i}:{tag}', x[:i] + ((v * (L // len(v) + 1))[:L],) + x[i + 1:])
            elif kind == 'elem' and type(v) is list and v and all(iorel.is_int(e) for e in v):
                for tag, nv in (('all_min', [lo] * len(v)), ('all_max', [hi] * len(v)), ('one_min', v[:-1] + [lo]), ('one_max', v[:-1] + [hi])):
                    put(f'arg{i}:elem_{tag}', x[:i] + (nv,) + x[i + 1:])
            elif kind == 'elem2' and type(v) is list and v and all(type(r) is list and r and all(iorel.is_int(e) for e in r) for r in v):
                for tag, bound in (('min', lo), ('max', hi)):
                    put(f'arg{i}:elem2_all_{tag}', x[:i] + ([[bound] * len(r) for r in v],) + x[i + 1:])
                    put(f'arg{i}:elem2_one_{tag}', x[:i] + ([r[:] for r in v[:-1]] + [v[-1][:-1] + [bound]],) + x[i + 1:])
            elif kind == 'value' and iorel.is_int(v):
                for tag, nv in (('min', lo), ('min+1', lo + 1), ('max', hi), ('max-1', hi - 1)):
                    if lo <= nv <= hi:
                        put(f'arg{i}:value_{tag}', x[:i] + (nv,) + x[i + 1:])
    return {k: [lit for lit in dict.fromkeys(v)] for k, v in inst.items()}


# ---- kind 3: metamorphic with the accurate predicate ----------------------------------------------------------------
PREDICATES = {'equal': {'equal'}, 'non_decreasing': {'equal', 'increase'}, 'non_increasing': {'equal', 'decrease'}}


def metamorphic(pairs, idx, put, contract, refo):
    by = {}
    for x, name, y in pairs:
        a, b = idx[x], idx[y]
        if contract[a][0] != 'ok' or contract[b][0] != 'ok':
            continue
        rc = iorel.category(iorel.value(refo[a]), iorel.value(refo[b]))
        pc = iorel.category(iorel.value(put[a]), iorel.value(put[b]))
        if rc is None:
            continue
        by.setdefault(name, []).append((rc, pc, x, y))
    inst = {}
    for name, rows in by.items():
        if len(rows) < MIN_MR_PAIRS:
            continue
        for pred, allowed in PREDICATES.items():
            if all(rc in allowed for rc, _, _, _ in rows):
                flagged = [v for rc, pc, x, y in rows if pc is not None and pc not in allowed for v in (x, y)]
                inst[f'{name}:{pred}'] = list(dict.fromkeys(flagged))
    return inst


# ---- kind 4: output properties with the accurate template -----------------------------------------------------------
def properties(args, out):
    """{name: bool} for the templates that apply to this (args, output)."""
    r = {}
    if num(out) and type(out) is not bool:
        r['out>=0'] = out >= 0
    for i, v in enumerate(args):
        if type(v) in (list, tuple, str):
            if num(out) and type(out) is not bool:
                r[f'out<=len(arg{i})'] = out <= len(v)
            if type(out) in (list, tuple, str):
                r[f'len(out)==len(arg{i})'] = len(out) == len(v)
        if numlist(v) and num(out) and type(out) is not bool:
            r[f'out<=sum(arg{i})'] = out <= sum(v)
            r[f'out<=max(arg{i})'] = out <= max(v)
            r[f'out>=min(arg{i})'] = out >= min(v)
        if type(v) in (list, tuple) and v:
            if all(type(e) is type(out) for e in v):  # True in [1, 2] / 2.0 in [2] must not count
                r[f'out in arg{i}'] = out in v
            if type(out) in (list, tuple):
                try:
                    r[f'set(out)<=set(arg{i})'] = set(out) <= set(v)
                except TypeError:
                    pass
    if type(out) in (list, tuple):
        try:
            r['out sorted'] = list(out) == sorted(out)
        except TypeError:
            pass
    return r


def output_properties(inputs, put, contract, refo):
    held, seen, viol = {}, {}, {}
    for k, lit in enumerate(inputs):
        if contract[k][0] != 'ok':
            continue
        ro = literal(refo[k])
        if ro is None:
            continue
        args = ast.literal_eval(lit)
        for name, ok in properties(args, ro).items():
            seen[name] = seen.get(name, 0) + 1
            held[name] = held.get(name, True) and ok
        po = literal(put[k])
        if po is not None:
            for name, ok in properties(args, po).items():
                if not ok:
                    viol.setdefault(name, []).append(lit)
    return {n: viol.get(n, []) for n in held if held[n] and seen[n] >= MIN_PROP_INPUTS}


# ---- kind 5: coverage arcs (coverage.py), universe = pool --------------------------------------------------------
def coverage_arcs(case, seeds, inputs):
    d = OUT / 'cases' / case['case_id'] / 'coverage'
    d.mkdir(parents=True, exist_ok=True)
    jp, op = d / 'job.json', d / 'result.json'
    lits = [repr(s) for s in seeds] + list(inputs)
    job = dict(source=case['source'], entry=case['entry'], inputs=lits, per_call_timeout=1)
    if not (op.exists() and jp.exists() and json.loads(jp.read_text()) == job):
        op.unlink(missing_ok=True)
        jp.write_text(json.dumps(job))
        sandbox(CONFIG['V4_PYTHON'], HERE / 'cov_worker.py', jp, op, 3600)
    res = json.loads(op.read_text())
    if not res.get('measured') or not any(res['arcs'][:len(seeds)]):
        raise RuntimeError('coverage: source not measured or public inputs produced no arcs')
    arcs = res['arcs']
    public = {tuple(a) for r in arcs[:len(seeds)] if r for a in r}
    inst = {}
    for lit, r in zip(inputs, arcs[len(seeds):]):
        for a in (r or []):
            if tuple(a) not in public:
                inst.setdefault(f'arc{a[0]}->{a[1]}', []).append(lit)
    return inst


# ---- kind 6: surviving mutants, outcomes reused read-only from v42_mutoracle ----------------------------------------
def mutation(case, inputs, put):
    base = MUTORACLE / 'cases' / case['case_id']
    outcomes = {}
    for d in sorted(base.glob('chunk*')):
        job = json.loads((d / 'job.json').read_text())
        if job['inputs'] != inputs:
            raise RuntimeError('v42_mutoracle inputs differ from the v41 pool')
        if (d / 'result.json').exists():
            outcomes.update({n: v for n, v in json.loads((d / 'result.json').read_text()).items() if n != 'put'})
        for sub in d.iterdir():
            if sub.is_dir() and (sub / 'result.json').exists():
                outcomes.update(json.loads((sub / 'result.json').read_text()))
    if not outcomes:
        raise RuntimeError('no v42_mutoracle mutant outcomes')
    pv = [iorel.value(o) for o in put]
    inst = {}
    for n in sorted(outcomes):
        flagged = [lit for lit, p, o in zip(inputs, pv, outcomes[n]) if p is not None and iorel.value(o) is not None
                   and not same(p, iorel.value(o))]
        if flagged:
            inst[n] = flagged
    return inst


# ---- oracle-kind accuracy (tool-mined candidates) ------------------------------------------------------------------
def mr_candidates(pairs, idx, put, contract, refo):
    """Predicates the PUT satisfies on >= 75% of valid pairs (>= MIN_MR_PAIRS): accurate iff the reference holds 100%."""
    by = {}
    for x, name, y in pairs:
        a, b = idx[x], idx[y]
        if contract[a][0] != 'ok' or contract[b][0] != 'ok':
            continue
        by.setdefault(name, []).append((iorel.category(iorel.value(put[a]), iorel.value(put[b])),
                                        iorel.category(iorel.value(refo[a]), iorel.value(refo[b])), x, y))
    cands = []
    for name, rows in by.items():
        rows = [r for r in rows if r[0] is not None and r[1] is not None]
        if len(rows) < MIN_MR_PAIRS:
            continue
        for pred, allowed in PREDICATES.items():
            if sum(pc in allowed for pc, _, _, _ in rows) / len(rows) >= CANDIDATE_SHARE:
                flagged = list(dict.fromkeys(v for pc, _, x, y in rows if pc not in allowed for v in (x, y)))
                cands.append(dict(name=f'{name}:{pred}', accurate=all(rc in allowed for _, rc, _, _ in rows), flagged=flagged))
    return cands


def prop_candidates(inputs, put, contract, refo):
    seen, put_ok, ref_ok, viol = {}, {}, {}, {}
    for k, lit in enumerate(inputs):
        if contract[k][0] != 'ok':
            continue
        po, ro = literal(put[k]), literal(refo[k])
        if po is None or ro is None:
            continue
        args = ast.literal_eval(lit)
        pp, rp = properties(args, po), properties(args, ro)
        for name in set(pp) & set(rp):
            seen[name] = seen.get(name, 0) + 1
            put_ok[name] = put_ok.get(name, 0) + pp[name]
            ref_ok[name] = ref_ok.get(name, 0) + rp[name]
            if not pp[name]:
                viol.setdefault(name, []).append(lit)
    return [dict(name=n, accurate=ref_ok[n] == seen[n], flagged=viol.get(n, [])) for n in seen
            if seen[n] >= MIN_PROP_INPUTS and put_ok[n] / seen[n] >= CANDIDATE_SHARE]


# ---- per case -------------------------------------------------------------------------------------------------------
def load_pool(case, v41_row):
    """v41 frozen pool, PUT outcomes and reference batch, read-only (hash-checked)."""
    from trickcatcher_linefacts.analysis.v42_mutoracle import mutoracle
    inputs, put = mutoracle.load_pool(case['case_id'], v41_row)
    return inputs, put, mutoracle.load_ref(case, inputs)


def dedupe(inst):
    """Merge instances with identical flagged sets (first name kept, group size recorded)."""
    out, seen = {}, {}
    for name, lits in inst.items():
        if not lits:
            continue
        key = tuple(lits)
        if key in seen:
            out[seen[key]]['merged'] += 1
        else:
            seen[key] = name
            out[name] = dict(flagged=lits, merged=0)
    return out


def tool_case(case, run, v41_row):
    seeds = ft_run.base_inputs(case, 'vibepass_half')
    domain = ft_concepts.domain_profile(seeds)
    prof = iorel.profile(seeds)
    names = param_names(run.task(case)['signature'])
    cons = constraints(run.task(case)['spec'], names)
    inputs, put, rr = load_pool(case, v41_row)
    pool = set(inputs)
    xs = [x for x in iorel.sample(seeds) if ft_concepts.in_domain(x, domain)]
    if any(repr(x) not in pool for x in xs):
        raise RuntimeError('resampled inputs are not in the frozen v41 pool')
    pairs = [(repr(x), name, repr(y)) for x in xs for name, y in iorel.transforms(x, prof) if ft_concepts.in_domain(y, domain)]
    idx = {lit: k for k, lit in enumerate(inputs)}
    kinds, errors = {}, {}
    builders = {'class': lambda: class_members(xs, prof, cons, seeds), 'boundary': lambda: boundary_members(xs, cons),
                'metamorphic': lambda: metamorphic(pairs, idx, put, rr['contract'], rr['ref']),
                'property': lambda: output_properties(inputs, put, rr['contract'], rr['ref']),
                'coverage': lambda: coverage_arcs(case, seeds, inputs), 'mutation': lambda: mutation(case, inputs, put)}
    for kind, build in builders.items():
        try:
            kinds[kind] = dedupe(build())
        except Exception as exc:  # per kind, not fatal
            errors[kind] = f'{type(exc).__name__}: {exc}'[:300]
            kinds[kind] = {}
    accuracy = {}
    for kind, cands in (('metamorphic', lambda: mr_candidates(pairs, idx, put, rr['contract'], rr['ref'])),
                        ('property', lambda: prop_candidates(inputs, put, rr['contract'], rr['ref']))):
        try:
            accuracy[kind] = cands()
        except Exception as exc:
            errors[f'{kind}_accuracy'] = f'{type(exc).__name__}: {exc}'[:300]
            accuracy[kind] = []
    return dict(case_id=case['case_id'], kinds=kinds, errors=errors, accuracy=accuracy, inputs=inputs, put=put, ref=rr,
                constraints={f'{a}:{k}': v for (a, k), v in cons.items()})


def evaluate(case, tc, official):
    inputs, put, rr = tc['inputs'], tc['put'], tc['ref']
    pool_exp, _ = exposing_set(inputs, put, rr['contract'], rr['ref'])
    universes = {k: list(inputs) for k in ('metamorphic', 'property', 'coverage', 'mutation')}
    gen_exp = set()
    for k in ('class', 'boundary'):
        universes[k] = list(dict.fromkeys(l for v in tc['kinds'][k].values() for l in v['flagged']))
    new = sorted({l for k in ('class', 'boundary') for l in universes[k]} - set(inputs))
    if new:
        p2, c2, r2 = run_inputs(case, 'generated', new)
        gen_exp, _ = exposing_set(new, p2, c2, r2)
    exp = pool_exp | gen_exp
    memo = {}

    def confirmed(lit):
        if lit not in memo:
            memo[lit] = lit in exp and iorel.official_exposes(official, case, lit)
        return memo[lit]
    row = dict(case_id=case['case_id'], errors=tc['errors'], c1=False)
    reach_union = set()
    for kind in KINDS:
        inst = tc['kinds'][kind]
        U = universes[kind]
        uset = set(U)
        eU = len(exp & uset)
        if not inst:
            row[kind] = dict(applicable=False, universe=len(U), universe_exposing=eU)
            continue
        shown = {n: v['flagged'][:K] for n, v in inst.items()}
        R = {l for v in shown.values() for l in v}
        if kind in INPUT_KINDS:  # the gate's union excludes oracle kinds (exposures by construction)
            reach_union |= R
        order = sorted(inst, key=lambda n: (-len(set(shown[n]) & exp), list(inst).index(n)))
        best, hits = order[0], []
        for n in order:
            if not set(shown[n]) & exp:
                break
            h = [l for l in shown[n] if confirmed(l)]
            if h:
                best, hits = n, h
                break
        rand_inst = statistics.mean(bool(set(v) & exp) for v in shown.values())
        lift = (len(set(shown[best]) & exp) / len(shown[best])) / (eU / len(U)) if eU else None
        row[kind] = dict(applicable=True, instances=len(inst), merged=sum(v['merged'] for v in inst.values()), universe=len(U),
                         universe_exposing=eU, reach=len(R), best=best, shown=len(shown[best]), hits=len(hits), covered=bool(hits),
                         matched_random=round(iorel.random_k(len(U), eU, len(R & uset)), 4), random_instance=round(rand_inst, 4),
                         lift=lift)
        row['c1'] |= bool(hits)
    # union over kinds; universe = pool + generated inputs
    allU = list(inputs) + new
    row['union_covered'] = any(row[k].get('covered') for k in INPUT_KINDS)
    row['union_with_oracle_covered'] = any(row[k].get('covered') for k in KINDS)  # reported, not gated
    row['union_reach'] = len(reach_union)
    row['union_matched_random'] = round(iorel.random_k(len(allU), len(exp), len(reach_union)), 4)
    row['c1'] = row['c1'] or any(confirmed(l) for l in sorted(exp)[:20])
    # oracle-kind accuracy (tool-mined candidates; no reference choice)
    row['oracle_accuracy'] = {}
    for kind in ORACLE_KINDS:
        cands = tc['accuracy'][kind]
        fa = sum(len([l for l in c['flagged'] if l not in exp]) for c in cands if not c['accurate'])
        row['oracle_accuracy'][kind] = dict(candidates=len(cands), accurate=sum(c['accurate'] for c in cands), false_alarm_inputs=fa,
                                            accurate_with_exposure=sum(1 for c in cands if c['accurate'] and set(c['flagged']) & exp))
    return row


def main():
    freeze_local_constants()
    run = ft_run.FTRun('vibepass_half')
    cases = run.cases
    v41 = {r['case_id']: r for r in json.loads((iorel.OUT / 'ceiling.json').read_text())['rows']}

    def safe(case):
        try:
            return tool_case(case, run, v41[case['case_id']])
        except Exception as exc:
            return dict(case_id=case['case_id'], error=f'{type(exc).__name__}: {exc}'[:300])
    with ThreadPoolExecutor(6) as pool:
        tcs = {tc['case_id']: tc for tc in pool.map(safe, cases)}
    official = Reference(run)
    official.root = iorel.OUT / 'official'  # v41 cache, content-digest keyed
    rows = []
    for case in cases:
        tc = tcs[case['case_id']]
        if 'error' in tc:
            rows.append(dict(case_id=case['case_id'], error=tc['error'], union_covered=False, union_matched_random=0.0, c1=False))
            continue
        try:
            rows.append(evaluate(case, tc, official))
        except Exception as exc:
            rows.append(dict(case_id=case['case_id'], error=f'evaluate: {type(exc).__name__}: {exc}'[:300], union_covered=False,
                             union_matched_random=0.0, c1=False))
    ok = [r for r in rows if 'error' not in r]
    per_kind = {}
    for kind in KINDS:
        app = [r[kind] for r in ok if r[kind]['applicable']]
        c1_lifts = [a['lift'] for r, a in ((r, r[kind]) for r in ok) if a['applicable'] and r['c1'] and a['lift'] is not None]
        per_kind[kind] = dict(applicable=len(app), ideal_coverage=sum(a['covered'] for a in app),
                              matched_random=round(sum(a['matched_random'] for a in app), 2),
                              random_instance=round(sum(a['random_instance'] for a in app), 2),
                              median_lift_c1=round(statistics.median(c1_lifts), 3) if c1_lifts else None,
                              mean_universe=round(statistics.mean(a['universe'] for a in app), 1) if app else None,
                              mean_reach=round(statistics.mean(a['reach'] for a in app), 1) if app else None,
                              kind_errors=sum(kind in r['errors'] for r in ok))
    oracle = {k: dict(candidates=sum(r['oracle_accuracy'][k]['candidates'] for r in ok),
                      accurate=sum(r['oracle_accuracy'][k]['accurate'] for r in ok),
                      false_alarm_inputs=sum(r['oracle_accuracy'][k]['false_alarm_inputs'] for r in ok),
                      tasks_accurate_with_exposure=sum(r['oracle_accuracy'][k]['accurate_with_exposure'] > 0 for r in ok))
              for k in ORACLE_KINDS}
    union = sum(r['union_covered'] for r in rows)
    union_oracle = sum(r.get('union_with_oracle_covered', False) for r in rows)
    expected = sum(r['union_matched_random'] for r in rows)
    taxonomy = [k for k in INPUT_KINDS if per_kind[k]['ideal_coverage'] >= 5 and (per_kind[k]['median_lift_c1'] or 0) >= 2]
    summary = dict(n=len(rows), case_errors=len(rows) - len(ok), c1=sum(r['c1'] for r in rows), per_kind=per_kind,
                   oracle_concepts=oracle, union_ideal_coverage=union, union_matched_random=round(expected, 2),
                   union_with_oracle_kinds=union_oracle,
                   taxonomy_input_kinds=taxonomy,
                   verdict='go' if union >= GATE_UNION and union >= expected + GATE_MARGIN else 'no-go')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'matrix.json').write_text(json.dumps(dict(summary=summary, rows=rows), indent=1, default=str) + '\n')
    (OUT / 'instances.json').write_text(json.dumps({k: dict(constraints=v.get('constraints'), error=v.get('error'), errors=v.get('errors'),
                                                        kinds={kk: {n: d['flagged'][:K] for n, d in vv.items()} for kk, vv in v.get('kinds', {}).items()})
                                                    for k, v in tcs.items()}, indent=1, default=str) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
