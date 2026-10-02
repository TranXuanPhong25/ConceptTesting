"""Numbers for RESULTS.md (host python, stdlib only).  usage: python3 m6_agent_oracle/analyze.py > m6_agent_oracle/out/analysis.txt
Outcome parsing (latest_log/parse/row/load/p_mcnemar) is copied from m5_blind_concept_spec/analyze.py (itself m1's).
Also writes out/m_methods.txt (M tests of each arm next to the clarified requirements, for the manual check) and
out/judge_sample.txt (the judge validation sample)."""
import glob, json, os, random, re, sys
from collections import Counter
from math import comb

sys.path.insert(0, "m6_agent_oracle")
import oracle as O

D = "m6_agent_oracle"
LOGS = "data/rq1/logs/Gemini-2-5-flash_gen_test_evaluate_buggy_gen_test_non_private_or_default_{}_log_*.log"
RQ1 = "data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{}_with_completion.jsonl"
KEYS = {"M": "reported test passed on buggy but failed on fixed", "E": "reported test passed on fixed but failed on buggy",
        "TN": "reported test passed on both", "FP": "reported test failed on both", "GEN": "Total test generated"}
# name, FILE_POST_FIX, folder holding its parts plan (None: a single log)
CONFIGS = [("Only Doc", "unified_invoked_docstring_prompt", None),
           ("Advanced Doc", "unified_invoked_advanced_docstring_prompt", None),
           ("m4 Concept-Inputs", "m4_concept_inputs", "m4_concept_inputs"),
           ("m5 B blind+Javadoc", "m5_blind_concept_javadoc", "m5_blind_concept_spec"),
           ("m6 blind oracle", "m6_oracle_blind", D),
           ("m6 sees-code oracle", "m6_oracle_sees_code", D)]
BLIND, SEES = "m6 blind oracle", "m6 sees-code oracle"
ARM_OF = {BLIND: "oracle_blind", SEES: "oracle_sees_code"}
PAIRS = [(SEES, BLIND), ("Advanced Doc", BLIND), ("Advanced Doc", SEES), ("m4 Concept-Inputs", BLIND),
         ("m5 B blind+Javadoc", BLIND), ("Only Doc", BLIND)]
HEAD = "| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |\n|---|---|---|---|---|---|---|---|"
norm = lambda s: re.sub(r"\s+", " ", s or "").strip()


# ---- copied from m5_blind_concept_spec/analyze.py
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


def test_src(completion, name):
    m = re.search(r"void\s+" + re.escape(name) + r"\s*\(", completion or "")
    if not m:
        return "(not found)"
    s = completion.rfind("@Test", 0, m.start()); s = s if s >= 0 and m.start() - s < 200 else m.start()
    e = completion.find("@Test", m.end())
    return completion[s:e if e > 0 else len(completion)].strip()
# ----


def outcomes(data, ids, sigs, keep, tag):
    sub = {"all": keep, "without Gson_4": [i for i in keep if ids[i] != "Gson_4_buggy"],
           "without Gson_4 and Cli_1": [i for i in keep if ids[i] not in ("Gson_4_buggy", "Cli_1_buggy")]}
    for label, idx in sub.items():
        print(f"\n## Intersection of clean methods, {label}: {len(idx)} methods\n\n{HEAD}")
        for name, ms in data.items():
            print(row(name, [ms[i] for i in idx]))
        has = lambda name, k: [data[name][i]["counts"][k] > 0 for i in idx]
        print()
        for a, b in [p for p in PAIRS if p[0] in data and p[1] in data]:
            out = []
            for k in ("M", "E"):
                oa, ob, p = p_mcnemar(has(a, k), has(b, k))
                out.append(f"≥1 {k} {sum(has(b, k))} vs {sum(has(a, k))}: only {b} {ob}, only {a} {oa}, p={p:.2g}")
            print(f"McNemar {b} vs {a}: " + "; ".join(out))
    print("\n## Each config on its own clean methods\n\n" + HEAD)
    for name, ms in data.items():
        print(row(f"{name} ({sum(not m['glitch'] for m in ms)} methods)", [m for m in ms if not m["glitch"]]))
    print("\n## Per-method changes (intersection)")
    for a, b in [p for p in PAIRS[:3] if p[0] in data and p[1] in data]:
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


def mechanism(records, evs, qs, an):
    print("\n## Questions")
    qrecs = [json.loads(l) for l in open(f"{D}/out/questions.jsonl")]
    nq = [len(r["questions"]) for r in qrecs]
    rej = sum(bool(q["issues"]) for r in qrecs for a in r["attempts"] for q in a["checked"])
    reasons = Counter(re.sub(r":.*|'.*", "", x).strip() for r in qrecs for a in r["attempts"] for q in a["checked"] for x in q["issues"])
    print(f"- {sum(nq)} questions in {len(nq)} methods (min {min(nq)}, max {max(nq)}, {sum(n == O.MAX_Q for n in nq)} methods with {O.MAX_Q}); "
          f"calls {sum(r['calls'] for r in qrecs)} ({sum(len(r['attempts']) > 1 for r in qrecs)} methods re-asked after the guard, "
          f"{sum(r['calls'] - len(r['attempts']) for r in qrecs)} parse re-asks); rejected question instances {rej}: {dict(reasons)}")
    print(f"- concepts: {dict(Counter(q['concept'].split()[0] for r in qrecs for q in r['questions']).most_common())}")

    print("\n## Evidence packs")
    ov = sum(bool(e["overloads"]) for e in evs.values()); ca = sum(bool(e["callers"]) for e in evs.values())
    ch = sorted(e["blind_pack_chars"] for e in evs.values())
    print(f"- methods with ≥1 same-name method {ov}, with ≥1 caller snippet {ca}, with neither {sum(not e['overloads'] and not e['callers'] for e in evs.values())}; "
          f"snippets/same-name methods dropped for sharing a 40-char window with the focal body: {sum(len(e['dropped_for_body_overlap']) for e in evs.values())} "
          f"in {sum(bool(e['dropped_for_body_overlap']) for e in evs.values())} methods; blind pack chars median {ch[len(ch) // 2]}, max {ch[-1]}; "
          f"blind packs with a focal-body window {sum(bool(e['blind_pack_body_leaks']) for e in evs.values())}; main sources unmodified in all checkouts: {all(e['src_unmodified'] for e in evs.values())}")
    # offline: other buggy code in the blind pack. (a) another dataset focal method of the same bug; (b) a buggy-side
    # line changed by the fix (fix_info diffs run fixed -> buggy, so '+' lines are buggy code) outside the focal method
    by_bug = {}
    for i, r in enumerate(records):
        by_bug.setdefault(r["extra:project_name"], []).append(i)
    other_focal, patched = [], []
    for i, r in enumerate(records):
        pack = norm(O.render_pack(r, evs[i], False))
        sib = [j for j in by_bug[r["extra:project_name"]] if j != i and norm(records[j]["source:source_method_code_format"])[:200] in pack]
        if sib:
            other_focal.append((i, sib))
        info = json.load(open(f"data/d4j2_fix_info/{evs[i]['bug']}/buggy_fix_info.json"))
        body = norm(r["source:source_method_code_format"])
        lines = {norm(l[1:]) for fc in info["fixing_changes"] for l in fc["diff"].splitlines()
                 if l.startswith("+") and not l.startswith("+++") and len(norm(l[1:])) >= 20}
        hit = [l for l in lines if l not in body and l in pack]
        if hit:
            patched.append((i, hit[:2]))
    tag = lambda i: f"{records[i]['extra:project_name'].replace('_buggy', '')}.{records[i]['source:source_method_name']}"
    print(f"- blind packs containing another focal method of the same bug (as a same-name method): {len(other_focal)}: "
          + ", ".join(f"{tag(i)} <- {[tag(j) for j in s]}" for i, s in other_focal))
    print(f"- blind packs containing a buggy line changed by the fix outside the focal method: {len(patched)}: "
          + "; ".join(f"{tag(i)}: {h}" for i, h in patched))

    print("\n## Answers per arm (all 78 methods)")
    for arm in O.ARMS:
        rs = [json.loads(l) for l in open(f"{D}/out/answers_{arm}.jsonl")]
        A = [(i, q, an[arm][i][q["id"]]) for i in sorted(an[arm]) for q in qs[i]]
        und = [x for _, _, x in A if x["undetermined"]]
        explicit = sum(O.is_undetermined(x["expected"]) for x in und)
        print(f"\n### {arm}: calls {sum(r['calls'] for r in rs)} (re-asks: {[(r['id'], r['calls']) for r in rs if r['calls'] > 1]})")
        print(f"- answers {len(A)}; UNDETERMINED {len(und)} ({100 * len(und) / len(A):.1f}%): explicit {explicit}, no evidence item {len(und) - explicit}, "
              f"missing in the reply {sum(x['missing'] for _, _, x in A)}; methods with all questions undetermined "
              f"{sum(all(an[arm][i][q['id']]['undetermined'] for q in qs[i]) for i in an[arm])}, with none {sum(not any(an[arm][i][q['id']]['undetermined'] for q in qs[i]) for i in an[arm])}")
        items = [(i, e) for i, _, x in A if not x["undetermined"] for e in x["evidence"]]
        src = Counter(e["source"] for _, e in items)
        print(f"- evidence items of determined answers {len(items)}: " + ", ".join(f"{k} {v} ({100 * v / len(items):.0f}%)" for k, v in src.most_common()))
        cites = Counter(s for _, _, x in A if not x["undetermined"] for s in {e["source"] for e in x["evidence"]})
        det = len(A) - len(und)
        print(f"- determined answers citing each source (share of {det}): " + ", ".join(f"{k} {v} ({100 * v / det:.0f}%)" for k, v in cites.most_common()))
        only = Counter("+".join(sorted({e["source"] for e in x["evidence"]})) for _, _, x in A if not x["undetermined"])
        print(f"- source combinations (top): {dict(only.most_common(8))}")
        # quotes copied verbatim from the material the arm saw (naming/standard quotes need not be)
        packs = {i: norm(O.render_pack(records[i], evs[i], arm == "oracle_sees_code")) for i in an[arm]}
        loose = {i: squash(p) for i, p in packs.items()}
        ver = [(i, e) for i, e in items if e["source"] not in ("naming", "standard") and e["quote"]]
        ok = sum(verbatim(e["quote"], loose[i]) for i, e in ver)
        print(f"- quotes found in the arm's pack (ignoring whitespace, case, Javadoc '*', HTML tags and '...' elisions; "
              f"javadoc/caller/overload/class_context/implementation/other): {ok} / {len(ver)} ({100 * ok / len(ver):.0f}%)")
        by_c = Counter(); un_c = Counter()
        for i, q, x in A:
            c = q["concept"].split()[0]; by_c[c] += 1; un_c[c] += x["undetermined"]
        print("- UNDETERMINED by question concept: " + ", ".join(f"{c} {un_c[c]}/{by_c[c]}" for c in sorted(by_c)))
        if arm == "oracle_blind":  # the orchestrator's check: no blind quote may come from the focal body
            susp = []
            for i, e in items + [(i, e) for i, _, x in A if x["undetermined"] for e in x["evidence"]]:
                q = norm(e["quote"]); body = norm(records[i]["source:source_method_code_format"])
                if len(q) >= 15 and q in body and q not in packs[i] or e["source"] in ("implementation", "other"):
                    susp.append((records[i]["extra:project_name"], e["source"], e["quote"][:120], q in body, q in packs[i]))
            print(f"- blind evidence items labelled implementation/other, or quoting focal-body text absent from the blind pack: {len(susp)}")
            for s in susp:
                print(f"    {s[0]} source={s[1]} in_focal_body={s[3]} in_blind_pack={s[4]}: {s[2]!r}")

    # how often do the two arms disagree on the same question?
    both = [(i, q) for i in an[O.ARMS[0]] for q in qs[i] if not an[O.ARMS[0]][i][q["id"]]["undetermined"] and not an[O.ARMS[1]][i][q["id"]]["undetermined"]]
    same = sum(norm(an[O.ARMS[0]][i][q["id"]]["expected"]).lower().strip(".") == norm(an[O.ARMS[1]][i][q["id"]]["expected"]).lower().strip(".") for i, q in both)
    print(f"\n- questions answered by both arms {len(both)}; identical expected text {same}")


def judge(records, qs, an, data, keep, path=f"{D}/out/judge.jsonl", label="v2 (used)", sample_n=10):
    if not os.path.exists(path):
        return print(f"\n(no {path} yet)")
    J = {r["idx"]: r for r in map(json.loads, open(path))}
    rows = [(i, j) for i in sorted(J) for j in J[i]["judgements"]]
    print(f"\n## Offline judge {label}, {path} (patch shown to the judge only): {len(J)} methods, {len(rows)} questions, "
          f"calls {sum(r['calls'] for r in J.values())}, unparsed question judgements {sum(not j['parsed'] for _, j in rows)}")
    rel = [(i, j) for i, j in rows if j["relevant"]]
    print(f"- questions on the bug's changed behaviour (relevant): {len(rel)} in {len({i for i, _ in rel})} methods; by concept "
          f"{dict(Counter(j['concept'].split()[0] for _, j in rel).most_common())}")
    for arm in O.ARMS:
        c = Counter(j[arm] for _, j in rel); n = max(1, len(rel))
        cs = Counter(j[arm] for _, j in rows if not j["relevant"]); ns = max(1, sum(cs.values()))
        print(f"- {arm}: relevant questions: " + ", ".join(f"{k} {c[k]} ({100 * c[k] / n:.0f}%)" for k in ("BUGGY", "FIXED", "NEITHER", "SAME", "UNDETERMINED", None) if c[k])
              + " | other questions: " + ", ".join(f"{k} {cs[k]} ({100 * cs[k] / ns:.0f}%)" for k in ("SAME", "NEITHER", "UNDETERMINED", "BUGGY", "FIXED", None) if cs[k]))
        print(f"    determined relevant answers (BUGGY or FIXED) that match buggy: {c['BUGGY']} / {c['BUGGY'] + c['FIXED']}; "
              f"methods with ≥1 BUGGY answer {len({i for i, j in rel if j[arm] == 'BUGGY'})}, with ≥1 FIXED answer {len({i for i, j in rel if j[arm] == 'FIXED'})}")
    pair = Counter((j[O.ARMS[0]], j[O.ARMS[1]]) for _, j in rel)
    print("- relevant questions, (blind, sees-code) verdict pairs: " + ", ".join(f"{k}: {v}" for k, v in pair.most_common()))
    oa, ob, p = p_mcnemar([j[O.ARMS[1]] == "BUGGY" for _, j in rel], [j[O.ARMS[0]] == "BUGGY" for _, j in rel])
    print(f"- exact McNemar, relevant questions answered BUGGY: sees-code only {oa}, blind only {ob}, p={p:.2g}")
    for arm, name in [x for x in ((O.ARMS[0], BLIND), (O.ARMS[1], SEES)) if x[1] in data]:
        for verdict, k in (("BUGGY", "M"), ("FIXED", "E")):
            withv = [i for i in keep if any(j[arm] == verdict for j in J[i]["judgements"] if j["relevant"])]
            without = [i for i in keep if i not in withv]
            f = lambda xs: f"{sum(data[name][i]['counts'][k] > 0 for i in xs)}/{len(xs)}"
            print(f"- {arm}: methods with ≥1 {verdict} relevant answer: ≥1 {k} in {f(withv)}; without: {f(without)}")
    # validation against my own verdicts (manual_judge.json)
    man = json.load(open(f"{D}/manual_judge.json"))
    keys = sorted({k.rsplit(":", 1)[0] for k in man if k.endswith(":relevant") and man[k] is not None}, key=lambda k: (int(k.split(":")[0]), k))
    byq = {(i, j["qid"]): j for i, j in rows}
    mrel = [k for k in keys if man[k + ":relevant"]]
    rel_ok = sum(byq[(int(k.split(":")[0]), k.split(":")[1])]["relevant"] == man[k + ":relevant"] for k in keys)
    strict = coll = tot = 0
    col = lambda v: "CORRECT" if v in ("FIXED", "SAME") else v
    for k in keys:
        j = byq[(int(k.split(":")[0]), k.split(":")[1])]
        for arm in O.ARMS:
            m = man[f"{k}:{arm}"]
            if m != "UNDETERMINED":
                tot += 1; strict += j[arm] == m; coll += col(j[arm]) == col(m)
    jb = sum(byq[(int(k.split(":")[0]), k.split(":")[1])][arm] == "BUGGY" for k in keys for arm in O.ARMS)
    mb = sum(man[f"{k}:{arm}"] == "BUGGY" for k in keys for arm in O.ARMS)
    jr = [k for k in keys if byq[(int(k.split(":")[0]), k.split(":")[1])]["relevant"]]
    print(f"- relevance: of the judge's relevant questions in my set {sum(man[k + ':relevant'] for k in jr)}/{len(jr)} are relevant; "
          f"of mine the judge finds {sum(k in jr for k in mrel)}/{len(mrel)}")
    for arm in O.ARMS:
        print(f"  {arm}: BUGGY labels judge {sum(byq[(int(k.split(':')[0]), k.split(':')[1])][arm] == 'BUGGY' for k in keys)}, "
              f"me {sum(man[f'{k}:{arm}'] == 'BUGGY' for k in keys)}, both {sum(byq[(int(k.split(':')[0]), k.split(':')[1])][arm] == 'BUGGY' == man[f'{k}:{arm}'] for k in keys)}")
    print(f"- validation on my {len(keys)} manually judged questions (manual_judge.json): relevance agrees {rel_ok}/{len(keys)} "
          f"(I mark {len(mrel)} relevant, the judge {sum(byq[(int(k.split(':')[0]), k.split(':')[1])]['relevant'] for k in keys)}); "
          f"answer verdicts agree {strict}/{tot} exactly, {coll}/{tot} with FIXED/SAME merged as 'correct'; BUGGY labels: judge {jb}, me {mb}")
    if sample_n:  # a fresh sample of judged-relevant questions outside the manual set, for a further manual read
        first = {k.rsplit(":", 1)[0] for k in json.load(open(f"{D}/manual_judge.json")) if k.endswith(":note")} - {
            "18:Q1", "74:Q6", "7:Q2", "20:Q5", "41:Q4", "2:Q4", "2:Q6", "64:Q1", "31:Q2", "4:Q5"}  # the sample is drawn outside the first set
        cand = [(i, j) for i, j in rel if f"{i}:{j['qid']}" not in first]
        sample = random.Random(7).sample(cand, min(sample_n, len(cand)))
        with open(f"{D}/out/judge_sample.txt", "w", errors="backslashreplace") as f:
            for i, j in sample:
                q = [x for x in qs[i] if x["id"] == j["qid"]][0]
                f.write(f"\n{'=' * 100}\n{i}:{j['qid']} {records[i]['extra:project_name']} {records[i]['source:source_method_name']}\n"
                        f"input: {q['input']}\nquestion: {q['question']}\njudge: buggy = {j['buggy_behaviour']} | fixed = {j['fixed_behaviour']}\n")
                for arm in O.ARMS:
                    f.write(f"  {arm}: judge {j[arm]} | answer: {an[arm][i][q['id']]['expected']}\n")
    return J


def m_dump(records, qs, an, data, keep):
    labels = json.load(open("m2_concept_diag/manual_labels.json"))
    with open(f"{D}/out/m_methods.txt", "w", errors="backslashreplace") as f:
        for name in (BLIND, SEES):
            comp = [json.loads(l) for l in open(RQ1.format(dict((n, p) for n, p, _ in CONFIGS)[name]))]
            for i in keep:
                m = data[name][i]
                if not m["counts"]["M"]:
                    continue
                f.write(f"\n{'=' * 100}\n{name} | {i} {records[i]['extra:project_name']} {records[i]['source:source_method_name']} | M {m['counts']['M']} "
                        f"E {m['counts']['E']} | bug concepts {labels[str(i)]['concepts']}: {labels[str(i)]['note']}\n")
                for t, c in m["cats"].items():
                    if c == "M":
                        f.write(f"--- M test {t}:\n{test_src(comp[i].get('completion'), t)}\n")
                a = an[ARM_OF[name]][i]
                f.write("--- clarified requirements:\n" + "\n".join(
                    f"  {q['id']} {q['input']} -> {'UNDETERMINED' if a[q['id']]['undetermined'] else a[q['id']]['expected']}" for q in qs[i]) + "\n")


def main():
    records = O.load_records()
    evs = O.load_evidence()
    qs = {r["idx"]: r["questions"] for r in map(json.loads, open(f"{D}/out/questions.jsonl"))}
    an = {arm: {r["idx"]: r["answers"] for r in map(json.loads, open(f"{D}/out/answers_{arm}.jsonl"))} for arm in O.ARMS}
    ids = [r["extra:project_name"] for r in records]
    tag = lambda i: f"{ids[i].replace('_buggy', '')}.{records[i]['source:source_method_name']}"
    have = [c for c in CONFIGS if c[0] not in (BLIND, SEES) or os.path.exists(f"{D}/out/{c[1]}_parts.json")]  # m6 arms once evaluated
    data = {name: load(fpf, folder) for name, fpf, folder in have}
    sigs = [m["sig"] for m in data["Advanced Doc"]]
    for name, ms in data.items():
        assert [m["sig"] for m in ms] == sigs and len(ms) == len(records), f"method order differs: {name}"
    glitched = {name: [i for i, m in enumerate(ms) if m["glitch"]] for name, ms in data.items()}
    keep = [i for i in range(len(sigs)) if not any(i in g for g in glitched.values())]
    print("glitched (excluded):", {n: [ids[i] for i in g] for n, g in glitched.items()})
    outcomes(data, ids, sigs, keep, tag)
    mechanism(records, evs, qs, an)
    judge(records, qs, an, data, keep, f"{D}/out/judge_v1.jsonl", "v1 (not used: relevance unreliable)", 0)
    judge(records, qs, an, data, keep)
    if BLIND in data and SEES in data:
        m_dump(records, qs, an, data, keep)
    print("\n## LLM calls (test generation)")
    for name, fpf, _ in CONFIGS[4:]:
        recs = [json.loads(l) for l in open(RQ1.format(fpf))]
        print(f"- {name}: test-generation records {len(recs)}, with a ```java block {sum('```java' in (r.get('completion') or '') for r in recs)}, "
              f"prompts with a 60-char mid-body window {sum(any(w in norm(r['content']) for w in mid_windows(records[k])) for k, r in enumerate(recs))}")


def squash(s):
    return re.sub(r"\s+", " ", re.sub(r"</?\w+>|[*/]|\{@\w+\s*|\}", " ", s)).strip().lower()


def verbatim(quote, loose_pack):
    quote = re.sub(r"^\s*\[\d+\]\s*", "", quote)  # snippet number copied with the quote
    parts = [p.strip(" .,;:") for p in re.split(r"\.\.\.|…", squash(quote))]
    parts = [p for p in parts if len(p) >= 8] or [squash(quote)]
    return all(p in loose_pack for p in parts)


def mid_windows(rec, w=60):
    b = norm(rec["source:source_method_code_format"]); b = b[b.find("{") + 1:]
    return [b[k:k + w] for k in range(0, max(1, len(b) - w), w) if len(b[k:k + w].strip()) >= w // 2]


if __name__ == "__main__":
    main()
