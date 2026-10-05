"""Numbers for RESULTS.md (host python, stdlib).  usage: python3 m9_concept_advanced/analyze.py > m9_concept_advanced/out/analysis.txt
Outcome parsing (latest_log/parse/row/load/p_mcnemar/HEAD) is reused from m6_agent_oracle/analyze.py (m5 -> m1 lineage),
fisher from m2_concept_diag/analyze.py, body_leaks from m5_blind_concept_spec/spec.py. Arms without data are skipped.
Pre-registered contrasts (exact McNemar on methods with >=1 E and >=1 M, intersection of clean methods):
  primary   m9 concept vs m9 placebo
  secondary m9 concept vs m9 adv_rerun, m9 concept vs Advanced Doc (original run)
  A/A noise m9 adv_rerun vs Advanced Doc (discordant methods)
  sensitivity: the same without Gson_4 and Cli_1, and without methods whose docstring carries the focal body (any arm)
Mechanism: Part 2 fix rate (fixrate.py), Part 1 vs m2 manual concept labels, fixed Part 2 vs >=1 E."""
import glob, importlib.util, json, os, re, sys
from collections import Counter


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


A6 = _load("m6_analyze", "m6_agent_oracle/analyze.py")
fisher = _load("m2_analyze", "m2_concept_diag/analyze.py").fisher
M5 = _load("m5_spec", "m5_blind_concept_spec/spec.py")
sys.path.insert(0, "m9_concept_advanced")
import m9

D = "m9_concept_advanced"
ADV, RERUN, CONCEPT, PLACEBO = "Advanced Doc", "m9 adv_rerun", "m9 concept", "m9 placebo"
CONFIGS = [(ADV, "unified_invoked_advanced_docstring_prompt", None), (RERUN, "m9_adv_rerun", D),
           (CONCEPT, "m9_concept", D), (PLACEBO, "m9_placebo", D)]
ARM = {RERUN: "adv_rerun", CONCEPT: "concept", PLACEBO: "placebo"}
PAIRS = [(PLACEBO, CONCEPT), (RERUN, CONCEPT), (ADV, CONCEPT), (ADV, RERUN), (RERUN, PLACEBO)]  # (a, b): "b vs a"
SUBSETS = {"all": (), "without Gson_4 and Cli_1": ("Gson_4_buggy", "Cli_1_buggy")}
labels = json.load(open("m2_concept_diag/manual_labels.json"))
records = [json.loads(l) for l in open(m9.SRC)]
ids = [r["extra:project_name"] for r in records]
tag = lambda i: f"{i}:{ids[i].replace('_buggy', '')}"


def docs(arm):
    p = f"{D}/out/docs_{arm}.jsonl"
    return {r["idx"]: r for r in map(json.loads, open(p))} if os.path.exists(p) else {}


def outcomes():
    data = {n: A6.load(f, d) for n, f, d in CONFIGS if glob.glob(A6.LOGS.format(f))}
    keep = [i for i in range(len(records)) if all(not ms[i]["glitch"] for ms in data.values())]
    for name, ms in data.items():
        assert [m["sig"] for m in ms] == [r["source:source_method_signature"] for r in records], name
    pairs = [p for p in PAIRS if p[0] in data and p[1] in data]
    # methods whose docstring carries >=40-char windows of the buggy focal body into the test prompt, in any m9 arm
    # (mostly the whole-text fallbacks of repetition loops; the same 3 in the original Advanced run): dropped for all arms
    body = sorted({i for a in m9.ARMS for i, d in docs(a).items() if M5.body_leaks(records[i], d["generated_docstring"])})
    subsets = {label: {i for i in range(len(records)) if ids[i] in drop} for label, drop in SUBSETS.items()}
    subsets[f"without the {len(body)} body-in-test-prompt methods ({', '.join(tag(i) for i in body)})"] = set(body)
    subsets["without body-in-test-prompt methods, Gson_4 and Cli_1"] = set(body) | subsets["without Gson_4 and Cli_1"]
    for label, drop in subsets.items():
        idx = [i for i in keep if i not in drop]
        print(f"\n## Intersection of clean methods, {label}: {len(idx)} methods\n\n{A6.HEAD}")
        for name, ms in data.items():
            print(A6.row(name, [ms[i] for i in idx]))
        has = lambda name, k: [data[name][i]["counts"][k] > 0 for i in idx]
        print()
        for a, b in pairs:
            out = []
            for k in ("E", "M"):
                oa, ob, p = A6.p_mcnemar(has(a, k), has(b, k))
                out.append(f"≥1 {k} {sum(has(b, k))} vs {sum(has(a, k))}: only {b} {ob}, only {a} {oa}, p={p:.3g}")
            print(f"- {b} vs {a}: " + "; ".join(out))
    print("\n## Each config on its own clean methods\n\n" + A6.HEAD)
    for name, ms in data.items():
        print(A6.row(f"{name} ({sum(not m['glitch'] for m in ms)} methods)", [m for m in ms if not m["glitch"]]))
    print("\n## Discordant methods (intersection, all)")
    for a, b in pairs:
        for k in ("E", "M"):
            g = [tag(i) for i in keep if data[b][i]["counts"][k] and not data[a][i]["counts"][k]]
            l = [tag(i) for i in keep if data[a][i]["counts"][k] and not data[b][i]["counts"][k]]
            print(f"- ≥1 {k}, {b} vs {a}: only {b} {g}; only {a} {l}")
    print("\nM-methods per config (method: M tests):")
    for name, ms in data.items():
        print(f"- {name}: " + ", ".join(f"{tag(i)}:{ms[i]['counts']['M']}" for i in keep if ms[i]["counts"]["M"]))
    return data, keep


def calls_and_cost():
    print("\n## LLM calls and cost")
    cs = m9.calls()
    for arm in m9.ARMS:
        a = [c for c in cs if c["arm"] == arm]
        if a:
            billed = [c for c in a if c.get("in_tok")]
            print(f"- docstring {arm}: methods {len({c['idx'] for c in a})}, API attempts {len(a)} (billed {len(billed)}, "
                  f"errors {len(a) - len(billed)}), in {sum(c['in_tok'] for c in billed)} / out {sum(c['out_tok'] for c in billed)} "
                  f"tokens, ${sum(c['usd'] for c in a):.3f}")
            loops = [c for c in billed if c["out_tok"] >= 65536]  # hit the output limit: repetition loops
            print(f"  repetition loops (65,536 output tokens, docstring = the notebook's whole-text fallback): {len(loops)}, "
                  f"${sum(c['usd'] for c in loops):.3f}: " + ", ".join(f"{tag(c['idx'])} ${c['usd']:.3f}" for c in loops))
    for f in sorted(f for f in glob.glob(m9.RQ1.format("m9_*")) if "_err_msg_" not in f and not re.search(r"_(part|redo)\d+_with", f)):
        print(f"- test generation {os.path.basename(f)}: {sum(1 for _ in open(f))} completions (one call each, shim retries not logged)")
    m9.cost()


def part1(text):
    """Part 1 (before the Part 2 heading) and its item 3 (from the Checklist Review heading)."""
    m = re.search(r"\n[#*\s]*Part 2\b", text)
    p1 = text[:m.start()] if m else text
    k = p1.find("Checklist Review")
    return p1, (p1[k:] if k >= 0 else "")


def checklist_flags(item3):
    """{Ck: flagged?} from the concept arm's item 3: flagged unless the finding says no issue."""
    out = {}
    parts = re.split(r"(?:^|\n)[\s*\-#]*\**(C[1-8])\b", item3)
    for c, txt in zip(parts[1::2], parts[2::2]):
        no = re.search(r"\bno (significant |major |real |obvious |direct |specific )?(issues?|problems?|concerns?)\b|not applicable|\bn/a\b", txt, re.I)
        out[c] = not no or bool(re.search(r"\*\*Issue|\bIssue\b ?[.:]", txt))  # approximate: free-text findings
    return out


KW = {"C1": r"\bnull\b|NullPointer", "C2": r"\bempty\b|\bblank\b|whitespace", "C3": r"off-by-one|boundar|out of bounds|IndexOutOfBounds|last index|edge case",
      "C4": r"exception|\bthrows?\b", "C5": r"escap|normali[sz]|\bformat|quot", "C6": r"overflow|precision|rounding|negative|\bNaN\b|infinit",
      "C7": r"unicode|locale|surrogate|non-ASCII|upper ?case|lower ?case|code ?point", "C8": r"\bstate\b|mutat|side.effect|idempoten|\bshared\b|\breset"}


def mechanism(data, keep):
    fx = {a: json.load(open(f"{D}/out/fixrate_{a}.json")) for a in m9.ARMS if os.path.exists(f"{D}/out/fixrate_{a}.json")}
    if fx:
        print("\n## Part 2 fix rate (substitute the corrected implementation, run the bug's trigger tests; all 78 methods / 60 bugs)\n")
        print("| arm | Part 2 found | compiled | fixed (method) | any trigger passes | bugs fixed (all its methods substituted) |\n|---|---|---|---|---|---|")
        for a, r in fx.items():
            ms, bs = r["methods"].values(), r["bugs"].values()
            print(f"| {a} | {sum(m['part2'] for m in ms)} | {sum(m['compiled'] for m in ms)} | {sum(m['fixed'] for m in ms)} | "
                  f"{sum(m['any_pass'] for m in ms)} | {sum(b['fixed'] for b in bs)} / {len(r['bugs'])} |")
        chk = json.load(open(f"{D}/out/fixrate_check.json"))
        rep = {b for b, x in chk.items() if (x["fixed_version"] or {}).get("fixed")}
        rep_m = [str(i) for b in rep for i in chk[b]["idx"]]
        print(f"\nHarness check: substituting the FIXED focal methods fixes {len(rep)}/60 bugs ({len(rep_m)} methods); the other "
              f"{60 - len(rep)} need changes outside the focal methods. Buggy methods substituted: "
              f"{sum(bool((x['buggy_version'] or {}).get('fixed')) for x in chk.values())} fixes.")
        for a, r in fx.items():
            print(f"- {a}, restricted to the {len(rep)} reproducible bugs: methods fixed {sum(r['methods'][k]['fixed'] for k in rep_m)}/{len(rep_m)}, "
                  f"bugs fixed {sum(r['bugs'][b]['fixed'] for b in rep)}/{len(rep)}")
        print("- fixed methods per arm: " + "; ".join(f"{a}: " + ", ".join(tag(int(k)) for k in sorted(r["methods"], key=int) if r["methods"][k]["fixed"]) for a, r in fx.items()))
        for a, b in (("placebo", "concept"), ("adv_rerun", "concept"), ("adv_rerun", "placebo")):
            if a in fx and b in fx:
                for unit, n in (("methods", 78), ("bugs", None)):
                    ks = sorted(fx[a][unit])
                    oa, ob, p = A6.p_mcnemar([fx[a][unit][k]["fixed"] for k in ks], [fx[b][unit][k]["fixed"] for k in ks])
                    print(f"- fixed {unit}, {b} vs {a}: only {b} {ob}, only {a} {oa}, p={p:.3g}")
        print("\nFixed Part 2 vs ≥1 E (intersection of clean methods): ≥1 E among fixed / among not fixed, Fisher p")
        for a, r in fx.items():
            name = next(n for n, x in ARM.items() if x == a)
            if name in data:
                f_ = [i for i in keep if r["methods"][str(i)]["fixed"]]; nf = [i for i in keep if not r["methods"][str(i)]["fixed"]]
                e1 = lambda idx: sum(data[name][i]["counts"]["E"] > 0 for i in idx)
                m1 = lambda idx: sum(data[name][i]["counts"]["M"] > 0 for i in idx)
                print(f"- {a}: ≥1 E {e1(f_)}/{len(f_)} vs {e1(nf)}/{len(nf)} (p={fisher(e1(f_), len(f_) - e1(f_), e1(nf), len(nf) - e1(nf)):.3g}); "
                      f"≥1 M {m1(f_)}/{len(f_)} vs {m1(nf)}/{len(nf)}")
    print("\n## Part 1 vs the bug concept (m2 manual labels; methods whose label has a C1-C8 concept)")
    lab = {i: [c for c in labels[str(i)]["concepts"] if c != "C0"] for i in range(len(records))}
    idx = [i for i in lab if lab[i]]
    for a in m9.ARMS:
        ds = docs(a)
        if len(ds) < len(records):
            continue
        p1 = {i: part1(ds[i]["completion"]) for i in ds}
        kw = lambda t, cs: any(re.search(KW[c], t, re.I) for c in cs)
        items12 = {i: p1[i][0].replace(p1[i][1], "") for i in ds}
        line = (f"- {a} ({len(idx)} methods): keyword proxy, items 1-2 mention the bug's concept {sum(kw(items12[i], lab[i]) for i in idx)}; "
                f"mean concepts mentioned per method {sum(sum(bool(re.search(KW[c], items12[i], re.I)) for c in KW) for i in idx) / len(idx):.1f}/8")
        if a == "concept":
            fl = {i: checklist_flags(p1[i][1]) for i in ds}
            parsed = sum(len(fl[i]) == 8 for i in ds)
            line += (f"; checklist parsed {parsed}/78, bug concept flagged {sum(any(fl[i].get(c) for c in lab[i]) for i in idx)}/{len(idx)}, "
                     f"mean flagged per method {sum(sum(fl[i].values()) for i in ds) / len(ds):.1f}/8")
            pairs = [(c in lab[i], fl[i][c]) for i in idx if len(fl[i]) == 8 for c in fl[i]]
            fa, na, fb, nb = (sum(f for l, f in pairs if l), sum(l for l, f in pairs), sum(f for l, f in pairs if not l), sum(not l for l, f in pairs))
            line += (f"; flag rate labelled concept {fa}/{na} ({fa / max(1, na):.2f}) vs other concepts of the same methods "
                     f"{fb}/{nb} ({fb / max(1, nb):.2f}), Fisher p={fisher(fa, na - fa, fb, nb - fb):.3g}")
            per = Counter(c for i in ds for c, v in fl[i].items() if v)
            line += f"; flags per concept {dict(sorted(per.items()))}"
        print(line)
    print("\n## Docstrings")
    base = [json.loads(l) for l in open("data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl")]
    for a in m9.ARMS:
        ds = docs(a)
        if len(ds) == len(records):
            print(f"- {a}: docstrings byte-identical to the original Advanced run: {sum(ds[i]['generated_docstring'] == base[i]['generated_docstring'] for i in ds)}/{len(ds)}")
    for a in m9.ARMS:
        ds = docs(a)
        if ds:
            n = len(ds)
            print(f"- {a}: {n} completions, mean {sum(len(d['completion']) for d in ds.values()) / n:.0f} chars; docstring from /** */ "
                  f"{sum(d['generated_docstring'].startswith(chr(10) + '/**') for d in ds.values())}, mean docstring "
                  f"{sum(len(d['generated_docstring']) for d in ds.values()) / n:.0f} chars; focal-body windows in the docstring "
                  f"(test prompt): {[tag(i) for i in sorted(ds) if M5.body_leaks(records[i], ds[i]['generated_docstring'])]}")


if __name__ == "__main__":
    data, keep = outcomes()
    calls_and_cost()
    mechanism(data, keep)
