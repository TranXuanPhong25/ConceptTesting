"""m8 Phase 1 numbers for RESULTS.md (host python, stdlib).  usage: python3 m8_concept_mutants/analyze.py > m8_concept_mutants/out/analysis.txt
Outcome parsing (latest_log / parse / row / load / p_mcnemar) is reused from m6_agent_oracle/analyze.py (m5 -> m1 lineage).
"Advanced + m8" = the union of the two test suites per method (counts added, per-test outcomes merged; glitched if either
run is glitched): the m8 tests are separate test methods, so the Advanced run is reused instead of being re-evaluated.
The fixed version is used here only (arbiter accuracy, offline)."""
import importlib.util, json, sys
from collections import Counter, defaultdict

_spec = importlib.util.spec_from_file_location("m6_analyze", "m6_agent_oracle/analyze.py")
A6 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(A6)

D = "m8_concept_mutants"
ADV, BLIND, MC, MG = "Advanced Doc", "m6 blind oracle", "m8 concept (alone)", "m8 generic (alone)"
UC, UG = "Advanced + m8 concept", "Advanced + m8 generic"
CONFIGS = [(ADV, "unified_invoked_advanced_docstring_prompt", None), (BLIND, "m6_oracle_blind", "m6_agent_oracle"),
           (MC, "m8_concept", D), (MG, "m8_generic", D)]
PAIRS = [(MG, MC), (UG, UC), (ADV, UC), (ADV, UG), (ADV, MC), (BLIND, UC)]  # (a, b): "b vs a"; the first is primary


def union(a, b):
    return [{"sig": x["sig"], "counts": {k: x["counts"][k] + y["counts"][k] for k in x["counts"]}, "cats": {**x["cats"], **y["cats"]},
             "glitch": x["glitch"] or y["glitch"]} for x, y in zip(a, b)]


def table(data, idx, label):
    print(f"\n## {label}: {len(idx)} methods\n\n{A6.HEAD}")
    for name, ms in data.items():
        print(A6.row(name, [ms[i] for i in idx]))
    print()
    has = lambda name, k: [data[name][i]["counts"][k] > 0 for i in idx]
    for a, b in PAIRS:
        out = []
        for k in ("E", "M"):
            oa, ob, p = A6.p_mcnemar(has(a, k), has(b, k))
            out.append(f"≥1 {k} {sum(has(b, k))} vs {sum(has(a, k))}: only {b} {ob}, only {a} {oa}, exact McNemar p={p:.3g}")
        print(f"- {b} vs {a}: " + "; ".join(out))


def arbiter_accuracy(arm, runs, its):
    """per decided item: does the chosen output equal the fixed version's output on that probe input?"""
    ans = {r["idx"]: r["answers"] or {} for r in map(json.loads, open(f"{D}/out/arbiter_{arm}.jsonl"))}
    c = Counter()
    for i, a in ans.items():
        fx = (runs.get(i) or {}).get("fixed") or {}
        for it in its[str(i)][arm]["items"]:
            ch = a.get(str(it["item"]), {}).get("choice", "UNDETERMINED")
            c["items"] += 1
            f = fx.get(it["k"])
            rel = f is not None and f != it["orig"]
            c["bug_relevant"] += rel
            if ch == "UNDETERMINED":
                c["undetermined"] += 1; c["undet_relevant"] += rel
                continue
            chosen, other = (it["A"], it["B"]) if ch == "A" else (it["B"], it["A"])
            c["decided"] += 1
            c["chose_mutant"] += chosen == it["mut"]
            if f is None:
                c["no_fixed_output"] += 1
            elif f == chosen:
                c["correct"] += 1; c["correct_relevant"] += rel
            elif f == other:
                c["wrong"] += 1; c["wrong_relevant"] += rel
            else:
                c["neither"] += 1; c["neither_relevant"] += rel
    return c


def main():
    records = [json.loads(l) for l in open("data/prompts/buggy_source_data_unified_invoked.jsonl")]
    ids = [r["extra:project_name"] for r in records]
    tag = lambda i: f"{ids[i].replace('_buggy', '')}.{records[i]['source:source_method_name']}"
    data = {name: A6.load(fpf, folder) for name, fpf, folder in CONFIGS}
    data[UC], data[UG] = union(data[ADV], data[MC]), union(data[ADV], data[MG])
    sigs = [r["source:source_method_signature"] for r in records]
    for name, ms in data.items():
        assert [m["sig"] for m in ms] == sigs, name
    glitched = {n: [i for i, m in enumerate(ms) if m["glitch"]] for n, ms in data.items()}
    keep = [i for i in range(len(sigs)) if not any(i in g for g in glitched.values())]
    print("glitched (excluded):", {n: [ids[i] for i in g] for n, g in glitched.items() if g})
    table(data, keep, "Intersection of clean methods")
    table(data, [i for i in keep if ids[i] not in ("Gson_4_buggy", "Cli_1_buggy")], "Sensitivity: without Gson_4 and Cli_1")
    print("\n## Per-method changes (intersection)")
    for a, b in PAIRS[:3]:
        for k in ("E", "M"):
            g = [tag(i) for i in keep if data[b][i]["counts"][k] and not data[a][i]["counts"][k]]
            l = [tag(i) for i in keep if data[a][i]["counts"][k] and not data[b][i]["counts"][k]]
            print(f"- ≥1 {k}, {b} vs {a}: only {b} {g}; only {a} {l}")
    for name in (MC, MG):
        print(f"- {name} M-methods: " + ", ".join(f"{tag(i)}:{data[name][i]['counts']['M']}" for i in keep if data[name][i]["counts"]["M"]))
        print(f"- {name} E-methods: " + ", ".join(f"{tag(i)}:{data[name][i]['counts']['E']}" for i in keep if data[name][i]["counts"]["E"]))

    # ---- pipeline internals
    its = json.load(open(f"{D}/out/items.json"))
    runs = {r["idx"]: r for r in map(json.loads, open(f"{D}/out/probe_runs.jsonl"))}
    chk = json.load(open(f"{D}/out/probe_check.json"))
    gen = [json.loads(l) for l in open(f"{D}/out/probe_gen.jsonl")]
    print("\n## Probes")
    ok = [i for i, c in chk.items() if c["ok"]]
    nd = sum(sum(v != r["orig2"].get(k) for k, v in r["orig"].items()) for r in runs.values())
    print(f"- methods {len(gen)}, probe compiled {len(ok)}, attempts {Counter(len(g['attempts']) for g in gen)}, cases "
          f"{sum(len(chk[i]['cases']) for i in ok)} (median {sorted(len(chk[i]['cases']) for i in ok)[len(ok) // 2]}), "
          f"nondeterministic cases {nd}, probes that compile on the fixed version {sum(r['fixed_compiled'] for r in runs.values())}/{len(runs)}")
    print(f"- probe source quoting the focal body (40-char windows): {[k for k, c in chk.items() if c.get('body_leaks_in_probe')]}")
    for arm in ("concept", "generic"):
        n = [len(v[arm]["items"]) for v in its.values()]
        print(f"- {arm}: distinct differences {sum(v[arm]['n_diff'] for v in its.values())}, items sent {sum(n)} "
              f"(methods with ≥1 item {sum(x > 0 for x in n)})")
    sel = json.load(open(f"{D}/out/selection.json"))
    for arm in ("concept", "generic"):
        dist = Counter()
        for i, r in runs.items():
            for m in sel[str(i)][arm]:
                dist[any(r["mutants"][m].get(k) not in (None, "timeout", "DUP", v) for k, v in r["orig"].items() if v == r["orig2"].get(k))] += 1
        print(f"- {arm}: selected mutants distinguished by ≥1 probe case {dist[True]}/{sum(dist.values())}")

    print("\n## Arbiter (offline accuracy: chosen output vs the fixed version's output on the same probe input)")
    for arm in ("concept", "generic"):
        c = arbiter_accuracy(arm, runs, its)
        dec = max(1, c["decided"])
        print(f"- {arm}: items {c['items']}, UNDETERMINED {c['undetermined']} ({100 * c['undetermined'] / max(1, c['items']):.0f}%), decided {c['decided']}, "
              f"chose the mutant's output {c['chose_mutant']} ({100 * c['chose_mutant'] / dec:.0f}%); fixed = chosen {c['correct']}, fixed = other "
              f"{c['wrong']}, neither {c['neither']}, no fixed output {c['no_fixed_output']}; accuracy where fixed equals one side "
              f"{c['correct'] / max(1, c['correct'] + c['wrong']):.3f}")
        print(f"    bug-relevant items (fixed output differs from the current one): {c['bug_relevant']}; decided {c['correct_relevant'] + c['wrong_relevant'] + c['neither_relevant']}"
              f" (correct {c['correct_relevant']}, wrong {c['wrong_relevant']}, neither {c['neither_relevant']}), UNDETERMINED {c['undet_relevant']}")
        t = json.load(open(f"{D}/out/tests_{arm}.json"))
        kept_mut = sum(1 for x in t.values() for k in x["kept"] if not x["self_check"][str(k)][1])
        print(f"    tests {sum(len(x['kept']) for x in t.values())} in {sum(bool(x['kept']) for x in t.values())} methods ({kept_mut} assert the "
              f"mutant's output, i.e. fail on the current code); dropped: compile errors {sum(len(x['dropped_compile']) for x in t.values())}, "
              f"self-check mismatches on the buggy code {sum(len(x['dropped_self_check']) for x in t.values())}")

    print("\n## LLM calls and cost (out/llm_calls.jsonl: one line per billed response)")
    calls = [json.loads(l) for l in open(f"{D}/out/llm_calls.jsonl")]
    by = defaultdict(Counter)
    for c in calls:
        by[c["step"]]["calls"] += 1; by[c["step"]]["in"] += c["prompt_tokens"]; by[c["step"]]["out"] += c["output_tokens"] + c["thought_tokens"]
        by[c["step"]]["usd"] += c["usd"]
    for s, c in sorted(by.items()):
        print(f"- {s}: calls {c['calls']}, input tokens {c['in']}, output tokens {c['out']}, {c['usd']:.3f} USD")
    print(f"- total: calls {len(calls)}, {sum(c['usd'] for c in calls):.3f} USD (prices: input 0.30, output 2.50 USD per 1M tokens)")
    for arm in ("concept", "generic"):
        rs = [json.loads(l) for l in open(f"{D}/out/arbiter_{arm}.jsonl")]
        print(f"- arbiter {arm}: methods {len(rs)}, calls {sum(r['calls'] for r in rs)}; probe calls (shared by both arms) "
              f"{sum(len(g['attempts']) for g in gen)}")


if __name__ == "__main__":
    main()
