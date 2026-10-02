"""Numbers for RESULTS.md (host python, stdlib only).  usage: python3 m3_concept_spec/analyze.py
Per-method outcomes come from the evaluation logs (m1_test_review/analyze.py `parse`), with this folder's resumed part
logs merged in the order of out/<arm>_parts.json. Configs are compared on the intersection of their clean methods."""
import importlib.util, json, os, statistics, sys
from collections import Counter

_spec = importlib.util.spec_from_file_location("m1_analyze", "m1_test_review/analyze.py")
m1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(m1)
sys.path.insert(0, "m3_concept_spec")
import spec as S

D = "m3_concept_spec"
DOC = "data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_{}.jsonl"
CONFIGS = [("Doc W/ Code (ref.)", "unified_invoked_docstring_code_prompt", "docstring"),
           ("Only Doc", "unified_invoked_docstring_prompt", "docstring"),
           ("Advanced Doc", "unified_invoked_advanced_docstring_prompt", "advanced_docstring_base_cot_code"),
           ("Concept-Spec", "m3_concept_spec", "m3_concept_spec"),
           ("Placebo-Spec", "m3_concept_placebo", "m3_concept_placebo")]
KEYS = ("M", "E", "TN", "FP")


def load(fpf):
    """per-method blocks; merges resumed parts (out/<fpf>_parts.json) and applies redo parts."""
    plan = f"{D}/out/{fpf}_parts.json"
    parts = json.load(open(plan)) if os.path.exists(plan) else [{"fpf": fpf, "n": None}]
    meths = [m for p in parts if "idx" not in p for m in m1.parse(m1.latest_log(p["fpf"]), p["n"])]
    for p in parts:
        for i, m in zip(p.get("idx", []), m1.parse(m1.latest_log(p["fpf"]))):
            assert meths[i]["sig"] == m["sig"]
            meths[i] = m
    return meths


def mcnemar(a, b):
    return m1.mcnemar(a, b).replace("p=0.000", "p<0.001") + (f" (p={_p(a, b):.1e})" if _p(a, b) < 0.001 else "")


def _p(a, b):
    from math import comb
    n01 = sum(x and not y for x, y in zip(a, b)); n10 = sum(y and not x for x, y in zip(a, b)); n = n01 + n10
    return min(1.0, 2 * sum(comb(n, k) for k in range(min(n01, n10) + 1)) / 2 ** n) if n else 1.0


def row(name, ms):
    tot = {k: sum(m["counts"][k] for m in ms) for k in KEYS}; gen = sum(m["counts"]["GEN"] for m in ms)
    return m1.row(name, tot, gen, ms)


def dist(xs):
    q = statistics.quantiles(xs, n=4)
    return f"min {min(xs)} · Q1 {q[0]:.0f} · median {statistics.median(xs):.0f} · Q3 {q[2]:.0f} · max {max(xs)} · mean {statistics.mean(xs):.0f}"


def main():
    data = {name: load(fpf) for name, fpf, _ in CONFIGS}
    sigs = [m["sig"] for m in data["Only Doc"]]
    ids = [json.loads(l)["extra:project_name"] for l in open(DOC.format("docstring"))]
    for name, ms in data.items():
        assert [m["sig"] for m in ms] == sigs, f"method order differs: {name}"
    glitched = {name: [i for i, m in enumerate(ms) if m["glitch"]] for name, ms in data.items()}
    keep = [i for i in range(len(sigs)) if not any(i in g for g in glitched.values())]
    print("glitched (excluded):", {n: [ids[i] for i in g] for n, g in glitched.items()})
    print(f"\n## Intersection of clean methods: {len(keep)} of {len(sigs)}\n")
    print("| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |\n|---|---|---|---|---|---|---|---|")
    for name, ms in data.items():
        print(row(name, [ms[i] for i in keep]))
    print(f"\nsensitivity, without the 6 Gson_4 methods (one bug) and Cli_1 (M in every config):\n")
    sub = [i for i in keep if ids[i] not in ("Gson_4_buggy", "Cli_1_buggy")]
    print("| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |\n|---|---|---|---|---|---|---|---|")
    for name, ms in data.items():
        print(row(f"{name} ({len(sub)} methods)", [ms[i] for i in sub]))
    has = lambda name, k: [data[name][i]["counts"][k] > 0 for i in keep]
    print()
    for a, b in (("Advanced Doc", "Concept-Spec"), ("Placebo-Spec", "Concept-Spec"), ("Only Doc", "Concept-Spec"),
                 ("Advanced Doc", "Placebo-Spec"), ("Only Doc", "Placebo-Spec")):
        print(f"McNemar {b} vs {a} (lost = {a} only, gained = {b} only): ≥1 E {mcnemar(has(a, 'E'), has(b, 'E'))}; "
              f"≥1 M {mcnemar(has(a, 'M'), has(b, 'M'))}")
    print("\n## Each config on its own clean methods\n")
    print("| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |\n|---|---|---|---|---|---|---|---|")
    for name, ms in data.items():
        print(row(f"{name} ({len(ms) - len(glitched[name])} methods)", [m for m in ms if not m["glitch"]]))

    labels = json.load(open("m2_concept_diag/manual_labels.json"))
    print("\n## Per bug concept (manual labels, intersection): methods with ≥1 E / ≥1 M (M/E/FP tests; red-prec)\n")
    print("| concept | n | " + " | ".join(data) + " |\n|---|---|" + "---|" * len(data))
    for c in [f"C{i}" for i in range(9)]:
        idx = [i for i in keep if c in labels[str(i)]["concepts"]]
        cells = []
        for name, ms in data.items():
            t = {k: sum(ms[i]["counts"][k] for i in idx) for k in KEYS}
            cells.append(f"E{sum(ms[i]['counts']['E'] > 0 for i in idx)} M{sum(ms[i]['counts']['M'] > 0 for i in idx)} "
                         f"({t['M']}/{t['E']}/{t['FP']}; {t['E'] / max(1, t['E'] + t['FP']):.2f})")
        print(f"| {c} | {len(idx)} | " + " | ".join(cells) + " |")

    # does the Concept-Spec state a concrete (not "unspecified") rule in the facet of the bug's own concept?
    sp = {json.loads(l)["idx"]: json.loads(l)["spec"] for l in open(f"{D}/out/specs_spec.jsonl")}
    stated = lambda i: any(isinstance(sp[i][c], list) and any(not S.is_unspecified(r) for r in sp[i][c])
                           for c in labels[str(i)]["concepts"] if c != "C0")
    idx18 = [i for i in keep if any(c != "C0" for c in labels[str(i)]["concepts"])]
    print(f"\nConcept-Spec, methods whose bug concept is in C1-C8 ({len(idx18)}): does the spec state a concrete rule in that facet?")
    for flag in (True, False):
        g = [i for i in idx18 if stated(i) == flag]
        print(f"  {'stated' if flag else 'not stated'}: {len(g)} methods; ≥1 M: Concept-Spec {sum(data['Concept-Spec'][i]['counts']['M'] > 0 for i in g)}, "
              f"Advanced {sum(data['Advanced Doc'][i]['counts']['M'] > 0 for i in g)}; ≥1 E: Concept-Spec "
              f"{sum(data['Concept-Spec'][i]['counts']['E'] > 0 for i in g)}, Advanced {sum(data['Advanced Doc'][i]['counts']['E'] > 0 for i in g)}")

    print("\n## Docstring length (chars of `generated_docstring`, all 78 methods)\n")
    lens = {}
    for name, _, doc in CONFIGS[1:]:
        lens[name] = [len(json.loads(l)["generated_docstring"]) for l in open(DOC.format(doc))]
        print(f"- {name}: {dist(lens[name])}")
    for name in ("Concept-Spec", "Placebo-Spec"):
        other = lens["Placebo-Spec" if name == "Concept-Spec" else "Concept-Spec"]
        print(f"  - {name} longer than the other arm on {sum(a > b for a, b in zip(lens[name], other))}/78 methods")
    # length as a confound: E-methods by length tercile within each arm (intersection)
    for name, _, _ in CONFIGS[1:]:
        ts = statistics.quantiles([lens[name][i] for i in keep], n=3)
        cells = []
        for lo, hi in ((0, ts[0]), (ts[0], ts[1]), (ts[1], 1e9)):
            idx = [i for i in keep if lo <= lens[name][i] < hi]
            cells.append(f"{sum(data[name][i]['counts']['E'] > 0 for i in idx)}/{len(idx)}")
        print(f"  - {name}: methods ≥1 E by own length tercile (short/mid/long): {' · '.join(cells)}")

    print("\n## Spec tables\n")
    for arm, name in (("spec", "Concept-Spec"), ("placebo", "Placebo-Spec")):
        recs = [json.loads(l) for l in open(f"{D}/out/specs_{arm}.jsonl")]
        facets = [k for k, _, _ in S.FACETS[arm]]
        rules = [(k, r) for x in recs for k in facets if isinstance(x["spec"][k], list) for r in x["spec"][k]]
        un = sum(S.is_unspecified(r) for _, r in rules)
        na = Counter(k for x in recs for k in facets if x["spec"][k] == "not applicable")
        per = Counter(k for k, _ in rules); unk = Counter(k for k, r in rules if S.is_unspecified(r))
        src = Counter(r["source"] for _, r in rules)
        calls = sum(x["calls"] for x in recs)
        print(f"- {name}: {len(recs)} specs, spec-generation LLM calls {calls} (re-asks {calls - len(recs)}; "
              f"methods with ≥1 re-ask {sum(x['calls'] > 1 for x in recs)}), missing keys {sum(len(x['spec']['missing_keys']) for x in recs)}")
        print(f"  rules {len(rules)} ({len(rules) / len(recs):.1f}/method), unspecified {un} ({100 * un / len(rules):.1f}%); "
              f"methods with ≥1 unspecified rule {sum(any(S.is_unspecified(r) for k in facets if isinstance(x['spec'][k], list) for r in x['spec'][k]) for x in recs)}")
        print("  per facet (rules / unspecified / methods 'not applicable'): " +
              "; ".join(f"{k} {per[k]}/{unk[k]}/{na[k]}" for k in facets))
        print(f"  sources: {dict(src.most_common())}")


if __name__ == "__main__":
    main()
