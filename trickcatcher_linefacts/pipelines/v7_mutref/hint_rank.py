"""Frozen LR[noref+mutref]; method-only extraction adapted from analysis/hint_rank.py.

No fitting or HumanEval+ labels. Reference agreement is consulted only for MUTANT
inputs. All extraction details (witness first, 40-input cap, nearest-base repr,
majority threshold, base-pass filtering) follow the registered analysis.
"""
from __future__ import annotations
import ast
import hashlib
import json
import math
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = 'trickcatcher_linefacts.pipelines.' + Path(__file__).resolve().parent.name
from . import paths

KIND_GROUPS = ['OUTCOME', 'STMT', 'MUTANT', 'MUTANT-X', 'BOUND', 'NUM', 'REL',
               'SHAPE', 'OUTPUT', 'LOOP', 'LOOP-MAX', 'DU', 'DECISION', 'SPEC']
FEATURE_NAMES = ['kind=' + k for k in KIND_GROUPS] + [
    'covered_site', 'boundary', 'tier1(g_demote)', 'on_compare_line', 'log10(hit_frac)',
    'out_change_vs_nearest_base', 'crash_on_hit_input', 'crash_frac',
    'mutant_agrees_ref_put_not', 'only_mutant_disagrees_ref']


def x_of(r):
    kind = 'SPEC' if r['src'] == 'spec' else r['slot']
    return [float(kind == k) for k in KIND_GROUPS] + [
        float(r['covered_site']), float(r['boundary']), float(r['tier']), float(r['cmp_dist'] == 0),
        math.log10(max(r['hit_frac'], 1e-3)), float(r['out_change']),
        float(r['crash'] > 0), r['crash'] / max(1, r['n_eval']),
        float(r.get('mut_fh', 0) > 0),
        float(r.get('mut_wrong', 0) > 0 and r.get('mut_fh', 0) == 0)]


def score(r):
    coef = paths.CONFIG['hint_rank']['coefficients']
    return sum(coef[name] * value for name, value in zip(FEATURE_NAMES, x_of(r))) + coef['intercept']


def select(n, rows, k=3):
    order = list(range(len(rows)))
    random.Random(paths.CONFIG['hint_rank']['tie_seed'] + n).shuffle(order)
    order.sort(key=lambda j: -score(rows[j]))
    return order[:k]


def extract(task, he, fr, spec, precond, refs_txt):
    import difflib
    from . import facts as F, spec_facts as S
    from .tracer import HOOKS, call, instrument, load_module, run_base, same, trace, fact_hit
    from .fuzz_validity import validator
    from .oracle_b01 import code_block

    n, entry, src, bundle = task['task'], task['entry'], task['put'], task

    # --- replay facts.main up to the fuzz inputs (same seed, same validator)
    rng = random.Random(F.SEED + n)
    pg = load_module(src)
    put = pg[entry]
    base_args, ok = run_base(put, he["test"], ns=pg)
    code, sites = instrument(src)
    iput = load_module(code, HOOKS)[entry]
    base_lines, base_out = set(), []
    for a in base_args:
        cs, ls, st, val = trace(iput, a)
        base_lines |= ls
        base_out.append((st, val))
    F.CONSTS[:] = sorted({x.value for x in ast.walk(ast.parse(src)) if isinstance(x, ast.Constant)
                          and isinstance(x.value, (int, float)) and not isinstance(x.value, bool)
                          and abs(x.value) < 10 ** 6} - {0, 1, -1})[:12]
    with validator("mined", n, precond) as valid:
        fz = F.fuzz_inputs(base_args, rng, valid, n, {})
    fzt = [trace(iput, a) for a in fz]
    pout = [(t[2], t[3]) for t in fzt]

    # --- spec-only reference programs (B2), kept if they pass the base tests
    refs_txt = sorted((r for r in refs_txt if r['stage'] == 'ref' and r['task'] == str(n)),
                      key=lambda r: r['sample'])
    refs = []
    for r in refs_txt:
        s = code_block(r["text"])
        if not s:
            continue
        try:
            ns = load_module("from typing import *\nimport math\n" + s, filename="<ref>")
            fn = ns.get(entry)
        except BaseException:
            continue
        if callable(fn) and run_base(fn, bundle["base"], T=20, record=False, ns=ns)[1] is True:
            refs.append(fn)

    def majority(args):
        if len(refs) < 3:
            return None
        outs = [call(fn, args, T=3.0) for fn in refs]
        good = [v for s, v in outs if s == "ok"]
        groups = []
        for v in good:
            for g in groups:
                if same(g[0], v):
                    g[1] += 1
                    break
            else:
                groups.append([v, 1])
        if not groups:
            return None
        v, c = max(groups, key=lambda g: g[1])
        return (v,) if c > len(refs) / 2 else None

    maj_cache = {}

    def maj(i, args):
        if i not in maj_cache:
            maj_cache[i] = majority(args)
        return maj_cache[i]

    # --- static helpers
    tree = ast.parse(src)
    cmp_lines = sorted({x.lineno for x in ast.walk(tree) if isinstance(x, ast.Compare)})

    def cmp_dist(line):
        return min((abs(line - l) for l in cmp_lines), default=99)

    def rep(a):
        r = repr(a)
        return r[:400]

    base_reps = [rep(a) for a in base_args]

    def nearest_base(a):
        r = rep(a)
        best = max(range(len(base_args)), key=lambda j: difflib.SequenceMatcher(None, r, base_reps[j]).ratio())
        return best

    def witness_args(call_src):
        node = ast.parse(call_src, mode="eval").body
        return (tuple(ast.literal_eval(x) for x in node.args), {k.arg: ast.literal_eval(k.value) for k in node.keywords})

    def bad(st, v, m):  # PUT disagrees with the ref majority m (None = no majority)
        return m is not None and (st != "ok" or not same(v, m[0]))

    def signals(hits, put_out, mut_out=None):
        """hits: list of (fz index or key, args). ref/crash signals over the hit inputs (capped)."""
        hits = hits[:40]
        crash = sum(put_out(i)[0] not in ("ok",) for i, _ in hits)
        n_fh = n_mbad = 0
        for i, a in hits if mut_out is not None else []:
            m = maj(i, a)
            if m is None:
                continue
            ps, pv = put_out(i)
            pb = bad(ps, pv, m)
            if mut_out is not None:
                ms, mv = mut_out(i)
                mb = bad(ms, mv, m)
                n_fh += pb and not mb
                n_mbad += mb and not pb
        out = dict(n_eval=len(hits), crash=crash)
        if mut_out is not None:
            out.update(mut_fh=n_fh, mut_wrong=n_mbad)
        return out

    rows = []
    witness_mismatch = 0
    for idx, f in enumerate(fr["facts"]):
        if not f["reached"]:
            continue
        mfn, mo = None, {}
        if f["kind"] == "MUTANT":
            try:
                mfn = load_module(F.make_mutant(src, f["k"])[0])[entry]
            except BaseException:
                mfn = None
        hit = []
        for i, a in enumerate(fz):
            mout = None
            if f["kind"] == "MUTANT":
                if mfn is None:
                    break
                mo[i] = mout = call(mfn, a)
            if fact_hit(f, fzt[i], pout[i], mout):
                hit.append(i)
        wa = witness_args(f["witness_call"])
        if f["witness"] >= len(fz) or F.call_src(entry, fz[f["witness"]]) != f["witness_call"]:
            witness_mismatch += 1
        w_i = f["witness"] if f["witness"] < len(fz) and F.call_src(entry, fz[f["witness"]]) == f["witness_call"] else None
        wst, wv = pout[w_i] if w_i is not None else call(put, wa)
        nb = nearest_base(wa)
        out_change = not (wst == base_out[nb][0] and (wst != "ok" or same(wv, base_out[nb][1])))
        hits = [(i, fz[i]) for i in ([w_i] if w_i is not None else []) + [i for i in hit if i != w_i]]
        sig = signals(hits, lambda i: pout[i],
                      (lambda i: mo[i] if i in mo else call(mfn, fz[i])) if mfn is not None else None)
        rows.append(dict(src="code", idx=idx, kind=f["kind"], slot=F.slot(f), line=f["line"], block=f.get("block"),
                         tier=f.get("tier", 0), g_demote=bool(f.get("g_demote")), guard_class=f.get("guard_class"),
                         boundary=bool(f.get("boundary")), family=f.get("family"), extended=bool(f.get("extended")),
                         covered_site=f["kind"] != "STMT" and f["line"] in base_lines, cmp_dist=cmp_dist(f["line"]),
                         n_hit=len(hit), hit_frac=len(hit) / max(1, len(fz)), out_change=out_change,
                         witness_crash=wst != "ok", **sig))
    for j, f in enumerate(spec["facts"]):
        c = f["input_class"]
        wa = (tuple(f["witness_args"]), {})
        hit = [i for i, a in enumerate(fz) if not a[1] and c["param"] < len(a[0]) and S.in_class(c["cls"], a[0][c["param"]])]
        wst, wv = call(put, wa)
        nb = nearest_base(wa)
        out_change = not (wst == base_out[nb][0] and (wst != "ok" or same(wv, base_out[nb][1])))
        hits = [("w", wa)] + [(i, fz[i]) for i in hit]
        sig = signals(hits, lambda i: (wst, wv) if i == "w" else pout[i])
        rows.append(dict(src="spec", idx=j, kind="SPEC", slot="SPEC-" + c["cls"], line=None, block=None, tier=0,
                         g_demote=False, guard_class=None, boundary=False, family=c["cls"], extended=False,
                         covered_site=False, cmp_dist=99, n_hit=len(hit) + 1, hit_frac=(len(hit) + 1) / max(1, len(fz) + 1),
                         out_change=out_change, witness_crash=wst != "ok", **sig))
    return dict(task=n, n_fuzz=len(fz), n_base=len(base_args), n_refs=len(refs), n_refs_raw=len(refs_txt),
                witness_mismatch=witness_mismatch, rows=rows)


def fingerprint(task, he, fr, spec, precond, refs):
    inputs = dict(task=task, he={k: he[k] for k in ('entry_point', 'test')}, facts=fr['facts'],
                  spec=spec, valid=(precond / str(task['task']) / 'valid.py').read_text(), refs=refs,
                  config=paths.CONFIG['hint_rank'],
                  source=Path(__file__).read_text())
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()


def stage(layout, workers=12):
    from .run import task_sources
    from .v4_runtime import immutable
    tasks, he, _ = task_sources(layout)
    refs_path = layout.refs / 'ref_responses.json'
    if not refs_path.is_file():
        raise ValueError('run refs before bundle (B2 programs are required)')
    refs = json.loads(refs_path.read_text())
    directory = layout.root / 'rank'
    directory.mkdir(parents=True, exist_ok=True)

    def one(t):
        n = t['task']
        fr = json.loads((layout.facts / f'{n}.json').read_text())
        spec = json.loads((layout.specfacts / f'{n}.json').read_text())
        rr = [r for r in refs if r['task'] == str(n)]
        if len(rr) != 10 or {r['sample'] for r in rr} != set(range(10)):
            raise ValueError(f'task {n}: expected the ten B2 responses')
        fp = fingerprint(t, he[n], fr, spec, layout.precond, rr)
        job = dict(task=t, he=he[n], fr=fr, spec=spec, precond=str(layout.precond), refs=rr, fingerprint=fp)
        jp, op = directory / f'{n}.job.json', directory / f'{n}.json'
        immutable(jp, job)
        if op.exists():
            if json.loads(op.read_text()).get('fingerprint') != fp:
                raise ValueError(f'task {n}: stale ranking features; use a fresh output directory')
            return
        result = subprocess.run(['timeout', '-k', '5', '3600', 'unshare', '-rn', sys.executable,
                                 '-I', '-B', str(Path(__file__).resolve()), 'worker', str(jp), str(op)],
                                env=paths.worker_env(), capture_output=True, text=True)
        if result.returncode or not op.exists():
            raise RuntimeError(f'task {n}: rank worker rc={result.returncode}: {result.stderr[-1000:]}')
        print(f'rank: task {n} ready', flush=True)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, tasks))


def worker(jp, op):
    from .v4_runtime import immutable
    job = json.loads(Path(jp).read_text())
    result = extract(job['task'], job['he'], job['fr'], job['spec'], Path(job['precond']), job['refs'])
    result['fingerprint'] = job['fingerprint']
    immutable(Path(op), result)


if __name__ == '__main__':
    if sys.argv[1:2] != ['worker']:
        raise SystemExit('use run bundle to extract features')
    worker(*sys.argv[2:4])
