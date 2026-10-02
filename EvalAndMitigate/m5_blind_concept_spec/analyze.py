"""Numbers for RESULTS.md (host python, stdlib only).  usage: python3 m5_blind_concept_spec/analyze.py
Per-method outcomes come from the evaluation logs (parse/latest_log/row copied from m1_test_review/analyze.py); resumed
part logs are merged in the order of <folder>/out/<fpf>_parts.json. Configs are compared on the intersection of their
clean methods. Also writes out/m_methods.txt (M tests + spec rules per misguided method, for the manual check)."""
import glob, json, os, re, statistics, sys
from collections import Counter
from math import comb

sys.path.insert(0, "m5_blind_concept_spec")
import spec as S  # FACETS, is_unspecified (copies of m3's)

D = "m5_blind_concept_spec"
LOGS = "data/rq1/logs/Gemini-2-5-flash_gen_test_evaluate_buggy_gen_test_non_private_or_default_{}_log_*.log"
DOC = "data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_{}.jsonl"
RQ1 = "data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{}_with_completion.jsonl"
KEYS = {"M": "reported test passed on buggy but failed on fixed", "E": "reported test passed on fixed but failed on buggy",
        "TN": "reported test passed on both", "FP": "reported test failed on both", "GEN": "Total test generated"}
# name, FILE_POST_FIX, folder holding its parts plan (None: a single log), docstring file, spec table (None: free text)
CONFIGS = [("Only Doc", "unified_invoked_docstring_prompt", None, "docstring", None),
           ("Advanced Doc", "unified_invoked_advanced_docstring_prompt", None, "advanced_docstring_base_cot_code", None),
           ("m3 Concept-Spec", "m3_concept_spec", "m3_concept_spec", "m3_concept_spec", "m3_concept_spec/out/specs_spec.jsonl"),
           ("A blind", "m5_blind_concept", D, "m5_blind_concept", f"{D}/out/specs_blind_concept.jsonl"),
           ("B blind+Javadoc", "m5_blind_concept_javadoc", D, "m5_blind_concept_javadoc", f"{D}/out/specs_blind_concept_javadoc.jsonl")]
PAIRS = [("m3 Concept-Spec", "A blind"), ("Advanced Doc", "A blind"), ("A blind", "B blind+Javadoc"),
         ("m3 Concept-Spec", "B blind+Javadoc"), ("Advanced Doc", "B blind+Javadoc"), ("Only Doc", "A blind")]
HEAD = "| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |\n|---|---|---|---|---|---|---|---|"
LOOSE = re.compile(r"unspecified|not specified|undefined|implementation[- ](dependent|defined|specific)", re.I)


# ---- copied from m1_test_review/analyze.py
def latest_log(fpf):
    return max(glob.glob(LOGS.format(fpf)), key=lambda p: int(re.search(r"_log_(\d+)\.log$", p).group(1)))


def parse(log, n=None):
    """Per method block (first n blocks): signature, reported count diffs, per-test category {name: E|M|FP}."""
    prev, out = dict.fromkeys(KEYS, 0), []
    for block in open(log).read().split("INFO - Processing Project:")[1:][:n]:
        cur = dict(prev)
        for k, t in KEYS.items():
            found = re.findall(re.escape(t) + r": (\d+)", block)
            if found:
                cur[k] = int(found[-1])  # counters in the log are cumulative
        fails, side = {"buggy": set(), "fixed": set()}, None
        for line in block.split("INFO - Reported execution results:")[-1].splitlines() if "Reported execution results" in block else []:
            if line.startswith("INFO - buggy error report:"): side = "buggy"
            elif line.startswith("INFO - fixed error report:"): side = "fixed"
            elif line.startswith("INFO - --- ") and side: fails[side].add(line.split("::")[-1].strip())
            elif line.startswith("INFO - bug") or line.startswith("-----"): side = None
        b, f = fails["buggy"], fails["fixed"]
        cats = {**{t: "E" for t in b - f}, **{t: "M" for t in f - b}, **{t: "FP" for t in b & f}}
        diff = {k: cur[k] - prev[k] for k in KEYS}
        ran = re.search(r"buggy passed (\w+), fixed passed (\w+)", block)
        glitch = bool(ran) and any(ran.group(j) == "False" and f"{s} error empty" in block for j, s in ((1, "buggy"), (2, "fixed")))
        out.append({"sig": block.split("method signature: ")[1].split("\n")[0].strip(), "counts": diff, "cats": cats, "glitch": glitch})
        prev = cur
    return out


def row(name, ms):
    tot = {k: sum(m["counts"][k] for m in ms) for k in ("M", "E", "TN", "FP")}
    c = sum(tot.values()); pct = lambda k: f"{tot[k]} ({100 * tot[k] / max(1, c):.2f}%)"
    e1 = sum(m["counts"]["E"] > 0 for m in ms); m1 = sum(m["counts"]["M"] > 0 for m in ms)
    return f"| {name} | {sum(m['counts']['GEN'] for m in ms)} / {c} | {pct('M')} | {pct('E')} | {pct('FP')} | {tot['E'] / max(1, tot['E'] + tot['FP']):.3f} | {m1} | {e1} |"
# ----


def load(fpf, folder):
    plan = f"{folder}/out/{fpf}_parts.json" if folder else None
    parts = json.load(open(plan)) if plan and os.path.exists(plan) else [{"fpf": fpf, "n": None}]
    meths = [m for p in parts if "idx" not in p for m in parse(latest_log(p["fpf"]), p["n"])]
    for p in parts:  # redo parts replace infrastructure-failed blocks
        for i, m in zip(p.get("idx", []), parse(latest_log(p["fpf"]))):
            assert meths[i]["sig"] == m["sig"]
            meths[i] = m
    return meths


def p_mcnemar(a, b):
    """exact two-sided McNemar; a = first config, b = second; returns (only a, only b, p)."""
    n01 = sum(x and not y for x, y in zip(a, b)); n10 = sum(y and not x for x, y in zip(a, b)); n = n01 + n10
    return n01, n10, (min(1.0, 2 * sum(comb(n, k) for k in range(min(n01, n10) + 1)) / 2 ** n) if n else 1.0)


def dist(xs):
    q = statistics.quantiles(xs, n=4)
    return f"min {min(xs)} · Q1 {q[0]:.0f} · median {statistics.median(xs):.0f} · Q3 {q[2]:.0f} · max {max(xs)} · mean {statistics.mean(xs):.0f}"


def test_src(completion, name):
    m = re.search(r"void\s+" + re.escape(name) + r"\s*\(", completion or "")
    if not m:
        return "(not found)"
    s = completion.rfind("@Test", 0, m.start()); s = s if s >= 0 and m.start() - s < 200 else m.start()
    e = completion.find("@Test", m.end())
    return completion[s:e if e > 0 else len(completion)].strip()


def main():
    data = {name: load(fpf, folder) for name, fpf, folder, _, _ in CONFIGS}
    ids = [json.loads(l)["extra:project_name"] for l in open(DOC.format("docstring"))]
    sigs = [m["sig"] for m in data["Advanced Doc"]]
    for name, ms in data.items():
        assert [m["sig"] for m in ms] == sigs, f"method order differs: {name}"
    glitched = {name: [i for i, m in enumerate(ms) if m["glitch"]] for name, ms in data.items()}
    keep = [i for i in range(len(sigs)) if not any(i in g for g in glitched.values())]
    print("glitched (excluded):", {n: [ids[i] for i in g] for n, g in glitched.items()})
    tag = lambda i: f"{ids[i].replace('_buggy', '')}.{sigs[i].split('#')[2].split('(')[0]}"
    sub = {"all": keep, "without Gson_4": [i for i in keep if ids[i] != "Gson_4_buggy"],
           "without Gson_4 and Cli_1": [i for i in keep if ids[i] not in ("Gson_4_buggy", "Cli_1_buggy")]}

    for label, idx in sub.items():
        print(f"\n## Intersection of clean methods, {label}: {len(idx)} methods\n\n{HEAD}")
        for name, ms in data.items():
            print(row(name, [ms[i] for i in idx]))
        has = lambda name, k: [data[name][i]["counts"][k] > 0 for i in idx]
        print()
        for a, b in PAIRS:
            out = []
            for k in ("M", "E"):
                oa, ob, p = p_mcnemar(has(a, k), has(b, k))
                out.append(f"≥1 {k} {sum(has(b, k))} vs {sum(has(a, k))}: only {b} {ob}, only {a} {oa}, p={p:.2g}")
            print(f"McNemar {b} vs {a}: " + "; ".join(out))

    print("\n## Each config on its own clean methods\n\n" + HEAD)
    for name, ms in data.items():
        print(row(f"{name} ({len(ms) - len(glitched[name])} methods)", [m for m in ms if not m["glitch"]]))

    print("\n## Per-method changes (intersection)")
    for a, b in PAIRS[:3]:
        for k in ("M", "E"):
            g = [tag(i) for i in keep if data[b][i]["counts"][k] and not data[a][i]["counts"][k]]
            l = [tag(i) for i in keep if data[a][i]["counts"][k] and not data[b][i]["counts"][k]]
            print(f"- ≥1 {k}, {b} vs {a}: only {b} {g}; only {a} {l}")
    print("\nM-methods per config (method: M tests):")
    for name, ms in data.items():
        print(f"- {name}: " + ", ".join(f"{tag(i)}:{ms[i]['counts']['M']}" for i in keep if ms[i]["counts"]["M"]))

    labels = json.load(open("m2_concept_diag/manual_labels.json"))
    print("\n## Per bug concept (manual labels, intersection): methods ≥1 E / ≥1 M (M/E/FP tests; red-prec)\n")
    print("| concept | n | " + " | ".join(data) + " |\n|---|---|" + "---|" * len(data))
    for c in [f"C{i}" for i in range(9)]:
        idx = [i for i in keep if c in labels[str(i)]["concepts"]]
        cells = []
        for name, ms in data.items():
            t = {k: sum(ms[i]["counts"][k] for i in idx) for k in ("M", "E", "FP")}
            cells.append(f"E{sum(ms[i]['counts']['E'] > 0 for i in idx)} M{sum(ms[i]['counts']['M'] > 0 for i in idx)} "
                         f"({t['M']}/{t['E']}/{t['FP']}; {t['E'] / max(1, t['E'] + t['FP']):.2f})")
        print(f"| {c} | {len(idx)} | " + " | ".join(cells) + " |")

    print("\n## Spec tables (all 78 methods)\n")
    specs = {}
    facets = [k for k, _, _ in S.FACETS]
    for name, _, _, _, path in CONFIGS:
        if not path:
            continue
        recs = [json.loads(l) for l in open(path)]
        specs[name] = {x["idx"]: x["spec"] for x in recs}
        rules = [(k, r) for x in recs for k in facets if isinstance(x["spec"][k], list) for r in x["spec"][k]]
        un = sum(S.is_unspecified(r) for _, r in rules); loose = sum(bool(LOOSE.search(r["expected"])) for _, r in rules)
        na = Counter(k for x in recs for k in facets if x["spec"][k] == "not applicable")
        calls = sum(x["calls"] for x in recs)
        print(f"- {name}: {len(recs)} specs, spec-generation calls {calls} (re-asks {calls - len(recs)} in "
              f"{sum(x['calls'] > 1 for x in recs)} methods), missing keys {sum(len(x['spec']['missing_keys']) for x in recs)}")
        print(f"  rules {len(rules)} ({len(rules) / len(recs):.1f}/method); \"unspecified\" (whole expected) {un} ({100 * un / len(rules):.1f}%) "
              f"in {sum(any(S.is_unspecified(r) for k in facets if isinstance(x['spec'][k], list) for r in x['spec'][k]) for x in recs)} methods; "
              f"expected mentions unspecified/undefined/implementation-dependent {loose} ({100 * loose / len(rules):.1f}%)")
        print("  per facet (rules / unspecified / methods 'not applicable'): " +
              "; ".join(f"{k} {sum(f == k for f, _ in rules)}/{sum(f == k and S.is_unspecified(r) for f, r in rules)}/{na[k]}" for k in facets))
        print(f"  sources: {dict(Counter(r['source'] for _, r in rules).most_common(8))}")

    print("\n## Docstring length (chars of `generated_docstring`, all 78 methods)")
    lens = {name: [len(json.loads(l)["generated_docstring"]) for l in open(DOC.format(doc))] for name, _, _, doc, _ in CONFIGS}
    for name in lens:
        print(f"- {name}: {dist(lens[name])}")
    for name in ("A blind", "B blind+Javadoc"):
        ts = statistics.quantiles([lens[name][i] for i in keep], n=3)
        cells = [f"{sum(data[name][i]['counts']['E'] > 0 for i in keep if lo <= lens[name][i] < hi)}/{sum(lo <= lens[name][i] < hi for i in keep)}"
                 for lo, hi in ((0, ts[0]), (ts[0], ts[1]), (ts[1], 1e9))]
        print(f"  - {name}: methods ≥1 E by own length tercile (short/mid/long): {' · '.join(cells)}")

    print("\n## LLM calls (test generation)")
    for name, fpf, *_ in CONFIGS[3:]:
        recs = [json.loads(l) for l in open(RQ1.format(fpf))]
        print(f"- {name}: test-generation records {len(recs)}, with a ```java block {sum('```java' in (r.get('completion') or '') for r in recs)}")

    # dump for the manual check: M tests of every M-method of the blind arms (and m3), next to the spec rules
    with open(f"{D}/out/m_methods.txt", "w") as f:
        for name, fpf, *_ in CONFIGS[2:]:
            comp = [json.loads(l) for l in open(RQ1.format(fpf))]
            for i in keep:
                m = data[name][i]
                if not m["counts"]["M"]:
                    continue
                f.write(f"\n{'=' * 100}\n{name} | {i} {tag(i)} | M {m['counts']['M']} E {m['counts']['E']} | bug concepts "
                        f"{labels[str(i)]['concepts']}: {labels[str(i)]['note']}\n")
                for t, c in m["cats"].items():
                    if c == "M":
                        f.write(f"--- M test {t}:\n{test_src(comp[i].get('completion'), t)}\n")
                f.write("--- spec rules:\n" + "\n".join(f"  {k} {r['input']} -> {r['expected']}" for k in facets
                                                        if isinstance(specs[name][i][k], list) for r in specs[name][i][k]) + "\n")
    print(f"\nwrote {D}/out/m_methods.txt")


if __name__ == "__main__":
    main()
