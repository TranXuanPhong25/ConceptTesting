"""Numbers for RESULTS.md (host python, stdlib only).

usage: python3 m1_test_review/analyze.py <baseline FILE_POST_FIX> <arm FILE_POST_FIX>
Per-test outcomes are recovered from the "Reported execution results" lists in the evaluation logs
(failing-on-buggy and failing-on-fixed test names); tests in neither list are TN or did not compile.
"""
import glob, json, os, re, sys
from math import comb

LOGS = "data/rq1/logs/Gemini-2-5-flash_gen_test_evaluate_buggy_gen_test_non_private_or_default_{}_log_*.log"
KEYS = {"M": "reported test passed on buggy but failed on fixed", "E": "reported test passed on fixed but failed on buggy",
        "TN": "reported test passed on both", "FP": "reported test failed on both", "GEN": "Total test generated"}


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
        out.append({"sig": block.split("method signature: ")[1].split("\n")[0].strip(), "counts": diff, "cats": cats, "glitch": glitch,
                    "consistent": (len(b - f), len(f - b), len(b & f)) == (diff["E"], diff["M"], diff["FP"])})
        prev = cur
    return out


def load(fpf):
    """Per-method blocks of a config; merges the resumed parts written by eval_parts.py when there are any."""
    plan = f"m1_test_review/out/{fpf}_parts.json"
    parts = json.load(open(plan)) if os.path.exists(plan) else [{"fpf": fpf, "n": None}]
    meths = [m for p in parts if "idx" not in p for m in parse(latest_log(p["fpf"]), p["n"])]
    for p in parts:  # redo parts replace infrastructure-failed blocks
        for i, m in zip(p.get("idx", []), parse(latest_log(p["fpf"]))):
            assert meths[i]["sig"] == m["sig"]
            meths[i] = m
    tot = {k: sum(m["counts"][k] for m in meths) for k in KEYS}
    return meths, {k: tot[k] for k in ("M", "E", "TN", "FP")}, tot["GEN"], [latest_log(p["fpf"]) for p in parts]


def mcnemar(a, b):
    """exact two-sided McNemar on paired booleans a (baseline), b (arm)."""
    n01 = sum(x and not y for x, y in zip(a, b)); n10 = sum(y and not x for x, y in zip(a, b)); n = n01 + n10
    p = min(1.0, 2 * sum(comb(n, k) for k in range(min(n01, n10) + 1)) / 2 ** n) if n else 1.0
    return f"lost {n01}, gained {n10}, p={p:.3f}"


def row(name, tot, gen, meths):
    c = sum(tot.values()); pct = lambda k: f"{tot[k]} ({100 * tot[k] / c:.2f}%)"
    e1 = sum(m["counts"]["E"] > 0 for m in meths); m1 = sum(m["counts"]["M"] > 0 for m in meths)
    return f"| {name} | {gen} / {c} | {pct('M')} | {pct('E')} | {pct('FP')} | {tot['E'] / max(1, tot['E'] + tot['FP']):.3f} | {m1} | {e1} |"


def main(base, arm):
    bm, btot, bgen, blogs = load(base)
    am, atot, agen, alogs = load(arm)
    assert [m["sig"] for m in bm] == [m["sig"] for m in am], "method order differs between logs"
    dec = [json.loads(l) for l in open(f"m1_test_review/out/{arm}_decisions.jsonl")]
    raw = [json.loads(l) for l in open(f"m1_test_review/out/{arm}_raw.jsonl")]
    sigs = [m["sig"] for m in bm]
    n = len(dec); ab = [d for d in dec if d["decision"] == "ABSTAIN"]; rw = [d for d in dec if d["decision"] == "REWRITE"]
    r = len(ab) / n
    print(f"## {arm} vs {base}\n")
    print(f"logs: baseline {blogs}; arm {alogs}")
    print(f"per-test lists consistent with counters: baseline {sum(m['consistent'] for m in bm)}/{len(bm)}, arm {sum(m['consistent'] for m in am)}/{len(am)} methods\n")
    print("| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |\n|---|---|---|---|---|---|---|---|")
    print(row(f"baseline `{base}`", btot, bgen, bm))
    print(row(f"review `{arm}`", atot, agen, am))
    exp = {k: btot[k] * (1 - r) for k in btot}; c = sum(exp.values())
    e1 = sum(1 - r ** m["counts"]["E"] for m in bm); m1 = sum(1 - r ** m["counts"]["M"] for m in bm)
    print(f"| random abstain r={r:.3f} (expected) | {bgen * (1 - r):.0f} / {c:.0f} | {exp['M']:.1f} ({100 * exp['M'] / c:.2f}%) | {exp['E']:.1f} ({100 * exp['E'] / c:.2f}%) "
          f"| {exp['FP']:.1f} ({100 * exp['FP'] / c:.2f}%) | {btot['E'] / max(1, btot['E'] + btot['FP']):.3f} | {m1:.1f} | {e1:.1f} |\n")
    print(f"reviewed @Test methods {n}: KEEP {n - len(ab) - len(rw)}, REWRITE {len(rw)} ({100 * len(rw) / n:.1f}%), ABSTAIN {len(ab)} ({100 * r:.1f}%); "
          f"expected-value changes logged {sum(len(d['value_changes']) for d in rw)}; notes {sorted({d['note'] for d in dec if d['note']})}")
    print(f"reviewer LLM calls: {sum(x['calls'] for x in raw)} (files reviewed {len(raw)}; parse failures {sum(x['reply'] is None for x in raw)})\n")
    base_cat = lambda d: bm[sigs.index(d["method_signature"])]["cats"].get(d["test"], "TN/not-compiled")
    arm_cat = lambda d: am[sigs.index(d["method_signature"])]["cats"].get(d["test"], "TN/not-compiled")
    tally = lambda ds, f: {k: sum(f(d) == k for d in ds) for k in ("E", "M", "FP", "TN/not-compiled")}
    print(f"baseline outcome of ABSTAINED tests: {tally(ab, base_cat)} (random abstention would remove E/M/FP in proportion: "
          f"E {btot['E'] * r:.1f}, M {btot['M'] * r:.1f}, FP {btot['FP'] * r:.1f})")
    kept = [d for d in dec if d["decision"] == "KEEP"]
    print(f"baseline outcome of KEPT tests: {tally(kept, base_cat)}; same outcome in the arm run: {sum(base_cat(d) == arm_cat(d) for d in kept)}/{len(kept)}")
    print(f"REWRITTEN tests, baseline outcome: {tally(rw, base_cat)} -> arm outcome: {tally(rw, arm_cat)}\n")
    be = [m["counts"]["E"] > 0 for m in bm]; ae = [m["counts"]["E"] > 0 for m in am]
    bmm = [m["counts"]["M"] > 0 for m in bm]; amm = [m["counts"]["M"] > 0 for m in am]
    print(f"McNemar methods ≥1 E (baseline vs review): {mcnemar(be, ae)}")
    print(f"McNemar methods ≥1 M (baseline vs review): {mcnemar(bmm, amm)}\n")
    # vs the random-abstention control: tail probabilities of what the reviewer did, if it had dropped tests at random
    ab_cat = tally(ab, base_cat); all_cat = tally(dec, base_cat)
    for k in ("E", "FP"):
        print(f"P(random abstention at r drops >= {ab_cat[k]} of the {all_cat[k]} recoverable baseline {k} tests) = {binom_tail(all_cat[k], r, ab_cat[k]):.4f}")
    lost = sum(x and not y for x, y in zip(be, ae))
    print(f"P(random abstention at r loses >= {lost} of the {sum(be)} methods with >=1 E) = {pb_tail([r ** m['counts']['E'] for m in bm if m['counts']['E']], lost):.4f}\n")
    bad = [i for i in range(len(bm)) if bm[i]["glitch"] or am[i]["glitch"]]
    print(f"infrastructure-failed blocks (a run 'failed' with an empty error report): baseline {[bm[i]['sig'].split('#')[1] + '#' + str(i) for i in bad if bm[i]['glitch']]}, "
          f"arm {[am[i]['sig'].split('#')[1] + '#' + str(i) for i in bad if am[i]['glitch']]}")
    keep = [i for i in range(len(bm)) if i not in bad]
    sub = lambda ms: ({k: sum(ms[i]["counts"][k] for i in keep) for k in ("M", "E", "TN", "FP")}, sum(ms[i]["counts"]["GEN"] for i in keep), [ms[i] for i in keep])
    print(f"\nsensitivity, excluding those {len(bad)} methods from both sides ({len(keep)} methods):\n")
    print("| config | generated / compiled | M | E | FP | red-prec | methods ≥1 M | methods ≥1 E |\n|---|---|---|---|---|---|---|---|")
    print(row(f"baseline `{base}`", *sub(bm))); print(row(f"review `{arm}`", *sub(am)))
    print(f"\nMcNemar (subset) ≥1 E: {mcnemar([be[i] for i in keep], [ae[i] for i in keep])}; ≥1 M: {mcnemar([bmm[i] for i in keep], [amm[i] for i in keep])}")


def binom_tail(n, p, k):
    return sum(comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))


def pb_tail(ps, k):
    """P(sum of independent Bernoulli(ps) >= k)."""
    dist = [1.0]
    for p in ps:
        dist = [(dist[j] if j < len(dist) else 0) * (1 - p) + (dist[j - 1] * p if j else 0) for j in range(len(dist) + 1)]
    return sum(dist[k:])


if __name__ == "__main__":
    main(*sys.argv[1:3])
