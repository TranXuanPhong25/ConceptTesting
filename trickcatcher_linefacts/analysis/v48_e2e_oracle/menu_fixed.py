"""v47 tool-side menus with generality fixes, for future cohorts only.
diff_current33 rebuilds without references or model calls; frozen v47 is never changed.
"""
import argparse
import ast
import hashlib
import json
import math
import random
import re
import sys

sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v47_concept_select import select_run as old
from trickcatcher_linefacts.analysis.v48_e2e_oracle import e2e
from trickcatcher_linefacts.pipelines.v34_ftplacebo import ft_concepts, ft_run
from trickcatcher_linefacts.pipelines.v34_ftplacebo.flow_common import immutable

M, iorel = old.M, old.iorel
K, BASE, MENU_MAX = old.K, old.BASE, old.MENU_MAX
INPUT_KINDS, ARMS, CODE_KINDS = old.INPUT_KINDS, old.ARMS, old.CODE_KINDS
NUMBER = r'[+-]?\d+(?:\s*(?:\*\*|\^|\*)\s*[+-]?\d+)*'
TARGET = r'(?:len\(\s*[A-Za-z_]\w*\s*\)|[A-Za-z_]\w*(?:\.length|\[[A-Za-z_]\w*\]\[[A-Za-z_]\w*\]|\[[A-Za-z_]\w*\])?)'


def number(text):
    """Integer powers, mathematical ^ notation and products; no eval or partial parses."""
    tree = ast.parse(text.strip().replace('^', '**'), mode='eval')

    def calc(n):
        if isinstance(n, ast.Constant) and type(n.value) is int:
            return n.value
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return (-1 if isinstance(n.op, ast.USub) else 1) * calc(n.operand)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Mult, ast.Pow)):
            a, b = calc(n.left), calc(n.right)
            if isinstance(n.op, ast.Pow) and not 0 <= b <= 100:
                raise ValueError('unsupported exponent')
            v = a * b if isinstance(n.op, ast.Mult) else a ** b
            if v.bit_length() > 1024:
                raise ValueError('bound too large')
            return v
        raise ValueError('unsupported numeric bound: ' + text)
    return calc(tree.body)


def constraints_report(spec, names):
    spec = re.sub(rf'(<=|<)\s*[A-Za-z_]\w*\s*==\s*({TARGET})', r'\1 \2', spec)
    middle = re.compile(rf'(?P<op1><=|<)\s*(?P<target>{TARGET}(?:\s*,\s*{TARGET})*)\s*(?P<op2><=|<)')
    out, unsupported = {}, []
    for line in spec.splitlines():
        for m in middle.finditer(line):
            targets = [s.strip() for s in m['target'].split(',')]
            relevant = []
            for t in targets:
                length = re.fullmatch(r'len\(\s*(\w+)\s*\)', t)
                base = length.group(1) if length else re.match(r'\w+', t).group()
                if base in names:
                    kind = 'length' if length or t.endswith('.length') else 'elem2' if t.count('[') == 2 else 'elem' if '[' in t else 'value'
                    relevant.append((names.index(base), kind))
            if not relevant:
                continue
            left, right = line[:m.start()].rstrip(), line[m.end():].lstrip()
            lo = re.search(rf'(?<![\w*^])({NUMBER})$', left)
            hi = re.match(rf'({NUMBER})(?![\w*^]|\s*(?:\*|\^|\+|/|-\s*\d))', right)
            try:
                if not lo or not hi:
                    raise ValueError('unsupported bound syntax')
                # A power/product must never be silently shortened by regex backtracking.
                if re.search(r'[\w*^]\s*$', left[:lo.start()]):
                    raise ValueError('unsupported lower bound')
                a, b = number(lo.group(1)) + (m['op1'] == '<'), number(hi.group(1)) - (m['op2'] == '<')
                if a > b:
                    raise ValueError('empty bound range')
                for key in relevant:
                    out[key] = (a, b)
            except (ValueError, SyntaxError) as exc:
                unsupported.append(dict(text=line.strip(), target=m['target'], error=str(exc)))
        if '<=' in line and any(re.search(rf'\b{re.escape(n)}\b', line) for n in names) \
                and not list(middle.finditer(line)):
            unsupported.append(dict(text=line.strip(), error='unsupported constraint form'))
    return out, unsupported


def constraints(spec, names):
    out, unsupported = constraints_report(spec, names)
    if unsupported:
        raise ValueError(json.dumps(unsupported))
    return out


def log_uniform(rng, lo, hi):
    """Log-uniform magnitude within each sign, including zero when allowed."""
    if lo > hi:
        raise ValueError('empty range')
    if lo >= 0:
        return old.log_uniform(rng, lo, hi)
    segments = []
    if lo < 0:
        segments.append((-1, max(1, -hi), -lo))
    if lo <= 0 <= hi:
        segments.append((0, 0, 0))
    if hi > 0:
        segments.append((1, max(1, lo), hi))
    sign, a, b = rng.choice(segments)
    return 0 if sign == 0 else sign * min(b, max(a, round(math.exp(rng.uniform(math.log(a), math.log(b))))))


def argument_range(pool, i, kind):
    values = []
    for x in pool:
        if i >= len(x):
            continue
        v = x[i]
        if kind == 'value' and iorel.is_int(v):
            values.append(v)
        elif kind == 'elem' and type(v) is list:
            values.extend(e for e in v if iorel.is_int(e))
        elif kind == 'elem2' and type(v) is list:
            values.extend(e for row in v if type(row) is list for e in row if iorel.is_int(e))
    return (min(values), max(values)) if values else None


def spec_range_members(case_id, xs, cons, pool=None):
    inst = {}
    for (i, kind), (lo, hi) in sorted(cons.items()):
        bounds = argument_range(xs if pool is None else pool, i, kind)
        if kind == 'length' or (bounds is not None and lo >= bounds[0] and hi <= bounds[1]):
            continue
        for variant in ('all', 'one'):
            rng = random.Random(f'{case_id}:{i}:{kind}:{variant}')
            name = f'arg{i}:{kind}_spread_{variant}'
            for x in xs[:BASE]:
                if i >= len(x):
                    continue
                v = x[i]
                if kind == 'elem' and type(v) is list and v and all(iorel.is_int(e) for e in v):
                    nv = [log_uniform(rng, lo, hi) for _ in v] if variant == 'all' else v[:-1] + [log_uniform(rng, lo, hi)]
                elif kind == 'elem2' and type(v) is list and v and all(type(r) is list and r and all(iorel.is_int(e) for e in r) for r in v):
                    nv = [[log_uniform(rng, lo, hi) for _ in r] for r in v] if variant == 'all' else [r[:] for r in v[:-1]] + [v[-1][:-1] + [log_uniform(rng, lo, hi)]]
                elif kind == 'value' and iorel.is_int(v) and variant == 'all':
                    nv = log_uniform(rng, lo, hi)
                else:
                    continue
                inst.setdefault(name, []).append(repr(x[:i] + (nv,) + x[i + 1:]))
    return {k: list(dict.fromkeys(v)) for k, v in inst.items()}


def dedupe(inst):
    out, seen = {}, {}
    for name, lits in inst.items():
        if not lits:
            continue
        key = frozenset(lits)
        if key in seen:
            out[seen[key]]['merged'] += 1
        else:
            seen[key] = name
            out[name] = dict(flagged=list(dict.fromkeys(lits)), merged=0)
    return out


def menu(kinds, params, cons, mtext, case_id, arm):
    order = [k for k in INPUT_KINDS if arm == 'spec+code' or k not in CODE_KINDS]
    queues = {k: list(kinds[k]) for k in order}
    items, seen, merged = [], set(), 0
    while len(items) < MENU_MAX and any(queues.values()):
        for k in order:
            while queues[k] and len(items) < MENU_MAX:
                name = queues[k].pop(0)
                key = frozenset(kinds[k][name]['flagged'][:K])
                if key in seen:
                    merged += 1
                    continue
                seen.add(key)
                items.append(dict(id=f'M{len(items) + 1}', kind=k, instance=name,
                                  text=old.describe(k, name, params, cons, mtext, case_id)))
                break
    return dict(items=items, merged=merged)


def cached_call(path, messages):
    """No network: only accept a saved call whose exact prompt digest matches."""
    rec = json.loads(path.read_text())
    sha = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
    if rec.get('prompt_sha256') != sha:
        raise ValueError('cached prompt digest differs: ' + str(path))
    return rec


def coverage_cached(inv, case, seeds, inputs):
    d = M.OUT / 'cases' / case['case_id'] / 'coverage'
    job = inv.read(d / 'job.json')
    expected = dict(source=case['source'], entry=case['entry'], inputs=[repr(s) for s in seeds] + inputs, per_call_timeout=1)
    if job != expected:
        raise ValueError('coverage cache differs; frozen v44 must not be rewritten')
    res = inv.read(d / 'result.json')
    if not res.get('measured') or not any(res['arcs'][:len(seeds)]):
        raise ValueError('coverage not measured')
    public = {tuple(a) for r in res['arcs'][:len(seeds)] if r for a in r}
    inst = {}
    for lit, arcs in zip(inputs, res['arcs'][len(seeds):]):
        for a in arcs or []:
            if tuple(a) not in public:
                inst.setdefault(f'arc{a[0]}->{a[1]}', []).append(lit)
    return inst


def prepare_case(case, inv=None):
    inv = inv or e2e.Inventory()
    cid = case['case_id']
    inputs = e2e.pool_inputs(inv, cid)
    put = inv.read(iorel.OUT / 'cases' / cid / 'put' / 'result.json')['put']
    seeds = ft_run.base_inputs(case, 'vibepass_half')
    domain, prof = ft_concepts.domain_profile(seeds), iorel.profile(seeds)
    xs = [x for x in iorel.sample(seeds) if ft_concepts.in_domain(x, domain)]
    if any(repr(x) not in set(inputs) for x in xs):
        raise ValueError('resampled inputs differ from frozen pool')
    task = e2e.task_view(case)
    params = M.param_names(task['signature'])
    cons, unsupported = constraints_report(task['spec'], params)
    builders = {'class': lambda: M.class_members(xs, prof, cons, seeds), 'boundary': lambda: M.boundary_members(xs, cons),
                'coverage': lambda: coverage_cached(inv, case, seeds, inputs), 'mutation': lambda: M.mutation(case, inputs, put),
                'spec_range': lambda: spec_range_members(cid, xs, cons, [ast.literal_eval(l) for l in inputs]),
                'value_biased': lambda: old.value_biased_members(cid, seeds, xs)}
    kinds, errors = {}, {}
    for k, build in builders.items():
        try:
            kinds[k] = dedupe(build())
        except Exception as exc:
            kinds[k], errors[k] = {}, f'{type(exc).__name__}: {exc}'[:300]
    mtext = old.mutant_texts(cid, list(kinds['mutation']), task['source_masked'])
    menus = {a: menu(kinds, params, cons, mtext, cid, a) for a in ARMS}
    return dict(case_id=cid, complete=not errors and not unsupported, errors=errors, unsupported_constraints=unsupported,
                kinds={k: {n: v['flagged'][:K] for n, v in d.items()} for k, d in kinds.items()}, menus=menus)


def diff_current33():
    inv = e2e.Inventory()
    tasks, _ = e2e.planned(inv)
    frozen = inv.read(old.OUT / 'prepared.json')
    cases = e2e.tool_cases(inv, tasks)
    rows = []
    for cid in tasks:
        try:
            p = prepare_case(cases[cid], inv)
            changed = {}
            for a in ARMS:
                before = frozen[cid].get('menus', {}).get(a, {}).get('items', [])
                after = p['menus'][a]['items']
                changed[a] = dict(changed=before != after, before=len(before), after=len(after))
            rows.append(dict(case_id=cid, complete=p['complete'], errors=p['errors'],
                             unsupported_constraints=p['unsupported_constraints'], menus=changed))
        except Exception as exc:
            rows.append(dict(case_id=cid, complete=False, error=f'{type(exc).__name__}: {exc}'))
    result = dict(tasks=len(tasks), changed_tasks=[r['case_id'] for r in rows if any(a['changed'] for a in r.get('menus', {}).values())],
                  incomplete_tasks=[r['case_id'] for r in rows if not r['complete']], rows=rows)
    immutable(e2e.OUT / 'menu_fixed_diff.json', result)
    print(json.dumps(result, indent=2))
    return int(bool(result['incomplete_tasks']))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=('diff_current33',))
    ap.parse_args()
    raise SystemExit(diff_current33())
