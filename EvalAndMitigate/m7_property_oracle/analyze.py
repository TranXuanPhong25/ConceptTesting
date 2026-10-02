"""Numbers for RESULTS.md (host python, stdlib).  usage: python3 m7_property_oracle/analyze.py > m7_property_oracle/out/analysis.txt
Outcome parsing (latest_log/parse/row/load/p_mcnemar/test_src) is reused from m6_agent_oracle/analyze.py (m5 -> m1 lineage).
Also writes out/me_tests.txt (every M and E test of both m7 arms with its assertion-form label and source)."""
import importlib.util, json, re, sys
from collections import Counter

sys.path.insert(0, "m7_property_oracle")
import form as F

_spec = importlib.util.spec_from_file_location("m6_analyze", "m6_agent_oracle/analyze.py")
A6 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(A6)
O = A6.O  # m6 oracle module (records, evidence, render_pack)

D = "m7_property_oracle"
CONFIGS = [("Only Doc", "unified_invoked_docstring_prompt", None),
           ("Advanced Doc", "unified_invoked_advanced_docstring_prompt", None),
           ("m6 blind oracle", "m6_oracle_blind", "m6_agent_oracle"),
           ("m6 sees-code oracle", "m6_oracle_sees_code", "m6_agent_oracle"),
           ("m7 prop", "m7_prop", D),
           ("m7 example", "m7_example", D)]
PROP, EX, ADV, BLIND = "m7 prop", "m7 example", "Advanced Doc", "m6 blind oracle"
PAIRS = [(EX, PROP), (ADV, PROP), (ADV, EX), (BLIND, PROP), (BLIND, EX)]  # (a, b): "b vs a"
FPF = {n: f for n, f, _ in CONFIGS}


def mcnemar_lines(data, idx, pairs):
    has = lambda name, k: [data[name][i]["counts"][k] > 0 for i in idx]
    for a, b in pairs:
        out = []
        for k in ("M", "E"):
            oa, ob, p = A6.p_mcnemar(has(a, k), has(b, k))
            out.append(f"≥1 {k} {sum(has(b, k))} vs {sum(has(a, k))}: only {b} {ob}, only {a} {oa}, p={p:.3g}")
        print(f"- {b} vs {a}: " + "; ".join(out))


def table(data, idx, label):
    print(f"\n## {label}: {len(idx)} methods\n\n{A6.HEAD}")
    for name, ms in data.items():
        print(A6.row(name, [ms[i] for i in idx]))
    print()
    mcnemar_lines(data, idx, PAIRS)


def other_focal(records, evs):
    """m6 blind packs that contain another focal method of the same bug (m6 analyze.py `mechanism`, same rule)."""
    norm = A6.norm
    by_bug = {}
    for i, r in enumerate(records):
        by_bug.setdefault(r["extra:project_name"], []).append(i)
    return [i for i, r in enumerate(records) if any(
        norm(records[j]["source:source_method_code_format"])[:200] in norm(O.render_pack(r, evs[i], False))
        for j in by_bug[r["extra:project_name"]] if j != i)]


def forms(fpf, records):
    """per method index: {test name: classification} (form.py)."""
    comp = [json.loads(l) for l in open(A6.RQ1.format(fpf))]
    assert [c["method_signature"] for c in comp] == [r["source:source_method_signature"] for r in records]
    return [F.classify(c.get("completion"), r["source:source_method_name"]) for c, r in zip(comp, records)]


def strict(ms, fm, idx):
    """post hoc: drop tests with any unmarked LITERAL; per-test outcomes from the log's failing-test lists.
    Compiled tests among the dropped ones are estimated (failing ones certainly compiled; passing ones at the method's
    TN / (non-failing tests) rate). Returns per-method booleans (≥1 M, ≥1 E) of the kept tests."""
    tot, kept_all, has_m, has_e = Counter(), 0, [], []
    for i in idx:
        cats, f = ms[i]["cats"], fm[i]
        drop = {t for t, x in f.items() if F.label(x) == "LITERAL"}
        c = Counter(v for t, v in cats.items() if t not in drop)
        comp = sum(ms[i]["counts"][k] for k in ("M", "E", "TN", "FP"))
        nonfail = max(1, len(f) - len(cats))
        tot["compiled"] += comp - len(drop & set(cats)) - len(drop - set(cats)) * ms[i]["counts"]["TN"] / nonfail
        for k in ("M", "E", "FP"):
            tot[k] += c[k]
        kept_all += len(f) - len(drop)
        has_m.append(c["M"] > 0); has_e.append(c["E"] > 0)
    cc = max(1, tot["compiled"])
    print(f"| m7 prop strict (post hoc) | {kept_all} kept / ~{tot['compiled']:.0f} | {tot['M']} (~{100 * tot['M'] / cc:.2f}%) | "
          f"{tot['E']} (~{100 * tot['E'] / cc:.2f}%) | {tot['FP']} (~{100 * tot['FP'] / cc:.2f}%) | "
          f"{tot['E'] / max(1, tot['E'] + tot['FP']):.3f} | {sum(has_m)} | {sum(has_e)} |")
    return has_m, has_e


def main():
    records = O.load_records()
    evs = O.load_evidence()
    ids = [r["extra:project_name"] for r in records]
    tag = lambda i: f"{ids[i].replace('_buggy', '')}.{records[i]['source:source_method_name']}"
    data = {name: A6.load(fpf, folder) for name, fpf, folder in CONFIGS}
    sigs = [m["sig"] for m in data[ADV]]
    for name, ms in data.items():
        assert [m["sig"] for m in ms] == sigs == [r["source:source_method_signature"] for r in records], name
    glitched = {name: [i for i, m in enumerate(ms) if m["glitch"]] for name, ms in data.items()}
    keep = [i for i in range(len(sigs)) if not any(i in g for g in glitched.values())]
    print("glitched (excluded):", {n: [ids[i] for i in g] for n, g in glitched.items()})
    table(data, keep, "Intersection of clean methods")
    no_g = [i for i in keep if ids[i] not in ("Gson_4_buggy", "Cli_1_buggy")]
    table(data, no_g, "Sensitivity: without Gson_4 and Cli_1")
    of = other_focal(records, evs)
    print(f"\nm6 blind packs containing another focal method of the same bug ({len(of)}): {[tag(i) for i in of]}")
    table(data, [i for i in keep if i not in of], "Sensitivity: without those methods")
    print("\n## Each config on its own clean methods\n\n" + A6.HEAD)
    for name, ms in data.items():
        print(A6.row(f"{name} ({sum(not m['glitch'] for m in ms)} methods)", [m for m in ms if not m["glitch"]]))

    print("\n## Per-method changes (intersection)")
    for a, b in PAIRS[:1] + PAIRS[3:5]:
        for k in ("M", "E"):
            g = [tag(i) for i in keep if data[b][i]["counts"][k] and not data[a][i]["counts"][k]]
            l = [tag(i) for i in keep if data[a][i]["counts"][k] and not data[b][i]["counts"][k]]
            print(f"- ≥1 {k}, {b} vs {a}: only {b} {g}; only {a} {l}")
    print("\nM-methods per config (method: M tests):")
    for name, ms in data.items():
        print(f"- {name}: " + ", ".join(f"{tag(i)}:{ms[i]['counts']['M']}" for i in keep if ms[i]["counts"]["M"]))

    # ---- assertion form
    fm = {name: forms(FPF[name], records) for name in (ADV, BLIND, PROP, EX)}
    print("\n## Assertion form (form.py), all 78 methods")
    for name, f in fm.items():
        s = F.summary([x for d in f for x in d.values()])
        pct = lambda k: f"{s[k]} ({100 * s[k] / max(1, s['tests']):.1f}%)"
        labels = Counter(F.label(x) for d in f for x in d.values())
        print(f"- {name}: @Test methods {s['tests']}; tests with ≥1 LITERAL {pct('lit')}, ≥1 unmarked LITERAL {pct('unmarked')}, "
              f"≥1 marked LITERAL {pct('marked')}, THROWS only {pct('throws_only')}, no assertion {pct('no_assert')}; "
              f"assertions {s['kinds']}; per-test labels {dict(labels)}")
        per_m = [sum(F.label(x) == "LITERAL" for x in d.values()) / max(1, len(d)) for d in f]
        print(f"    methods where >30% of tests have an unmarked LITERAL: {sum(p > 0.3 for p in per_m)} / {len(per_m)}")
    marked = [(i, t) for i, d in enumerate(fm[PROP]) for x in d.values() for t in x["marked_text"]]
    lits = lambda t: [s for s in re.findall(r'"((?:[^"\\]|\\.)*)"', t) if s] + re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?", t)
    inj = lambda i, t: all(re.sub(r"\\(.)", r"\1", x) in evs[i]["javadoc"] for x in lits(t)) and bool(lits(t))
    print(f"- m7 prop: LITERAL assertions marked `// from Javadoc` {len(marked)}; whose string/number literals all occur in the "
          f"method's original Javadoc {sum(inj(i, t) for i, t in marked)} (rough check)")

    print("\n## Mechanism: assertion form of the M and E tests (intersection)")
    with open(f"{D}/out/me_tests.txt", "w", errors="backslashreplace") as out:
        for name in (ADV, BLIND, PROP, EX):
            ms, f = data[name], fm[name]
            rows = Counter(); base = Counter()
            for i in keep:
                for t, x in f[i].items():
                    base[F.label(x)] += 1
                for t, c in ms[i]["cats"].items():
                    lab = F.label(f[i][t]) if t in f[i] else "not found"
                    rows[(c, lab)] += 1
                    if c in ("M", "E") and name in (PROP, EX):
                        out.write(f"\n{'=' * 100}\n{name} | {c} | {tag(i)} | {lab} | {t}\n{f[i][t]['src'] if t in f[i] else ''}\n")
            labs = ["LITERAL", "LITERAL-marked", "RELATION", "THROWS", "NONE", "not found"]
            print(f"- {name}: all tests by label {dict(base)}")
            for c in ("M", "E", "FP"):
                n = sum(rows[(c, l)] for l in labs)
                print(f"    {c} tests {n}: " + ", ".join(f"{l} {rows[(c, l)]}" for l in labs if rows[(c, l)])
                      + "; rate per label (outcome / tests with label): " + ", ".join(f"{l} {rows[(c, l)]}/{base[l]}" for l in labs[:5] if base[l]))

    print("\n## Post hoc strict m7 prop (tests with any unmarked LITERAL dropped; no new calls), intersection\n\n" + A6.HEAD)
    print(A6.row(PROP, [data[PROP][i] for i in keep]))
    sm, se = strict(data[PROP], fm[PROP], keep)
    print(A6.row(EX, [data[EX][i] for i in keep]))
    for k, v in (("M", sm), ("E", se)):
        for name in (EX, ADV):
            other = [data[name][i]["counts"][k] > 0 for i in keep]
            oa, ob, p = A6.p_mcnemar(other, v)
            print(f"- strict ≥1 {k} {sum(v)} vs {name} {sum(other)}: only strict {ob}, only {name} {oa}, p={p:.3g}")

    print("\n## LLM calls (test generation)")
    for arm in ("prop", "example"):
        rs = [json.loads(l) for l in open(f"{D}/out/gen_{arm}.jsonl")]
        v1 = sum(json.loads(l)["calls"] for l in open(f"{D}/out/v1_smoke/gen_{arm}.jsonl"))
        print(f"- m7 {arm}: records {len(rs)}, calls {sum(r['calls'] for r in rs)} (re-asks: {[(r['id'], r['calls']) for r in rs if r['calls'] > 1]}), "
              f"unparsable after re-asks {sum(not r['completion'] for r in rs)}; plus v1 smoke (prompt before the revision, discarded) {v1}")


if __name__ == "__main__":
    main()
