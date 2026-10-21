"""V4 fact construction: frozen templates/ranking/gates, standard fuzz/mutation/C1/C2."""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import ast, json, random, time
from .facts import SEED, N_FUZZ, FUZZ_CAP, K, G_PRIME, GATED_SLOTS, RANK_SLOTS, SLOTS, HOOKS, load_module, run_base, doc_fail, instrument, trace, statements, t_stmt, t_stmt_placebo, t_outcome, t_outcome_placebo, describe, say, call, same, t_mutant, new_facts, call_src, set_blocks, guard_features, tier, pick, display_slot, slot
from .preconditions import sha
from .v4_runtime import VERSIONS
from .v4_tools import Coverage, enumerate_mutants
from .v4_worker import draw


def build(job, directory):
    n, put_src, he = job['task']['task'], job['task']['put'], job['he']
    task = job['task']
    coverage = Coverage(put_src, task['entry'], directory)
    t0 = time.time()
    rng = random.Random(SEED + n)
    entry = he["entry_point"]
    pg = load_module(put_src)
    put = pg[entry]
    base_args, ok = run_base(put, he["test"], ns=pg)
    res = {"task": n, "entry": entry, "base_ok": ok, "n_base": len(base_args)}
    res["doc_fail"] = doc_fail(put, he["prompt"], entry)

    code, sites = instrument(put_src)
    iput = load_module(code, HOOKS)[entry]
    base_cells, base_lines, base_traces = set(), set(), []
    for a in base_args:
        tr = coverage.trace(iput, a)
        base_traces.append(tr)
        cs, ls, _, _ = tr
        base_cells |= cs
        base_lines |= ls

    generated = draw(dict(task=task, code=task['strategy_src'], seed=SEED+n, n=N_FUZZ, cap=FUZZ_CAP,
                          exclude=[repr(a) for a,k in base_args if not k]))
    fz = [(ast.literal_eval(r['input_repr']),{}) for r in generated['candidates']]
    res.update(facts_version='v4', fuzz_validity={k:v for k,v in generated.items() if k!='candidates'},
               fuzz_inputs=[r['input_repr'] for r in generated['candidates']],
               valid_sha256=sha(task['mined_valid_src']), strategy_sha256=sha(task['strategy_src']), tools=VERSIONS)
    fz_cells, fz_lines, fz_out, fz_traces = [], [], [], []
    for a in fz:
        tr = coverage.trace(iput, a)
        fz_traces.append(tr)
        cs, ls, st, val = tr
        fz_cells.append(cs)
        fz_lines.append(ls)
        fz_out.append((st, val))
    res["n_fuzz"] = len(fz)

    def first_hit(pred):
        for i in range(len(fz)):
            if pred(i):
                return i
        return None

    facts, placebo = coverage.branch_facts(base_traces, fz_traces)

    # OUTCOME
    for sid, s in enumerate(sites):
        if s["kind"] != "subcond":
            continue
        seen = {c for (x, c) in base_cells if x == sid and c in ("T", "F")}
        if len(seen) == 1:
            miss = "F" if "T" in seen else "T"
            w = first_hit(lambda i: (sid, miss) in fz_cells[i])
            facts.append({"kind": "OUTCOME", "line": s["line"], "text": t_outcome(s["line"], s["src"], miss, s["kind"] == "subcond", s.get("decision_line")),
                          "cell": [sid, miss], "witness": w})
        elif len(seen) == 2:
            placebo.append({"kind": "OUTCOME", "line": s["line"], "text": t_outcome_placebo(s["line"], s["src"], s["kind"] == "subcond", s.get("decision_line")),
                            "cells": [[sid, "T"], [sid, "F"]]})

    # STMT: maximal runs of consecutive never-executed statements
    stmts = [(ln, put_src.splitlines()[ln-1].strip()) for ln in sorted(coverage.statements)]
    run = []
    for ln, txt in stmts + [(None, None)]:
        if ln is not None and ln not in base_lines:
            run.append((ln, txt))
            continue
        if run:
            lines = [x for x, _ in run]
            w = first_hit(lambda i: bool(set(lines) & fz_lines[i]))
            facts.append({"kind": "STMT", "line": lines[0], "text": t_stmt(lines[0], lines[-1], run[0][1]),
                          "lines": lines, "witness": w})
            run = []
        if ln is not None:
            placebo.append({"kind": "STMT", "line": ln, "text": t_stmt_placebo(ln, txt), "lines": [ln]})

    # BOUND / REL / SHAPE / NUM: a property that held the same way in every base execution ("never" or "always")
    inv = {}
    for (sid, c) in base_cells:
        if isinstance(c, str) and c.split("|", 1)[0] in ("eqc", "eqv", "P", "R"):
            key, t = c.rsplit("|", 1)
            inv.setdefault((sid, key), set()).add(t)
    for (sid, key), ts in sorted(inv.items()):
        d = describe(sites, sid, key)
        if d is None:
            continue
        kind, line, subj, plural, form, pred, pre = d
        if len(ts) == 2:
            placebo.append({"kind": kind, "line": line, "text": pre + say(subj, plural, form, pred, "both") + ".",
                            "cells": [[sid, f"{key}|True"], [sid, f"{key}|False"]]})
            continue
        t = next(iter(ts))
        cell = f"{key}|{'False' if t == 'True' else 'True'}"
        w = first_hit(lambda i: (sid, cell) in fz_cells[i])
        mode = "always" if t == "True" else "never"
        facts.append({"kind": kind, "line": line, "cell": [sid, cell], "witness": w,
                      "text": pre + say(subj, plural, form, pred, mode) + "."})

    # Only mutmut supplies mutants; the two frozen 80-point sampling strata are retained.
    pts = enumerate_mutants(put_src, directory)
    order = [p['k'] for p in pts if not p['extended']]
    extra = [p['k'] for p in pts if p['extended']]
    random.Random(SEED).shuffle(order); random.Random(SEED).shuffle(extra)
    n_surv = n_equiv = 0
    mfns, plain = {}, {}
    for k in sorted(order[:80]+extra[:80]):
        p = pts[k]
        try:
            mg = load_module(p['mutant_src']); mfn = mg[entry]
        except BaseException:
            continue
        _, mok = run_base(mfn, he['test'], record=False, ns=mg)
        common = dict(kind='MUTANT', **{key:p[key] for key in
                      ('line','k','family','extended','operator','mutant_src')})
        if mok is not True:
            placebo.append(dict(common, text=t_mutant(p['line'],p['before'],p['after'],p['family'],True)))
            continue
        n_surv += 1
        w = None
        for i,a in enumerate(fz):
            st,val = call(mfn,a)
            if i not in plain: plain[i] = call(put,a)
            pst,pval = plain[i]
            if st!=pst or (st=='ok' and not same(val,pval)):
                w = i; break
        if w is None:
            n_equiv += 1; continue
        facts.append(dict(common,text=t_mutant(p['line'],p['before'],p['after'],p['family']),
                          witness=w,boundary=p['boundary']))
        mfns[k] = mfn
    res.update(n_points=len(pts), n_survived=n_surv, n_equiv_dropped=n_equiv,
               n_points_legacy=len(order), n_points_extended=len(extra),
               mutation_operators=sorted({p['operator'] for p in pts}))

    new_facts(put_src, sites, base_traces, fz_traces, facts, placebo)

    # dedupe identical texts, attach witness call source
    def dedupe(lst):
        seen, out = set(), []
        for f in lst:
            if f["text"] not in seen:
                seen.add(f["text"])
                out.append(f)
        return out

    facts, placebo = dedupe(facts), dedupe(placebo)
    for f in facts:
        f["reached"] = f["witness"] is not None
        f["witness_call"] = call_src(entry, fz[f["witness"]]) if f["reached"] else None

    set_blocks(put_src, facts)
    guard_features(put_src, entry, facts, sites, base_cells, fz, fz_cells, fz_lines, fz_out, mfns, put)
    for f in facts:
        f["tier"] = tier(f)
    top = pick(facts, n)
    # placebo: same kind mix as `top` where possible, seeded random
    prng = random.Random(SEED + n + 1)
    plc, pool = [], [p for p in placebo if display_slot(p) in RANK_SLOTS]
    prng.shuffle(pool)
    for f in top:
        c = next((p for p in pool if p["kind"] == f["kind"]), None) or (pool[0] if pool else None)
        if c:
            plc.append(c)
            pool.remove(c)

    res["facts"] = facts
    res["rank_version"], res["rank_k"], res["g_prime"] = "v3", K, G_PRIME
    res["gated_slots"] = list(GATED_SLOTS)
    res["top3"] = [facts.index(f) for f in top]
    res["placebo3"] = plc
    res["placebo_all"] = placebo
    res["counts"] = {k: sum(slot(f) == k for f in facts) for k in SLOTS}
    res["reached"] = {k: sum(slot(f) == k and f["reached"] for f in facts) for k in SLOTS}
    res["secs"] = round(time.time() - t0, 1)
    # Compare measurement semantics on exactly the same base inputs, without using labels.
    legacy_lines = set().union(*(trace(iput,a)[1] for a in base_args)) if base_args else set()
    res['coverage_diagnostics'] = dict(base_lines=sorted(base_lines), tracer_lines=sorted(legacy_lines),
                                     only_coverage=sorted(base_lines-legacy_lines), only_tracer=sorted(legacy_lines-base_lines),
                                     branch_exits=coverage.branches)
    return res

