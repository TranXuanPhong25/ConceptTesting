"""m8 Phase 0 numbers (host python, stdlib): mutants / compile rate / smoke-equivalence per concept, the selection with an
equal mutant count per method, and the mechanism check (bug-touching, fix-direction) concept vs generic, cross-tabulated
with m2's manual bug-concept labels. Trigger tests and the fixed version are used here only (offline analysis).

usage: python3 m8_concept_mutants/analyze0.py > m8_concept_mutants/out/phase0_analysis.txt   (also writes out/selection.json)
"""
import json, sys
from collections import Counter, defaultdict
from math import comb

D = "m8_concept_mutants"
CAP = 40
CONCEPTS = [f"C{i}" for i in range(1, 9)]


def p_mcnemar(a, b):
    """exact two-sided McNemar on paired booleans; returns (only a, only b, p)."""
    n01 = sum(x and not y for x, y in zip(a, b)); n10 = sum(y and not x for x, y in zip(a, b)); n = n01 + n10
    return n01, n10, (min(1.0, 2 * sum(comb(n, k) for k in range(min(n01, n10) + 1)) / 2 ** n) if n else 1.0)


def load():
    muts = [json.loads(l) for l in open(f"{D}/out/mutants.jsonl")]
    runs = {r["mid"]: r for r in map(json.loads, open(f"{D}/out/phase0_runs.jsonl"))}
    base = json.load(open(f"{D}/out/phase0_base.json"))
    env = json.load(open(f"{D}/out/env.json"))
    labels = json.load(open("m2_concept_diag/manual_labels.json"))
    return muts, runs, base, env, labels


def stable(b):
    """per test: 'excl' (status unstable across the original runs), 'status' (message unstable), 'full'."""
    out = {}
    for t, o in b["orig"].items():
        obs = [b[k].get(t) for k in ("orig", "orig2", "d4j")]
        out[t] = "excl" if len({x[0] for x in obs if x}) > 1 else "status" if len({x[1] for x in obs if x}) > 1 else "full"
    return out


def changes(r, b, st, tests, timeouts=True):
    """tests whose outcome differs from the recompiled original."""
    out = []
    for t in tests:
        if st.get(t, "excl") == "excl" or t not in r.get("tests", {}):
            continue
        m, o = r["tests"][t], b["orig"][t]
        if not timeouts and m[0] == "TIMEOUT":
            continue
        if m[0] != o[0] or (st[t] == "full" and m[1] != o[1]):
            out.append(t)
    return out


def fixes(r, b, st, tests):
    return [t for t in tests if st.get(t) != "excl" and b["orig"][t][0] != "PASS" and r.get("tests", {}).get(t, [""])[0] == "PASS"]


def main():
    muts, runs, base, env, labels = load()
    missing = [mu["mid"] for m in muts for mu in m["mutants"] if mu["mid"] not in runs]
    print(f"# m8 Phase 0 (offline, no LLM)\n\ncandidates without a run record: {len(missing)}")

    # ---- per concept: generated, compiled, equivalence
    gen_all, kept, comp, ident, usable, smoke_eq, comp_eq = (Counter() for _ in range(7))
    by_op = defaultdict(Counter)
    sel = {}
    for m in muts:
        i, b = m["idx"], base[str(m["idx"])]
        st = stable(b)
        alltests = list(b["orig"])
        usable_arm = {"concept": [], "generic": []}
        seen = {"concept": set(), "generic": set()}
        for mu in m["mutants"]:
            r = runs.get(mu["mid"])
            c, op = mu["concept"], mu["op"]
            kept[c] += 1; by_op[op]["kept"] += 1
            if not r or not r["compiled"]:
                continue
            comp[c] += 1; by_op[op]["compiled"] += 1
            if r["cls_md5"] == b["cls_md5"]:
                ident[c] += 1; comp_eq[c] += 1; by_op[op]["identical"] += 1
                continue
            eq = not changes(r, b, st, alltests)
            comp_eq[c] += eq
            if r["cls_md5"] in seen[mu["arm"]]:
                continue  # same bytecode as an earlier mutant of this arm
            seen[mu["arm"]].add(r["cls_md5"])
            usable[c] += 1; smoke_eq[c] += eq; by_op[op]["usable"] += 1; by_op[op]["smoke_eq"] += eq
            usable_arm[mu["arm"]].append(mu["mid"])
        n = min(len(usable_arm["concept"]), len(usable_arm["generic"]), CAP)
        sel[i] = {"n": n, "concept": usable_arm["concept"][:n], "generic": usable_arm["generic"][:n],
                  "concept_all": usable_arm["concept"][:CAP], "generic_all": usable_arm["generic"][:CAP]}
    print("\n## Mutants per concept (all 78 methods)\n")
    print("| concept | candidates kept (≤80/method/arm) | compiled | compile rate | bytecode = original | usable (distinct bytecode) | "
          "smoke-equivalent among compiled | smoke-equivalent among usable | selected (equal n) |\n|---|---|---|---|---|---|---|---|---|")
    selc = Counter(runs[mid]["concept"] for s in sel.values() for arm in ("concept", "generic") for mid in s[arm])
    for c in CONCEPTS + ["G"]:
        print(f"| {c} | {kept[c]} | {comp[c]} | {100 * comp[c] / max(1, kept[c]):.0f}% | {ident[c]} | {usable[c]} | "
              f"{comp_eq[c]} ({100 * comp_eq[c] / max(1, comp[c]):.0f}%) | {smoke_eq[c]} ({100 * smoke_eq[c] / max(1, usable[c]):.0f}%) | {selc[c]} |")
    tc = lambda d, ks: sum(d[k] for k in ks)
    print(f"| all concept | {tc(kept, CONCEPTS)} | {tc(comp, CONCEPTS)} | {100 * tc(comp, CONCEPTS) / tc(kept, CONCEPTS):.0f}% | "
          f"{tc(ident, CONCEPTS)} | {tc(usable, CONCEPTS)} | {tc(comp_eq, CONCEPTS)} ({100 * tc(comp_eq, CONCEPTS) / tc(comp, CONCEPTS):.0f}%) | "
          f"{tc(smoke_eq, CONCEPTS)} ({100 * tc(smoke_eq, CONCEPTS) / tc(usable, CONCEPTS):.0f}%) | {tc(selc, CONCEPTS)} |")
    print("\nsmoke run = the bug's trigger tests + the developer tests that invoke the focal method; 'equivalent' = no outcome "
          "change on any of them (an upper bound on true equivalence). Candidate totals before the 80 cap: concept "
          f"{sum(m['n_all']['concept'] for m in muts)}, generic {sum(m['n_all']['generic'] for m in muts)}.")
    print("\nper operator: kept / compiled / usable / smoke-equivalent among usable")
    for op in sorted(by_op):
        x = by_op[op]
        print(f"- {op}: {x['kept']} / {x['compiled']} / {x['usable']} / {x['smoke_eq']}")
    ns = [s["n"] for s in sel.values()]
    print(f"\n## Selection: equal n per method = min(usable concept, usable generic, {CAP})\n- total per arm {sum(ns)}; "
          f"methods with n=0: {sum(n == 0 for n in ns)}; n<5: {sum(n < 5 for n in ns)}; median {sorted(ns)[len(ns) // 2]}; "
          f"methods where the concept arm lost usable mutants to the equal-n rule: "
          f"{sum(len(s['concept_all']) > s['n'] for s in sel.values())} (usable concept capped at {CAP}: {sum(len(s['concept_all']) for s in sel.values())})")
    json.dump(sel, open(f"{D}/out/selection.json", "w"), indent=1)

    # ---- mechanism check per bug
    bugs = sorted({m["bug"] for m in muts})
    meth_of = defaultdict(list)
    for m in muts:
        meth_of[m["bug"]].append(m["idx"])
    sets = ("concept", "generic", "concept_all", "generic_all")

    def per_bug(kind, fix=False, timeouts=True, concept=None):
        out = {}
        for bg in bugs:
            trig = env["bugs"][bg]["trigger"]
            hit = False
            for i in meth_of[bg]:
                b = base[str(i)]; st = stable(b)
                for mid in sel[i][kind]:
                    r = runs[mid]
                    if concept and r["concept"] != concept:
                        continue
                    if fixes(r, b, st, trig) if fix else changes(r, b, st, trig, timeouts):
                        hit = True; break
                if hit:
                    break
            out[bg] = hit
        return out

    res = {(fx, k): per_bug(k, fx) for fx in (False, True) for k in sets}
    res_not = {k: per_bug(k, timeouts=False) for k in sets}
    print(f"\n## Mechanism check (per bug, n={len(bugs)}; trigger tests, offline)\n")
    print("| mutant set | bug-touching | bug-touching (timeouts not counted) | fix-direction |\n|---|---|---|---|")
    for k in sets:
        bt, fx, bn = sum(res[(False, k)].values()), sum(res[(True, k)].values()), sum(res_not[k].values())
        print(f"| {k} | {bt} ({100 * bt / len(bugs):.0f}%) | {bn} ({100 * bn / len(bugs):.0f}%) | {fx} ({100 * fx / len(bugs):.0f}%) |")
    for fx, name in ((False, "bug-touching"), (True, "fix-direction")):
        for a, b in (("generic", "concept"), ("generic_all", "concept_all")):
            va, vb = [res[(fx, a)][x] for x in bugs], [res[(fx, b)][x] for x in bugs]
            oa, ob, p = p_mcnemar(va, vb)
            print(f"- {name}, {b} vs {a}: only {b} {ob}, only {a} {oa}, exact McNemar p={p:.3g}")
    for fx, name in ((False, "bug-touching"), (True, "fix-direction")):
        only_c = [x for x in bugs if res[(fx, "concept")][x] and not res[(fx, "generic")][x]]
        only_g = [x for x in bugs if res[(fx, "generic")][x] and not res[(fx, "concept")][x]]
        print(f"- {name} (selected sets): only concept {only_c}; only generic {only_g}")
    neither = [x for x in bugs if not res[(False, "concept_all")][x] and not res[(False, "generic_all")][x]]
    print(f"- bugs touched by no usable mutant of either arm: {neither}")
    fixers = defaultdict(list)
    for m in muts:
        b = base[str(m["idx"])]; st = stable(b)
        for k in ("concept", "generic"):
            for mid in sel[m["idx"]][k]:
                if fixes(runs[mid], b, st, env["bugs"][m["bug"]]["trigger"]):
                    mu = next(x for x in m["mutants"] if x["mid"] == mid)
                    fixers[m["bug"]].append(f"{mu['op']}: {mu['desc'][:90]}")
    print("\nfix-direction mutants (selected sets), per bug:")
    for bg in bugs:
        if fixers[bg]:
            print(f"- {bg}: " + " | ".join(fixers[bg][:6]) + (f" (+{len(fixers[bg]) - 6})" if len(fixers[bg]) > 6 else ""))

    # ---- cross-tab with manual labels (union over the bug's focal methods)
    blab = {bg: sorted({c for i in meth_of[bg] for c in labels[str(i)]["concepts"]}) for bg in bugs}
    print("\n## Cross-tab with m2 manual bug-concept labels (selected sets)\n")
    print("| label | bugs | concept arm touching | matching-concept mutants touching | generic touching | concept fix-dir | matching fix-dir | generic fix-dir |")
    print("|---|---|---|---|---|---|---|---|")
    for c in ["C0"] + CONCEPTS:
        bs = [bg for bg in bugs if c in blab[bg]]
        if not bs:
            continue
        cell = lambda d: f"{sum(d[x] for x in bs)}"
        if c != "C0":
            mts, mfs = cell(per_bug("concept", concept=c)), cell(per_bug("concept", True, concept=c))
        else:
            mts = mfs = "–"
        print(f"| {c} | {len(bs)} | {cell(res[(False, 'concept')])} | {mts} | {cell(res[(False, 'generic')])} | "
              f"{cell(res[(True, 'concept')])} | {mfs} | {cell(res[(True, 'generic')])} |")
    print("\n'matching-concept mutants': only the concept arm's selected mutants of the label's concept count.")
    print("\nper concept of the operator (selected concept mutants): bugs where that concept had ≥1 selected mutant / of those, bugs it touched")
    for c in CONCEPTS:
        has = [bg for bg in bugs if any(runs[mid]["concept"] == c for i in meth_of[bg] for mid in sel[i]["concept"])]
        t = per_bug("concept", concept=c)
        print(f"- {c}: {len(has)} / {sum(t[x] for x in has)} (labelled {c}: {sum(c in blab[x] for x in has)} / "
              f"{sum(t[x] for x in has if c in blab[x])})")

    bt = sum(res[(False, "concept")].values())
    print(f"\n## Gate (pre-registered in README.md)\nselected concept mutants bug-touching on {bt}/{len(bugs)} bugs "
          f"({100 * bt / len(bugs):.1f}%); threshold 30% (18 bugs) -> {'PASS: go to Phase 1' if bt >= 18 else 'FAIL: stop'}")


if __name__ == "__main__":
    main()
