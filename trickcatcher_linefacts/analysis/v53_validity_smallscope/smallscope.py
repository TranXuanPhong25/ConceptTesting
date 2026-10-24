"""v53 Stage 2: small-scope input concept with the Sonnet `defn` oracle (see PREREG_STAGE2.md, amendment 1). Repo root:
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v53_validity_smallscope/smallscope.py prompts
  PYTHONPATH=. $V4_PYTHON trickcatcher_linefacts/analysis/v53_validity_smallscope/smallscope.py score
Sonnet subagents write out/.../stage2/answers/oracle/<problem>_<i>.txt (i < 3, the 18 problems not in v52) and
out/.../stage2/answers/<scope|plain>/<problem>.txt.
"""
import ast
import collections
import itertools
import json
import random
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from trickcatcher_linefacts.analysis.v48_e2e_oracle import menu_fixed as M
from trickcatcher_linefacts.analysis.v49_defn_oracle import gen
from trickcatcher_linefacts.analysis.v49_defn_oracle import oracle as O
from trickcatcher_linefacts.analysis.v49_defn_oracle import plan_rules as R
from trickcatcher_linefacts.analysis.v52_sonnet_defn import pilot as P
from trickcatcher_linefacts.analysis.v53_validity_smallscope import validity as V

E = O.E
OUT = V.OUT / 'stage2'
GEN_ARMS = ('scope', 'plain')
ARMS = (*GEN_ARMS, 'typed', 'random_small', 'universe')
K = 3
CAP = 300
SHARED = ('Each input is a tuple of the arguments in signature order (a 1-tuple when there is one parameter). Use only '
          'builtins and itertools; deterministic; no I/O, randomness or global state. Only the function inputs() and '
          'helpers; do not solve the problem.')
INSTR = {
    'scope': ('First write a comment block with one line `# DIMENSION: <name> | <scope> | <why>` for every input '
              'dimension: the size of each parameter, the values of its elements or characters, and every relation '
              'between parameters stated in the Constraints. Choose small scopes that keep the boundary values the '
              'Constraints allow and values that create ties, duplicates and equal elements. Then define inputs() that '
              'enumerates all valid combinations within these scopes, between 100 and 300 distinct inputs; shrink the '
              'scopes rather than truncate. ' + SHARED),
    'plain': ('Define inputs() returning between 100 and 300 distinct small valid inputs most likely to reveal a bug in a '
              'plausible but incorrect solution. ' + SHARED),
}


def message(task, arm):
    return (f"Problem statement:\n{task['spec']}\n\nPublic tests (valid inputs):\n{task['base']}\n\n"
            f"Function signature:\ndef {task['signature']}:\n\n{INSTR[arm]}")


def v52_task(cids):
    found = [c for c in cids if c in P.TASKS]
    return found[0] if found else None


def prompts():
    _, probs = V.problems()
    manifest = dict(oracle=[], scope=[], plain=[])
    for pid, cases in probs.items():
        cids = [c['case_id'] for c in cases]
        texts = {gen.messages(E.task_view(c), 'defn')[1]['content'] for c in cases}
        if len(texts) != 1:
            raise ValueError('defn prompt differs across sibling tasks: ' + pid)
        if v52_task(cids) is None:
            system, user = gen.messages(E.task_view(cases[0]), 'defn')
            path = OUT / 'prompts' / 'oracle' / f'{pid}.txt'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"SYSTEM:\n{system['content']}\n\nUSER:\n{user['content']}\n")
            manifest['oracle'].append(pid)
        for arm in GEN_ARMS:
            path = OUT / 'prompts' / arm / f'{pid}.txt'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"SYSTEM:\n{V.SYSTEM}\n\nUSER:\n{message(E.task_view(cases[0]), arm)}\n")
            manifest[arm].append(pid)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1))
    print({k: len(v) for k, v in manifest.items()})


GEN_WRAP = """

import itertools as _ss_it
_ss_cache = None


def __gen__(i):
    global _ss_cache
    if _ss_cache is None:
        _ss_cache = list(_ss_it.islice(inputs(), 2000))
    return len(_ss_cache) if i < 0 else _ss_cache[i]
"""


def params(case):
    return re.findall(r'(\w+)\s*:', E.task_view(case)['signature'].split('->')[0])


def literal(value, arity):
    """repr of an argument tuple, or None (wrong type/arity, or no literal round trip)."""
    if not isinstance(value, tuple) or len(value) != arity:
        return None
    lit = repr(value)
    try:
        return lit if ast.literal_eval(lit) == value else None
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None


def generated(case, pid, arm):
    """Run inputs() once in the sandbox: (literals <= CAP in answer order, info)."""
    code = O.code_block((OUT / 'answers' / arm / f'{pid}.txt').read_text())
    info = dict(status='ok', yielded=0, dropped=0, duplicates=0)
    if not code:
        return [], dict(info, status='parse_error')
    src, d = {'g': code + GEN_WRAP}, OUT / 'exec' / case['case_id'] / 'gen' / arm
    try:
        n = O.batch(d / 'len', src, ['g'], '__gen__', ['(-1,)'], 20)['g'][0]
        count = int(n[1]) if n[0] == 'ok' else 0
        items = O.batch(d / 'items', src, ['g'], '__gen__', [f'({i},)' for i in range(count)], 20)['g'] if count else []
    except RuntimeError:
        return [], dict(info, status='sandbox_failed')
    if n[0] != 'ok':
        info['status'] = 'inputs_' + n[0] + ('' if len(n) < 2 else ':' + str(n[1]))
    out, arity = [], len(params(case))
    for o in items:
        info['yielded'] += 1
        try:
            lit = literal(ast.literal_eval(o[1]), arity) if o[0] == 'ok' and not o[1].endswith('<truncated>') else None
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            lit = None
        if lit is None:
            info['dropped'] += 1
        elif lit in out:
            info['duplicates'] += 1
        elif len(out) < CAP:
            out.append(lit)
    return out, info


def typed_candidates(case, rec, limit=20000):
    """Type-driven small domains (amendment 1 item 2), seeded index sample of the product, no materialization."""
    task = E.task_view(case)
    names = params(case)
    hints = [h.strip() for h in re.findall(r':\s*([^,]+?)(?=,\s*\w+\s*:|$)', task['signature'].split('->')[0].strip()[:-1]
                                             if task['signature'].split('->')[0].strip().endswith(')') else
                                             task['signature'].split('->')[0])]
    cons, _ = M.constraints_report(task['spec'], names)
    public = [ast.literal_eval(x) for x in rec['base_inputs']]

    def bound(i, kind, lo, hi):
        b = cons.get((i, kind))
        return (b[0], b[1]) if b else (lo, hi)

    def ints(lo, hi, width):
        return list(range(lo, min(hi, lo + width) + 1))
    domains = []
    for i, hint in enumerate(hints):
        h = hint.replace(' ', '')
        if h == 'int':
            lo, hi = bound(i, 'value', -2, 3)
            domains.append(ints(lo, hi, 5))
        elif h == 'str':
            lo, hi = bound(i, 'length', 0, 4)
            chars = sorted({ch for x in public if i < len(x) and isinstance(x[i], str) for ch in x[i]})[:3] or ['a', 'b']
            domains.append([''.join(p) for n in range(max(lo, 0), min(hi, max(lo, 0) + 3) + 1)
                            for p in itertools.product(chars, repeat=n)])
        elif h == 'List[int]':
            lo, hi = bound(i, 'length', 0, 4)
            elo, ehi = bound(i, 'elem', 0, 3)
            el = ints(elo, ehi, 3)
            domains.append([list(p) for n in range(max(lo, 0), min(hi, max(lo, 0) + 3) + 1)
                            for p in itertools.product(el, repeat=n)])
        elif h == 'List[List[int]]':
            lo, hi = bound(i, 'length', 1, 3)
            elo, ehi = bound(i, 'elem2', 0, 3)
            el = ints(elo, ehi, 3)
            widths = collections.Counter(len(r) for x in public if i < len(x) for r in x[i] if isinstance(r, list))
            w = widths.most_common(1)[0][0] if widths else 2
            rows = [list(p) for p in itertools.product(el, repeat=w)]
            domains.append(('rows', rows, list(range(max(lo, 0), min(hi, max(lo, 0) + 2) + 1))))
        else:
            raise ValueError('typed: unsupported parameter type ' + hint)
    sizes = [sum(len(d[1]) ** n for n in d[2]) if isinstance(d, tuple) else len(d) for d in domains]
    total = 1
    for s in sizes:
        total *= s

    def pick(d, j):
        if not isinstance(d, tuple):
            return d[j]
        _, rows, counts = d
        for n in counts:
            if j < len(rows) ** n:
                return [rows[(j // len(rows) ** k) % len(rows)] for k in range(n)]
            j -= len(rows) ** n
    rng = random.Random(f"v53s2/typed/{case['case_id']}")
    out = []
    for idx in (rng.sample(range(total), total) if total <= limit else rng.sample(range(total), limit)):
        args = []
        for d, s in zip(domains, sizes):
            idx, j = divmod(idx, s)
            args.append(pick(d, j))
        out.append(repr(tuple(args)))
    return list(dict.fromkeys(out)), dict(product=total, sampled=min(total, limit))


def random_candidates(inv, case):
    pool = [lit for lit in dict.fromkeys(E.pool_inputs(inv, case['case_id']))
            if size(ast.literal_eval(lit)) <= 10]
    random.Random(f"v53s2/random/{case['case_id']}").shuffle(pool)
    return pool, dict(pool_small=len(pool))


def size(v):  # DIAGNOSTICS D2 size
    if isinstance(v, str):
        return len(v)
    if isinstance(v, (list, tuple)):
        return sum(max(1, size(e)) if isinstance(e, (list, tuple, str)) else 1 for e in v)
    return 1


def accept(case, rec, pid, inputs, tag):
    """Stage 1 `open` checks on new inputs (public drop rule), under the Stage 2 execution root."""
    code, found, _ = V.checks((V.OUT / 'answers' / f'{pid}_open.txt').read_text())
    if not found or not inputs:
        return {lit: True for lit in inputs}
    srcs = [V.wrap(code, case['entry'], c['name']) for c in found]
    with E.execution_root(OUT):
        base = O.run_programs(case, 'chk_open', srcs, rec['base_inputs'], 'base', 2)
        ran = O.run_programs(case, 'chk_open', srcs, inputs, tag)
    ok = lambda o: bool(o) and o[0] == 'ok' and o[1] == 'True'
    kept = [j for j in range(len(found)) if all(ok(o) for o in base[f'p{j}'])]
    return {lit: all(ok(ran[f'p{j}'][n]) for j in kept) for n, lit in enumerate(inputs)}


def oracle_sources(pid, cids):
    src = []
    old = v52_task(cids)
    for i in range(K):
        path = (P.OUT / 'programs' / 'defn' / old / f'{i}.txt') if old else OUT / 'answers' / 'oracle' / f'{pid}_{i}.txt'
        code = O.code_block(path.read_text()) if path.is_file() else ''
        src.append(code)
    return src


def truth_for(inv, case, rows, official):
    """O.task_truth with references written under the Stage 2 root (v49/v48 caches stay untouched)."""
    view = dict(inputs={lit: dict(put=r['put'], vote=None, consensus=None) for lit, r in rows.items()})
    with O.reference_root(OUT):
        truth = E.reference_truth(inv, case, view, official, set())
    for lit, t in truth.items():
        put = E.iorel.value(rows[lit]['put'])
        cache = []

        def exposes(lit=lit, t=t, put=put, cache=cache):
            if not cache:
                cache.append(bool(t['valid'] and put is not None and t['ref'] is not None and not E.same(put, t['ref'])
                                  and E.iorel.official_exposes(official, case, lit)))
            return cache[0]
        t['exposes'] = exposes
    return truth


def status_of_answers(manifest):
    st = {}
    for pid in manifest['oracle']:
        for i in range(K):
            p = OUT / 'answers' / 'oracle' / f'{pid}_{i}.txt'
            st[f'oracle/{pid}_{i}'] = 'missing' if not p.is_file() else 'ok' if O.code_block(p.read_text()) else 'parse_error'
    for arm in GEN_ARMS:
        for pid in manifest[arm]:
            p = OUT / 'answers' / arm / f'{pid}.txt'
            st[f'{arm}/{pid}'] = 'missing' if not p.is_file() else 'ok' if O.code_block(p.read_text()) else 'parse_error'
    return st


def arm_metrics(inputs, rows, truth, valid, strict_valid):
    m = O.metrics(set(inputs), rows['tolerant'], truth, valid)['primary']['capped']
    s = O.metrics(set(inputs), rows['strict'], truth, strict_valid)['primary']['capped']
    proxy = [l for l in E.ordered(inputs) if R.exposing(dict(truth[l], exposing=None), E.iorel.value(rows['tolerant'][l]['put']))]
    fin = [l for l in proxy if sum(bool(o and o[0] == 'ok') for o in rows['tolerant'][l]['programs']) >= 2]
    return dict(inputs=len(inputs), confirmed_tasks=m['confirmed_tasks'], confirmed_tests=m['correct_assertions'],
                tests=m['tests'], fa_tests=m['fa_tests'], precision=m['precision'],
                strict=dict(confirmed_tasks=s['confirmed_tasks'], tests=s['tests'], fa_tests=s['fa_tests']),
                proxy_exposing=len(proxy), reach=any(truth[l]['exposes']() for l in proxy),
                finishing_reach=any(truth[l]['exposes']() for l in fin))


def score():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    st = status_of_answers(manifest)
    excluded = set(json.loads((OUT / 'excluded_problems.json').read_text())) if (OUT / 'excluded_problems.json').is_file() else set()
    blocked = sorted(k for k, s in st.items() if s != 'ok' and k.split('/')[1][:12] not in excluded)
    if blocked:  # registered: no verdict while any included answer is missing or unparseable
        print(json.dumps(dict(verdict='incomplete', blocked=blocked), indent=1))
        return 1
    inv = O.Inventory()
    _, ready = O.score_inputs(inv)
    cohort, _, records, _ = ready
    run, probs = V.problems()
    official = E.Reference(run)
    official.root = OUT / 'references' / 'official'
    cases = {c['case_id']: c for c in run.cases}
    pid_of = {c['case_id']: p for p, cs in probs.items() for c in cs}
    tasks, gen_info = {}, {}
    for cid in cohort:
        pid = pid_of[cid]
        if pid in excluded:
            continue
        rec, case = records[cid], cases[cid]
        universe = E.ordered(rec['inputs'])
        cands = {}
        for arm in GEN_ARMS:
            cands[arm], gen_info[f'{arm}/{cid}'] = generated(case, pid, arm)
        cands['typed'], gen_info[f'typed/{cid}'] = typed_candidates(case, rec)
        cands['random_small'], gen_info[f'random_small/{cid}'] = random_candidates(inv, case)
        everything = list(dict.fromkeys(universe + [l for a in cands for l in cands[a]]))
        acc = accept(case, rec, pid, everything, 'all')
        arms = {a: [l for l in cands[a] if acc[l]][:CAP] for a in cands}
        arms['universe'] = [l for l in universe if acc[l]]
        for a in ('typed', 'random_small'):
            arms[a + '_matched'] = arms[a][:len(arms['scope'])]
        arms['universe+scope'] = list(dict.fromkeys(arms['universe'] + arms['scope']))
        arms['universe+plain'] = list(dict.fromkeys(arms['universe'] + arms['plain']))
        used = list(dict.fromkeys(l for a in arms.values() for l in a))
        new = [l for l in used if l not in rec['inputs']]
        srcs = oracle_sources(pid, [c['case_id'] for c in probs[pid]])
        with E.execution_root(OUT):
            put_new = O.run_programs(case, 'put', [case['source']], new, 'new')['p0'] if new else []
            base = O.run_programs(case, 'sonnet_defn', srcs, rec['base_inputs'], 'base', 2)
            reasons = {j: O.rejection(rec['base_put'], base[f'p{j}']) for j in range(K)}
            strict = [j for j in range(K) if srcs[j] and not reasons[j]]
            tolerant = [j for j in range(K) if srcs[j] and (not reasons[j] or (
                O.resource_only(reasons[j], base[f'p{j}']) and 'mismatch' not in reasons[j]
                and any(o and o[0] == 'ok' for o in base[f'p{j}'])))]
            ran = O.run_programs(case, 'sonnet_defn_valid', [srcs[j] for j in tolerant], used, 'used')
        put = {l: rec['inputs'][l]['put'] for l in used if l in rec['inputs']} | dict(zip(new, put_new))
        rows = {}
        for name, ids in (('tolerant', tolerant), ('strict', strict)):
            rows[name] = {}
            for n, l in enumerate(used):
                outs = [ran[f'p{tolerant.index(j)}'][n] for j in ids]
                rows[name][l] = dict(put=put[l], programs=outs, **O.votes(put[l], outs))
        truth = truth_for(inv, case, rows['tolerant'], official)
        tasks[cid] = dict(problem=pid, oracle=dict(strict=strict, tolerant=tolerant,
                                                    reasons={str(j): reasons[j] for j in range(K)}),
                          arms={a: arm_metrics(ins, rows, truth, len(tolerant), len(strict)) for a, ins in arms.items()})
        print(cid, {a: (m['inputs'], m['confirmed_tasks'], m['fa_tests'], m['reach']) for a, m in tasks[cid]['arms'].items()},
              flush=True)
    names = list(next(iter(tasks.values()))['arms'])
    totals = {a: dict(confirmed_tasks=sum(t['arms'][a]['confirmed_tasks'] for t in tasks.values()),
                      strict_confirmed_tasks=sum(t['arms'][a]['strict']['confirmed_tasks'] for t in tasks.values()),
                      confirmed_tests=sum(t['arms'][a]['confirmed_tests'] for t in tasks.values()),
                      tests=sum(t['arms'][a]['tests'] for t in tasks.values()),
                      fa_tests=sum(t['arms'][a]['fa_tests'] for t in tasks.values()),
                      reach=sum(t['arms'][a]['reach'] for t in tasks.values()),
                      finishing_reach=sum(t['arms'][a]['finishing_reach'] for t in tasks.values()),
                      inputs=sum(t['arms'][a]['inputs'] for t in tasks.values())) for a in names}
    for t in totals.values():
        t['precision'] = t['confirmed_tests'] / t['tests'] if t['tests'] else None
    checks = {}
    for comp in ('plain', 'typed', 'random_small'):
        only = [c for c, t in tasks.items() if t['arms']['scope']['confirmed_tasks'] and not t['arms'][comp]['confirmed_tasks']]
        checks[comp] = dict(scope_only=only, comp_only=[c for c, t in tasks.items() if t['arms'][comp]['confirmed_tasks']
                                                        and not t['arms']['scope']['confirmed_tasks']],
                            margin=totals['scope']['confirmed_tasks'] - totals[comp]['confirmed_tasks'],
                            margin_ok=totals['scope']['confirmed_tasks'] >= totals[comp]['confirmed_tasks'] + 2,
                            span_ok=len({tasks[c]['problem'] for c in only}) >= 2,
                            fa_ok=totals['scope']['fa_tests'] <= totals[comp]['fa_tests'] + 5)
    precision_ok = (totals['scope']['precision'] or 0) >= 0.8
    passed = precision_ok and all(c['margin_ok'] and c['span_ok'] and c['fa_ok'] for c in checks.values())
    decision = dict(checks=checks, precision_ok=precision_ok,
                    verdict='pending_manual_audit' if passed else 'not promising',
                    audit_tasks=sorted({c for v in checks.values() for c in v['scope_only']}) if passed else [])
    out = dict(decision=decision, totals=totals, tasks=tasks, generation=gen_info, answer_status=st,
               excluded_problems=sorted(excluded))
    O.immutable(OUT / 'score.json', out)
    print(json.dumps(dict(decision=decision, totals=totals), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(dict(prompts=prompts, score=score)[sys.argv[1]]() or 0)
