"""Numbers for RESULTS.md (host python, stdlib only).  usage: python3 m4_concept_inputs/analyze.py
Per-method outcomes come from the evaluation logs (m1_test_review/analyze.py `parse`); resumed part logs are merged in the
order of <folder>/out/<fpf>_parts.json. Configs are compared on the intersection of their clean methods."""
import importlib.util, json, os, statistics
from math import comb

_spec = importlib.util.spec_from_file_location("m1_analyze", "m1_test_review/analyze.py")
m1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(m1)

D = "m4_concept_inputs"
DOC = "data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_{}.jsonl"
RQ1 = "data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{}_with_completion.jsonl"
# name, FILE_POST_FIX, folder holding its parts plan (None: a single log)
CONFIGS = [("Only Doc (ref.)", "unified_invoked_docstring_prompt", None),
           ("Advanced Doc", "unified_invoked_advanced_docstring_prompt", None),
           ("Concept-Inputs", "m4_concept_inputs", D),
           ("Placebo-Inputs", "m4_placebo_inputs", D)]
M3 = ("m3 Concept-Spec (ref.)", "m3_concept_spec", "m3_concept_spec")
KEYS = ("M", "E", "TN", "FP")
HEAD = "| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |\n|---|---|---|---|---|---|---|---|"


def load(fpf, folder):
    plan = f"{folder}/out/{fpf}_parts.json" if folder else None
    parts = json.load(open(plan)) if plan and os.path.exists(plan) else [{"fpf": fpf, "n": None}]
    meths = [m for p in parts if "idx" not in p for m in m1.parse(m1.latest_log(p["fpf"]), p["n"])]
    for p in parts:  # redo parts replace infrastructure-failed blocks
        for i, m in zip(p.get("idx", []), m1.parse(m1.latest_log(p["fpf"]))):
            assert meths[i]["sig"] == m["sig"]
            meths[i] = m
    return meths


def p_mcnemar(a, b):
    n01 = sum(x and not y for x, y in zip(a, b)); n10 = sum(y and not x for x, y in zip(a, b)); n = n01 + n10
    return n01, n10, (min(1.0, 2 * sum(comb(n, k) for k in range(min(n01, n10) + 1)) / 2 ** n) if n else 1.0)


def row(name, ms):
    tot = {k: sum(m["counts"][k] for m in ms) for k in KEYS}
    return m1.row(name, tot, sum(m["counts"]["GEN"] for m in ms), ms)


def dist(xs):
    q = statistics.quantiles(xs, n=4)
    return f"min {min(xs)} · Q1 {q[0]:.0f} · median {statistics.median(xs):.0f} · Q3 {q[2]:.0f} · max {max(xs)} · mean {statistics.mean(xs):.0f}"


def main():
    data = {name: load(fpf, folder) for name, fpf, folder in CONFIGS}
    ids = [json.loads(l)["extra:project_name"] for l in open(DOC.format("docstring"))]
    sigs = [m["sig"] for m in data["Advanced Doc"]]
    for name, ms in data.items():
        assert [m["sig"] for m in ms] == sigs, f"method order differs: {name}"
    glitched = {name: [i for i, m in enumerate(ms) if m["glitch"]] for name, ms in data.items()}
    keep = [i for i in range(len(sigs)) if not any(i in g for g in glitched.values())]
    print("glitched (excluded):", {n: [ids[i] for i in g] for n, g in glitched.items()})
    sub = {"all": keep, "no Gson_4": [i for i in keep if ids[i] != "Gson_4_buggy"]}

    for label, idx in sub.items():
        print(f"\n## Intersection of clean methods, {label}: {len(idx)} methods\n\n{HEAD}")
        for name, ms in data.items():
            print(row(name, [ms[i] for i in idx]))
        has = lambda name, k: [data[name][i]["counts"][k] > 0 for i in idx]
        print()
        for a, b in (("Advanced Doc", "Concept-Inputs"), ("Placebo-Inputs", "Concept-Inputs"),
                     ("Advanced Doc", "Placebo-Inputs"), ("Only Doc (ref.)", "Concept-Inputs")):
            out = []
            for k in ("E", "M"):
                lost, gained, p = p_mcnemar(has(a, k), has(b, k))
                out.append(f"≥1 {k} {sum(has(b, k))} vs {sum(has(a, k))}: lost {lost}, gained {gained}, p={p:.3f}")
            print(f"McNemar {b} vs {a}: " + "; ".join(out))

    tag = lambda i: f"{ids[i].replace('_buggy', '')}.{sigs[i].split('#')[2].split('(')[0]}"
    print("\n## Per-method changes vs Advanced Doc (intersection)")
    for arm in ("Concept-Inputs", "Placebo-Inputs"):
        for k in ("E", "M"):
            g = [tag(i) for i in keep if data[arm][i]["counts"][k] and not data["Advanced Doc"][i]["counts"][k]]
            l = [tag(i) for i in keep if data["Advanced Doc"][i]["counts"][k] and not data[arm][i]["counts"][k]]
            print(f"- {arm} ≥1 {k}: gained {g}; lost {l}")
    print("\nM-methods per config (method: M tests):")
    for name, ms in data.items():
        print(f"- {name}: " + ", ".join(f"{tag(i)}:{ms[i]['counts']['M']}" for i in keep if ms[i]["counts"]["M"]))
    always = [i for i in keep if all(ms[i]["counts"]["M"] for ms in data.values())]
    print(f"M tests without the methods that are M in every config ({[tag(i) for i in always]}): " +
          ", ".join(f"{name} {sum(ms[i]['counts']['M'] for i in keep if i not in always)}" for name, ms in data.items()))

    print("\n## Gson_4 (one bug, 6 methods) share of each config (intersection)")
    g4 = [i for i in keep if ids[i] == "Gson_4_buggy"]
    for name, ms in data.items():
        t = {k: sum(ms[i]["counts"][k] for i in g4) for k in KEYS}
        print(f"- {name}: E {t['E']}, M {t['M']}, FP {t['FP']}; methods ≥1 E {sum(ms[i]['counts']['E'] > 0 for i in g4)}")

    labels = json.load(open("m2_concept_diag/manual_labels.json"))
    items = {arm: {r["idx"]: r for r in map(json.loads, open(f"{D}/out/items_{arm}.jsonl"))} for arm in ("concept", "placebo")}
    print("\n## Per bug concept (manual labels, intersection): methods ≥1 E / ≥1 M (M/E/FP tests; red-prec)\n")
    print("| concept | n | " + " | ".join(data) + " |\n|---|---|" + "---|" * len(data))
    for c in [f"C{i}" for i in range(9)]:
        idx = [i for i in keep if c in labels[str(i)]["concepts"]]
        cells = []
        for name, ms in data.items():
            t = {k: sum(ms[i]["counts"][k] for i in idx) for k in KEYS}
            cells.append(f"E{sum(ms[i]['counts']['E'] > 0 for i in idx)} M{sum(ms[i]['counts']['M'] > 0 for i in idx)} "
                         f"({t['M']}/{t['E']}/{t['FP']}; {t['E'] / max(1, t['E'] + t['FP']):.2f})")
        print(f"| {c} | {len(idx)} | " + " | ".join(cells) + " |")
    # is the bug's own concept among the listed facets?
    idx18 = [i for i in keep if any(c != "C0" for c in labels[str(i)]["concepts"])]
    listed = lambda i: any(k in labels[str(i)]["concepts"] for k, _ in items["concept"][i]["items"] if k != "C0")
    print(f"\nConcept-Inputs, methods whose bug concept is in C1-C8 ({len(idx18)}): is an item of that concept in the list?")
    for flag in (True, False):
        g = [i for i in idx18 if listed(i) == flag]
        cnt = lambda name, k: sum(data[name][i]["counts"][k] > 0 for i in g)
        print(f"  {'listed' if flag else 'not listed'}: {len(g)} methods; ≥1 E Concept-Inputs {cnt('Concept-Inputs', 'E')}, "
              f"Placebo {cnt('Placebo-Inputs', 'E')}, Advanced {cnt('Advanced Doc', 'E')}; ≥1 M Concept-Inputs "
              f"{cnt('Concept-Inputs', 'M')}, Placebo {cnt('Placebo-Inputs', 'M')}, Advanced {cnt('Advanced Doc', 'M')}")

    print("\n## Appended section (all 78 methods)")
    for arm in ("concept", "placebo"):
        rs = [items[arm][i] for i in sorted(items[arm])]
        print(f"- {arm}: items {dist([len(r['items']) for r in rs])}; chars {dist([r['section_chars'] for r in rs])}")
    adv = [len(json.loads(l)["generated_docstring"]) for l in open(DOC.format("advanced_docstring_base_cot_code"))]
    print(f"- Advanced docstring chars (unchanged part): {dist(adv)}")
    # methods ≥1 E by length tercile of the appended section, per arm (a crude check of a length effect)
    for arm, name in (("concept", "Concept-Inputs"), ("placebo", "Placebo-Inputs")):
        L = {i: items[arm][i]["section_chars"] for i in keep}
        ts = statistics.quantiles(L.values(), n=3)
        cells = [f"{sum(data[name][i]['counts']['E'] > 0 for i in keep if lo <= L[i] < hi)}/{sum(lo <= L[i] < hi for i in keep)}"
                 for lo, hi in ((0, ts[0]), (ts[0], ts[1]), (ts[1], 1e9))]
        print(f"  - {name}: methods ≥1 E by section-length tercile (short/mid/long): {' · '.join(cells)}")

    print("\n## LLM calls")
    for name, fpf, _ in CONFIGS[2:]:
        recs = [json.loads(l) for l in open(RQ1.format(fpf))]
        print(f"- {name}: test-generation records {len(recs)}, with a ```java block {sum('```java' in (r.get('completion') or '') for r in recs)}")
    for arm in ("spec", "placebo"):
        print(f"- m3 specs_{arm}.jsonl (reused, not re-run): {sum(json.loads(l)['calls'] for l in open(f'm3_concept_spec/out/specs_{arm}.jsonl'))} calls")

    # reference: m3 Concept-Spec (same spec tables, used as oracles) on the intersection with its clean methods
    m3 = load(M3[1], M3[2])
    k3 = [i for i in keep if not m3[i]["glitch"]]
    print(f"\n## Reference: same spec tables as oracles (m3) vs as inputs, {len(k3)} methods\n\n{HEAD}")
    for name, ms in list(data.items())[1:] + [(M3[0], m3)]:
        print(row(name, [ms[i] for i in k3]))


if __name__ == "__main__":
    main()
