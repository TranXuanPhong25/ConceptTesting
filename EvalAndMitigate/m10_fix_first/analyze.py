"""m10 numbers (host python, stdlib).  usage (from anywhere):
  python3 m10_fix_first/analyze.py A        Phase A: Part 2 fix rate per arm (out/fix_<arm>.jsonl), exact McNemar vs A0,
                                            A2 selection, memorization check, cost; writes out/best_arm.txt
  python3 m10_fix_first/analyze.py B <arm>  Phase B: M/E/FP of m10_<arm> vs A0 (= m9 adv_rerun, evaluated in m9) and the
                                            original Advanced Doc (both from inputs/ref_outcomes.json), clean intersection,
                                            Gson_4/Cli_1 sensitivity, >=1 E / >=1 M split by "fix correct"
Outcome parsing (load/row/p_mcnemar/HEAD) is m6's analyze.py (m1 -> m5 -> m6 lineage, as in m9), fisher is m2's."""
import importlib.util, json, os, re, statistics, sys
from collections import Counter

D = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(D)
os.chdir(REPO)  # the reused analysis modules use repo-relative paths
sys.path.insert(0, D)
import m10


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


A6 = _load("m6_analyze", "m6_agent_oracle/analyze.py")
fisher = _load("m2_analyze", "m2_concept_diag/analyze.py").fisher
RECS = m10.records()
IDS = [r["extra:project_name"].replace("_buggy", "") for r in RECS]
IDX = m10.idx_of_bug()
tag = lambda i: f"{i}:{IDS[i]}"
SENS = ("Gson_4", "Cli_1")


def arm_data(arm):
    """(candidates {(idx, k)}, selection {idx}, per-bug runs {pairs}) of an arm; later lines replace earlier ones."""
    rows = m10.read_jsonl(f"{m10.OUT}/fix_{arm}.jsonl")
    cand = {(r["idx"], r["k"]): r for r in rows if r["kind"] == "cand"}
    sel = {i: s for i, s in m10.selections(arm).items() if s["n"] == m10.ARMS[arm][3]}
    bug = {tuple(map(tuple, r["pairs"])): r for r in rows if r["kind"] == "bug"}
    return cand, sel, bug


def chosen(arm):
    """{idx: the selected candidate's record}, {bug: fixed/compiled/reg_ok of the bug} (bugs with every method selected)."""
    cand, sel, bugrun = arm_data(arm)
    m = {i: cand[(i, s["k"])] for i, s in sel.items()}
    b = {}
    for bug, idxs in IDX.items():
        if all(i in m for i in idxs):
            r = m[idxs[0]] if len(idxs) == 1 else bugrun.get(tuple((i, sel[i]["k"]) for i in idxs))
            if r:
                b[bug] = r
    return m, b


def phase_a():
    env = json.load(open(f"{m10.OUT}/env.json")) if os.path.exists(f"{m10.OUT}/env.json") else {}
    rep = {b for b, e in env.items() if e["fixed_check"]["fixed"]}
    print(f"# m10 Phase A: Part 2 fix rate\n\nenv: {len(env)}/60 bugs built. Harness check (offline): substituting the "
          f"developer's fixed focal methods fixes {len(rep)}/{len(env)} bugs (m9: 50/60); the rest need changes outside the "
          f"focal methods: {sorted(set(env) - rep)}")
    bad_trig = [b for b, e in env.items() if any(v == "PASS" for v in e["trigger_on_buggy"].values())]
    print(f"bugs with a trigger test passing on the buggy code (expect none): {bad_trig}")
    if env:
        reg = [len(e["regression"]) for e in env.values()]
        print(f"regression oracle per bug (relevant tests passing on buggy, trigger tests excluded): median {statistics.median(reg):.0f}, "
              f"min {min(reg)}, max {max(reg)}; tests differing between defects4j-compiled and recompiled-alone classes: "
              f"{sum(e['n_differ_d4j_vs_recompiled'] for e in env.values())}; fixed methods substituted break a regression test in: "
              f"{sorted(b for b, e in env.items() if e['fixed_check']['compiled'] and not e['fixed_check']['reg_ok'])}")
    data = {a: chosen(a) for a in m10.ARMS if os.path.exists(f"{m10.OUT}/fix_{a}.jsonl")}
    print("\n## Per arm (selected candidate per method; bugs: all focal methods of the bug substituted together)\n")
    print("| arm | methods | Part 2 | compiled | regression-safe | **fixed** | fixed & reg-safe | any trigger passes | "
          "bugs fixed | bugs fixed (reproducible) |\n|---|---|---|---|---|---|---|---|---|---|")
    for a, (m, b) in data.items():
        ms = list(m.values())
        n = lambda k: sum(bool(r.get(k)) for r in ms)
        print(f"| {a} | {len(ms)} | {n('part2')} | {n('compiled')} | {n('reg_ok')} | **{n('fixed')}** | "
              f"{sum(r['fixed'] and r['reg_ok'] for r in ms)} | {n('any_pass')} | {sum(r['fixed'] for r in b.values())}/{len(b)} | "
              f"{sum(b[x]['fixed'] for x in b if x in rep)}/{len(rep & set(b))} |")
    m9 = json.load(open(f"{m10.INP}/m9_fixrate_adv_rerun.json"))
    if "A0" in data:
        a0 = {str(i) for i, r in data["A0"][0].items() if r["fixed"]}
        m9f = {k for k, r in m9["methods"].items() if r["fixed"]}
        print(f"\nA0 vs m9's own measurement of the same completions (m9 fixrate.py: {len(m9f)} methods fixed): "
              f"only m10 {sorted(a0 - m9f, key=int)}, only m9 {sorted(m9f - a0 & set(map(str, data['A0'][0])), key=int)}")
    print("\n## Exact McNemar vs A0 (same methods / bugs)\n")
    for a in [x for x in data if x != "A0" and "A0" in data]:
        for unit, k in (("methods", 0), ("bugs", 1)):
            common = sorted(set(data["A0"][k]) & set(data[a][k]))
            o0, oa, p = A6.p_mcnemar([data["A0"][k][x]["fixed"] for x in common], [data[a][k][x]["fixed"] for x in common])
            print(f"- {a} vs A0, fixed {unit} (n={len(common)}): {sum(data[a][k][x]['fixed'] for x in common)} vs "
                  f"{sum(data['A0'][k][x]['fixed'] for x in common)}; only {a} {oa}, only A0 {o0}, p={p:.3g}")
    for a, (m, _) in data.items():
        print(f"- fixed methods {a}: " + ", ".join(tag(i) for i in sorted(m) if m[i]["fixed"]))
    if "A2" in data:
        cand, sel, _ = arm_data("A2")
        K = m10.ARMS["A2"][3]
        idx = sorted(sel)
        anyf = [any(cand[(i, k)]["fixed"] for k in range(K)) for i in idx]
        first = [cand[(i, 0)]["fixed"] for i in idx]
        chos = [cand[(i, sel[i]["k"])]["fixed"] for i in idx]
        surv_fixed = [any(cand[(i, k)]["fixed"] and cand[(i, k)]["reg_ok"] for k in range(K)) for i in idx]
        print(f"\n## A2 selection ({len(idx)} methods, K={K})\n")
        print(f"- fixed: selected {sum(chos)}, first sample only {sum(first)}, a regression-safe fixed candidate exists "
              f"{sum(surv_fixed)}, any of the K (oracle pass@{K}) {sum(anyf)}")
        o1, o2, p = A6.p_mcnemar(first, chos)
        print(f"- selected vs first sample: only selected {o2}, only first {o1}, p={p:.3g}")
        print(f"- reasons: {dict(Counter(sel[i]['reason'] for i in idx))}; survivors per method: "
              f"{dict(sorted(Counter(sel[i]['n_surv'] for i in idx).items()))}")
        dis = [i for i in idx if sel[i].get("disagree")]
        print(f"- survivors disagree on >=1 deterministic probe input: {len(dis)} methods; inputs per such method: median "
              f"{statistics.median([len(sel[i]['disagree']) for i in dis]) if dis else 0}; clusters: "
              f"{dict(Counter(tuple(sel[i]['clusters']) for i in idx if 'clusters' in sel[i]))}")
        print(f"- selected fixed among methods with / without disagreement: {sum(chos[idx.index(i)] for i in dis)}/{len(dis)} vs "
              f"{sum(c for i, c in zip(idx, chos) if i not in dis)}/{len(idx) - len(dis)}")
        for i in dis:
            print(f"  - {tag(i)}: {sel[i]['n_surv']} survivors, clusters {sel[i]['clusters']}, chosen k{sel[i]['k']} "
                  f"({'FIXED' if cand[(i, sel[i]['k'])]['fixed'] else 'not fixed'}); undetermined inputs: "
                  + "; ".join(x["input"][:80] for x in sel[i].get("disagree_inputs", [])[:3]))
    print("\n## Memorization check (offline): token similarity of the selected Part 2 to the developer's fixed method\n")
    print(f"near-verbatim = similarity to the fixed method >= {m10.NEAR_VERBATIM} and higher than to the buggy method (one-line "
          f"fixes make buggy and fixed methods alike: median buggy-vs-fixed similarity "
          + (f"{statistics.median([m10.sim(x['buggy'], x['fixed']) for e in env.values() for x in e['methods'].values() if x['fixed']]):.3f}" if env else "n/a") + ")")
    print("\n| arm | Part 2 with a fixed-method reference | identical to the developer's fix | near-verbatim | fixed among near-verbatim | "
          "fixed among the others | identical to the buggy method |\n|---|---|---|---|---|---|---|")
    for a, (m, _) in data.items():
        ref = {i: env[IDS[i]]["methods"][str(i)] for i, r in m.items()
               if r.get("focal") and IDS[i] in env and env[IDS[i]]["methods"][str(i)]["fixed"]}
        sf = {i: m10.sim(m[i]["focal"], x["fixed"]) for i, x in ref.items()}
        sb = {i: m10.sim(m[i]["focal"], x["buggy"]) for i, x in ref.items()}
        nv = [i for i in ref if sf[i] >= m10.NEAR_VERBATIM and sf[i] > sb[i]]
        ot = [i for i in ref if i not in nv]
        print(f"| {a} | {len(ref)} | {sum(sf[i] == 1.0 for i in ref)} | {len(nv)} | {sum(m[i]['fixed'] for i in nv)}/{len(nv)} | "
              f"{sum(m[i]['fixed'] for i in ot)}/{len(ot)} | {sum(sb[i] == 1.0 for i in ref)} |")
    print("\n## Cost (Vertex list price; every API attempt logged in out/llm_calls.jsonl)\n")
    usd = {"A0": sum(c["usd"] for c in m10.read_jsonl(f"{m10.INP}/m9_llm_calls_adv_rerun.jsonl"))}
    calls = m10.read_jsonl(m10.LLM_LOG)
    for a in m10.ARMS:
        cs = [c for c in calls if c.get("arm") == a]
        if cs:
            usd[a] = sum(c["usd"] for c in cs)
            billed = [c for c in cs if "in_tok" in c]
            print(f"- {a}: {len(cs)} API attempts ({len(billed)} billed), in {sum(c['in_tok'] for c in billed)} / out "
                  f"{sum(c['out_tok'] for c in billed)} / thinking {sum(c['thought_tok'] for c in billed)} tokens, ${usd[a]:.3f}; "
                  f"hit the output limit: {sum(c.get('finish') == 'FinishReason.MAX_TOKENS' for c in billed)}")
    print(f"- A0: reused m9 adv_rerun completions (${usd['A0']:.3f}, spent in m9)")
    full = [a for a in data if a != "A0" and len(data[a][0]) == len(RECS)]
    if full:
        best = max(full, key=lambda a: (sum(r["fixed"] for r in data[a][0].values()), sum(r["fixed"] for r in data[a][1].values()), -usd.get(a, 0)))
        open(f"{m10.OUT}/best_arm.txt", "w").write(best + "\n")
        print(f"\nPhase B arm (most fixed methods, then bugs, then lower cost, among complete new arms {full}): **{best}** -> out/best_arm.txt")
    else:
        print("\nno new arm is complete on all 78 methods yet: no Phase B arm chosen")


def phase_b(arm):
    ref = json.load(open(f"{m10.INP}/ref_outcomes.json"))
    ADV, A0, X = "Advanced Doc", "A0 (m9 adv_rerun)", f"m10 {arm}"
    if not os.path.exists(f"m10_fix_first/out/m10_{arm}_parts.json"):
        sys.exit(f"no evaluation of m10_{arm} yet (run.sh phaseB {arm})")
    data = {ADV: ref[ADV], A0: ref[A0], X: A6.load(f"m10_{arm}", "m10_fix_first")}
    for name, ms in data.items():
        assert [x["sig"] for x in ms] == [r["source:source_method_signature"] for r in RECS], name
    keep = [i for i in range(len(RECS)) if all(not ms[i]["glitch"] for ms in data.values())]
    print(f"# m10 Phase B: {X}\n\nglitched (empty error report, excluded): " +
          "; ".join(f"{n}: {[tag(i) for i, x in enumerate(ms) if x['glitch']]}" for n, ms in data.items()))
    for label, idx in (("all", keep), ("without Gson_4 and Cli_1", [i for i in keep if IDS[i] not in SENS])):
        print(f"\n## Intersection of clean methods, {label}: {len(idx)} methods\n\n{A6.HEAD}")
        for name, ms in data.items():
            print(A6.row(name, [ms[i] for i in idx]))
        has = lambda name, k: [data[name][i]["counts"][k] > 0 for i in idx]
        print()
        for a, b in ((A0, X), (ADV, X), (ADV, A0)):
            out = []
            for k in ("E", "M"):
                oa, ob, p = A6.p_mcnemar(has(a, k), has(b, k))
                out.append(f"≥1 {k} {sum(has(b, k))} vs {sum(has(a, k))}: only {b} {ob}, only {a} {oa}, p={p:.3g}")
            print(f"- {b} vs {a}: " + "; ".join(out))
    for a, b in ((A0, X), (ADV, X)):
        for k in ("E", "M"):
            g = [tag(i) for i in keep if data[b][i]["counts"][k] and not data[a][i]["counts"][k]]
            l = [tag(i) for i in keep if data[a][i]["counts"][k] and not data[b][i]["counts"][k]]
            print(f"- ≥1 {k}, {b} vs {a}: only {b} {g}; only {a} {l}")
    print("\nM methods (method: M tests): " + "; ".join(f"{n}: " + ", ".join(f"{tag(i)}:{ms[i]['counts']['M']}" for i in keep if ms[i]["counts"]["M"]) for n, ms in data.items()))
    print("\n## Does a correct fix give better tests? (selected Part 2 fixes the bug: offline trigger tests; Fisher on ≥1 E)\n")
    for name, fa in ((A0, "A0"), (X, arm)):
        m, _ = chosen(fa)
        f_ = [i for i in keep if i in m and m[i]["fixed"]]
        nf = [i for i in keep if i in m and not m[i]["fixed"]]
        e1 = lambda ix: sum(data[name][i]["counts"]["E"] > 0 for i in ix)
        m1 = lambda ix: sum(data[name][i]["counts"]["M"] > 0 for i in ix)
        print(f"- {name}: ≥1 E fixed {e1(f_)}/{len(f_)} vs not fixed {e1(nf)}/{len(nf)} (p={fisher(e1(f_), len(f_) - e1(f_), e1(nf), len(nf) - e1(nf)):.3g}); "
              f"≥1 M {m1(f_)}/{len(f_)} vs {m1(nf)}/{len(nf)}")
    sel = m10.selections(arm)
    und = [i for i in keep if m10.undetermined_lines(sel.get(i, {}))]
    if und:
        rest = [i for i in keep if i not in und]
        e1 = lambda ix: sum(data[X][i]["counts"]["E"] > 0 for i in ix)
        m1 = lambda ix: sum(data[X][i]["counts"]["M"] > 0 for i in ix)
        print(f"- {X}, methods with Undetermined lines: ≥1 E {e1(und)}/{len(und)} vs without {e1(rest)}/{len(rest)}; "
              f"≥1 M {m1(und)}/{len(und)} vs {m1(rest)}/{len(rest)}")
    M5 = _load("m5_spec", "m5_blind_concept_spec/spec.py")
    docs = m10.read_jsonl(m10.DOC_OUT.format(arm))
    print(f"\nDocstrings quoting >=40-char windows of the buggy focal body (m5 body_leaks; reach the test prompt): "
          f"{[tag(i) for i, d in enumerate(docs) if M5.body_leaks(RECS[i], d['generated_docstring'])]}")
    rq1 = f"data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_m10_{arm}_with_completion.jsonl"
    rs = m10.read_jsonl(rq1)
    tok = lambda t: sum(ch.isdigit() for ch in t) + sum(not ch.isdigit() for ch in t) / 4.0  # m9's estimate (within 4%)
    usd = sum(tok(r["content"]) * 0.30e-6 + tok(r.get("completion") or "") * 2.50e-6 for r in rs)
    print(f"Test generation: {len(rs)} completions (one call each, Flash thinking off, upstream settings), estimated ${usd:.2f}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["A"]:
        phase_a()
    elif sys.argv[1:2] == ["B"]:
        phase_b(sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "best" else open(f"{m10.OUT}/best_arm.txt").read().strip())
    else:
        sys.exit(__doc__)
