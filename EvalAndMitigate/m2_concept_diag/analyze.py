"""Validation + outcome analysis for m2 (host python, stdlib only).  usage: python3 m2_concept_diag/analyze.py
Inputs: labels.jsonl (labels.py), manual_labels.json (my reading of all 78 in-method diffs), judge.jsonl (judge.py),
manual_judge.json (my verdicts on a sample), and the per-method outcomes parsed from the evaluation logs
(m1_test_review/analyze.py `load`, glitched methods excluded per config)."""
import importlib.util, json, os
from collections import Counter
from math import comb

_spec = importlib.util.spec_from_file_location("m1_analyze", "m1_test_review/analyze.py")
_m1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m1)
load = _m1.load  # per-method blocks of a config (merges m1's resumed part logs)

D = "m2_concept_diag"
DOCS = {"basic": "data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_docstring.jsonl",
        "advanced": "data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl"}
CS = [f"C{i}" for i in range(9)]
CONFIGS = [("Doc W/ Code", "unified_invoked_docstring_code_prompt", "basic"),
           ("Only Doc", "unified_invoked_docstring_prompt", "basic"),
           ("Advanced Doc", "unified_invoked_advanced_docstring_prompt", "advanced"),
           ("m1 review Only Doc", "m1_review_onlydoc", "basic"),
           ("m1 review Adv Doc", "m1_review_advdoc", "advanced")]


def fisher(a, b, c, d):
    """two-sided Fisher exact p for [[a, b], [c, d]]."""
    r1, c1, n = a + b, a + c, a + b + c + d
    pr = lambda x: comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)
    p0 = pr(a)
    return min(1.0, sum(pr(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if pr(x) <= p0 * (1 + 1e-9)))


def kappa(x, y):
    n = len(x); po = sum(a == b for a, b in zip(x, y)) / n
    pa, pb = sum(x) / n, sum(y) / n; pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def has18(cs):
    return any(c != "C0" for c in cs)


def validate_labels(labels, manual):
    print("## 1. Rule labels vs my reading of all 78 in-method diffs\n")
    rule = [set(l["concepts"]) for l in labels]; gold = [set(manual[str(l["idx"])]["concepts"]) for l in labels]
    print("| concept | rule+ | manual+ | TP | FP | FN | precision | recall | agreement | kappa |\n|---|---|---|---|---|---|---|---|---|---|")
    for c in CS:
        r = [c in s for s in rule]; g = [c in s for s in gold]
        tp = sum(a and b for a, b in zip(r, g)); fp = sum(a and not b for a, b in zip(r, g)); fn = sum(b and not a for a, b in zip(r, g))
        print(f"| {c} | {sum(r)} | {sum(g)} | {tp} | {fp} | {fn} | {tp / max(1, tp + fp):.2f} | {tp / max(1, tp + fn):.2f} | "
              f"{sum(a == b for a, b in zip(r, g)) / len(r):.2f} | {kappa(r, g):.2f} |")
    alltp = sum(len(r & g - {"C0"}) for r, g in zip(rule, gold)); allr = sum(len(r - {"C0"}) for r in rule); allg = sum(len(g - {"C0"}) for g in gold)
    print(f"\nmicro (C1-C8 label instances): precision {alltp}/{allr} = {alltp / allr:.2f}, recall {alltp}/{allg} = {alltp / allg:.2f}")
    exact = sum(r == g for r, g in zip(rule, gold)); some = sum(bool(r & g - {"C0"}) for r, g in zip(rule, gold) if has18(r))
    print(f"exact label-set match {exact}/78; methods where rule gives >=1 C1-C8 label and at least one is right: {some}/{sum(map(has18, rule))}")
    bugs = sorted({l["bug"] for l in labels})
    for name, sets in (("rule", rule), ("manual", gold)):
        m = sum(map(has18, sets)); b = sum(any(has18(s) for l, s in zip(labels, sets) if l["bug"] == bug) for bug in bugs)
        print(f"coverage ({name}): methods with >=1 of C1-C8 {m}/78 ({100 * m / 78:.0f}%), only C0 {78 - m}; bugs {b}/{len(bugs)} ({100 * b / len(bugs):.0f}%)")
    fps = Counter()
    for l, g in zip(labels, gold):
        for c in set(l["concepts"]) - g - {"C0"}:
            for ev in l["evidence"][c]:
                fps[(c, ev["pattern"])] += 1
    print("\nFalse-positive sources (concept, pattern): " + "; ".join(f"{c} `{p}` x{n}" for (c, p), n in fps.most_common()))
    print("scope: " + str(Counter(l["scope"] for l in labels)) + "\n")


def validate_judge(judge, mj):
    print("## 2. LLM judge vs my verdicts\n")
    key = {(j["idx"], j["docset"]): j for j in judge}
    pairs = [(v["verdict"], key[(int(k.split(":")[0]), k.split(":")[1])]["verdict"]) for k, v in mj.items()]
    conf = Counter(pairs)
    print(f"cases {len(pairs)}; agreement {sum(a == b for a, b in pairs)}/{len(pairs)} = {sum(a == b for a, b in pairs) / len(pairs):.2f}")
    print("confusion (mine -> judge): " + ", ".join(f"{a}->{b} {n}" for (a, b), n in sorted(conf.items())))
    for v in ("BUGGY", "FIXED"):
        print(f"binary agreement {v} vs not: {sum((a == v) == (b == v) for a, b in pairs)}/{len(pairs)}")
    norm = lambda t: " ".join(t.replace("*", " ").split())
    docs = {ds: [json.loads(l) for l in open(p)] for ds, p in DOCS.items()}
    q = [j for j in judge if j["verdict"] in ("BUGGY", "FIXED")]
    ok = sum(bool(j["quote"]) and norm(j["quote"]) in norm(docs[j["docset"]][j["idx"]]["generated_docstring"]) for j in q)
    print(f"BUGGY/FIXED verdicts whose quote occurs verbatim (whitespace/'*' normalised) in the docstring: {ok}/{len(q)}")
    print(f"judge calls {sum(j['calls'] for j in judge)} for {len(judge)} judgements; unparsed {sum(j['verdict'] is None for j in judge)}\n")
    print("| docset | BUGGY | FIXED | NEITHER |\n|---|---|---|---|")
    for ds in ("basic", "advanced"):
        c = Counter(j["verdict"] for j in judge if j["docset"] == ds); n = sum(c.values())
        print(f"| {ds} | {c['BUGGY']} ({100 * c['BUGGY'] / n:.1f}%) | {c['FIXED']} ({100 * c['FIXED'] / n:.1f}%) | {c['NEITHER']} ({100 * c['NEITHER'] / n:.1f}%) |")
    b = {j["idx"]: j["verdict"] for j in judge if j["docset"] == "basic"}; a = {j["idx"]: j["verdict"] for j in judge if j["docset"] == "advanced"}
    print("basic -> advanced transitions: " + ", ".join(f"{x}->{y} {n}" for (x, y), n in sorted(Counter((b[i], a[i]) for i in b).items())) + "\n")


def outcomes(labels, gold, judge):
    verdict = {(j["idx"], j["docset"]): j["verdict"] for j in judge}
    print("## 3. Outcomes per bug concept (manual labels; multi-label, so rows overlap). Glitched methods excluded per config.\n")
    per = {}
    for name, fpf, ds in CONFIGS:
        meths = load(fpf)[0]
        per[name] = [None if m["glitch"] else m["counts"] for m in meths]
    for lab_name, sets in (("manual", gold), ("rule", [set(l["concepts"]) for l in labels])):
        print(f"### by {lab_name} labels: methods with >=1 E / >=1 M (M, E, FP tests; red-prec)\n")
        print("| concept | n | " + " | ".join(n for n, _, _ in CONFIGS) + " |\n|---|---|" + "---|" * len(CONFIGS))
        for c in CS:
            idx = [i for i, s in enumerate(sets) if c in s]
            cells = []
            for name, _, _ in CONFIGS:
                ms = [per[name][i] for i in idx if per[name][i]]
                t = {k: sum(m[k] for m in ms) for k in ("M", "E", "FP")}
                cells.append(f"E{sum(m['E'] > 0 for m in ms)} M{sum(m['M'] > 0 for m in ms)} ({t['M']}/{t['E']}/{t['FP']}; "
                             f"{t['E'] / max(1, t['E'] + t['FP']):.2f})")
            print(f"| {c} | {len(idx)} | " + " | ".join(cells) + " |")
        print()
    print("## 4. Docstring verdict vs outcome, per config (methods; glitched excluded)\n")
    print("| config | verdict | n | >=1 E | >=1 M |\n|---|---|---|---|---|")
    tests = []
    for name, fpf, ds in CONFIGS:
        rows = [(verdict[(i, ds)], per[name][i]) for i in range(78) if per[name][i]]
        for v in ("FIXED", "BUGGY", "NEITHER"):
            sub = [m for vv, m in rows if vv == v]
            print(f"| {name} | {v} | {len(sub)} | {sum(m['E'] > 0 for m in sub)} | {sum(m['M'] > 0 for m in sub)} |")
        for v, k in (("FIXED", "E"), ("BUGGY", "M"), ("BUGGY", "E"), ("FIXED", "M")):
            a = sum(vv == v and m[k] > 0 for vv, m in rows); b = sum(vv == v and m[k] == 0 for vv, m in rows)
            c = sum(vv != v and m[k] > 0 for vv, m in rows); d = sum(vv != v and m[k] == 0 for vv, m in rows)
            tests.append(f"| {name} | {v} vs not | >=1 {k} | {a}/{a + b} | {c}/{c + d} | {fisher(a, b, c, d):.3f} |")
    print("\nFisher exact (two-sided): share of methods with the outcome among verdict=v vs the rest\n")
    print("| config | split | outcome | verdict=v | rest | p |\n|---|---|---|---|---|---|")
    print("\n".join(tests) + "\n")
    print("## 5. Misguided (>=1 M) and effective (>=1 E) methods: concept (manual) and docstring verdict\n")
    for name, fpf, ds in CONFIGS:
        for k in ("M", "E"):
            hit = [i for i in range(78) if per[name][i] and per[name][i][k] > 0]
            print(f"- {name} >=1 {k} ({len(hit)}): " + ", ".join(
                f"{labels[i]['project'].replace('_buggy', '')}#{labels[i]['sig'].split('#')[2].split('(')[0]}[{'+'.join(sorted(gold[i]))};{verdict[(i, ds)][0]}]" for i in hit))
            print(f"  concepts: {dict(sorted(Counter(c for i in hit for c in gold[i]).items()))}; verdicts: {dict(Counter(verdict[(i, ds)] for i in hit))}")
    print()
    print("## 6. Config differences on the common clean methods (E-methods / M-methods per concept)\n")
    common = [i for i in range(78) if all(per[n][i] for n, _, _ in CONFIGS[:3])]
    print(f"common clean methods of the three baselines: {len(common)}\n")
    print("| concept | n | Doc W/ Code E/M | Only Doc E/M | Advanced E/M |\n|---|---|---|---|---|")
    for c in CS:
        idx = [i for i in common if c in gold[i]]
        print(f"| {c} | {len(idx)} | " + " | ".join(f"{sum(per[n][i]['E'] > 0 for i in idx)}/{sum(per[n][i]['M'] > 0 for i in idx)}" for n, _, _ in CONFIGS[:3]) + " |")
    for v in ("FIXED", "BUGGY", "NEITHER"):
        for ds, names in (("basic", ("Doc W/ Code", "Only Doc")), ("advanced", ("Advanced Doc",))):
            idx = [i for i in common if verdict[(i, ds)] == v]
            print(f"- {ds} docstring {v}: n={len(idx)}; " + "; ".join(f"{n}: >=1E {sum(per[n][i]['E'] > 0 for i in idx)}, >=1M {sum(per[n][i]['M'] > 0 for i in idx)}" for n in names))

    print("\npaired, same methods: >=1 E under Only Doc (basic docstring) vs Advanced Doc (advanced docstring), grouped by the "
          "(basic -> advanced) verdict transition")
    for (vb, va), n in sorted(Counter((verdict[(i, "basic")], verdict[(i, "advanced")]) for i in common).items()):
        idx = [i for i in common if (verdict[(i, "basic")], verdict[(i, "advanced")]) == (vb, va)]
        o = [per["Only Doc"][i]["E"] > 0 for i in idx]; a = [per["Advanced Doc"][i]["E"] > 0 for i in idx]
        print(f"- {vb}->{va} n={n}: Only Doc {sum(o)}, Advanced {sum(a)} (Adv only {sum(y and not x for x, y in zip(o, a))}, "
              f"Only Doc only {sum(x and not y for x, y in zip(o, a))})")


def main():
    labels = [json.loads(l) for l in open(f"{D}/labels.jsonl")]
    manual = json.load(open(f"{D}/manual_labels.json"))
    judge = [json.loads(l) for l in open(f"{D}/judge.jsonl")]
    validate_labels(labels, manual)
    if os.path.exists(f"{D}/manual_judge.json"):
        validate_judge(judge, json.load(open(f"{D}/manual_judge.json")))
    outcomes(labels, [set(manual[str(l["idx"])]["concepts"]) for l in labels], judge)


if __name__ == "__main__":
    assert abs(fisher(3, 1, 1, 3) - 0.486) < 1e-3 and fisher(5, 0, 0, 5) < 0.008
    main()