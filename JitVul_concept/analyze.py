#!/usr/bin/env python3
"""Pairwise metrics per arm and exact McNemar tests on pair-correct (P-C).

Reads out/responses/ARM.jsonl and writes out/summary.md. Verdicts use the authors' rule
("@@vulnerable@@" anywhere in the lowercased reply). "strict" re-parses the raw reply and keeps the last tag.
"""
import re
from math import comb

from harness import ARMS, BLOCKS, IDE_BLOCKS, OUT, load_pairs, read_jsonl, strip_fence

TESTS = (("concept", "placebo"), ("concept", "base"), ("callee_code", "base"), ("placebo", "base"),
         ("concept", "ide"), ("ide", "base"))
BARE = re.compile(r"\s*[A-Za-z_][\w:~]*\s*\(")  # body starts at the function name: return-type line missing
TAG = re.compile(r"@@\s*(not\s+)?vulnerable\s*@@", re.I)


def strict(raw):
    tags = TAG.findall(raw)
    return int(bool(tags) and not tags[-1])


def load(arm, gold):
    recs = {(r["pair"], r["side"]): r for r in read_jsonl(OUT / "responses" / f"{arm}.jsonl") if "error" not in r}
    pairs = {}
    for (i, s), v in recs.items():
        b = recs.get((i, "non_vulnerable"))
        if s == "vulnerable" and b:
            pairs[i] = {"v": v["pred"], "b": b["pred"], "pc": int(v["pred"] == 1 and b["pred"] == 0),
                        "pc_strict": int(strict(v["raw"]) == 1 and strict(b["raw"]) == 0),
                        "cwe": int(v["cwe_pred"] in gold[i])}  # authors' rule: prediction in the gold CWE list
    return recs, pairs


def mcnemar(x, y):
    b = sum(p and not q for p, q in zip(x, y))
    c = sum(q and not p for p, q in zip(x, y))
    n = b + c
    return b, c, min(1.0, 2 * sum(comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n) if n else 1.0


def pct(k, n):
    return f"{100 * k / n:.1f}" if n else "-"


def main():
    pairs_ = load_pairs()
    gold = [p["cwe"] for p in pairs_]
    # dataset quirk: 327 vulnerable bodies lost their return-type line while the patched body kept it (a label cue)
    cue = [bool(BARE.match(strip_fence(p["vulnerable_function_body"])))
           and not BARE.match(strip_fence(p["non_vulnerable_function_body"])) for p in pairs_]
    meta = {}
    for r in read_jsonl(BLOCKS):
        m = meta.setdefault(r["pair"], {"callee_src": True, "same_body": r["same_body"]})
        m["callee_src"] &= r["n_src_callees"] > 0
    data = {a: load(a, gold) for a in ARMS}
    lines = ["# JitVul concept harness: results", "",
             "| arm | pairs | P-C % | P-V % | P-B % | P-R % | P-C strict % | F1 | func acc % | flagged % | CWE match % | no tag % | truncated % | prompt chars | tokens in/out | cost $ |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in ARMS:
        recs, pairs = data[a]
        if not pairs:
            continue
        n, r = len(pairs), list(recs.values())
        tp, fp = sum(p["v"] for p in pairs.values()), sum(p["b"] for p in pairs.values())
        cnt = lambda f: sum(f(p) for p in pairs.values())
        lines.append("| " + " | ".join(map(str, [
            a, n, pct(cnt(lambda p: p["pc"]), n), pct(cnt(lambda p: p["v"] and p["b"]), n),
            pct(cnt(lambda p: not p["v"] and not p["b"]), n), pct(cnt(lambda p: not p["v"] and p["b"]), n),
            pct(cnt(lambda p: p["pc_strict"]), n), f"{2 * tp / (2 * tp + fp + n - tp):.3f}" if tp else "0",
            pct(tp + n - fp, 2 * n), pct(tp + fp, 2 * n), pct(cnt(lambda p: p["cwe"]), n),
            pct(sum(not TAG.search(x["raw"]) for x in r), len(r)), pct(sum(x["finish"] == "MAX_TOKENS" for x in r), len(r)),
            round(sum(x["prompt_chars"] for x in r) / len(r)),
            f"{sum(x['tok_in'] for x in r)}/{sum(x['tok_out'] + x['tok_thought'] for x in r)}", f"{sum(x['cost'] for x in r):.3f}"])) + " |")
    lines += ["", "P-C = vulnerable flagged and patched not flagged; P-V = both flagged (always-vulnerable degenerate); "
              "P-B = neither flagged; P-R = both wrong. flagged = share of all functions labelled vulnerable.", "",
              "## Exact McNemar on P-C (pairs answered in both arms)", "",
              "| A vs B | subset | pairs | P-C A % | P-C B % | A only | B only | p (two-sided) |", "|---|---|---|---|---|---|---|---|"]
    subsets = {"all": lambda i: True, "callee source on both sides": lambda i: meta[i]["callee_src"],
               "identical target bodies": lambda i: meta[i]["same_body"],
               "no return-type cue": lambda i: not cue[i]}
    for x, y in TESTS:
        px, py = data[x][1], data[y][1]
        for name, keep in subsets.items():
            ids = sorted(i for i in px.keys() & py.keys() if keep(i))
            if not ids:
                continue
            xs, ys = [px[i]["pc"] for i in ids], [py[i]["pc"] for i in ids]
            b, c, p = mcnemar(xs, ys)
            lines.append(f"| {x} vs {y} | {name} | {len(ids)} | {pct(sum(xs), len(ids))} | {pct(sum(ys), len(ids))} | {b} | {c} | {p:.4g} |")
    if data["base"][1]:
        b = data["base"][1]
        k0 = [b[i]["pc"] for i in b if not cue[i]]
        k1 = [b[i]["pc"] for i in b if cue[i]]
        lines += ["", f"base P-C by return-type cue: no cue {sum(k0)}/{len(k0)} ({pct(sum(k0), len(k0))}%), "
                      f"cue (vulnerable body lacks the return-type line) {sum(k1)}/{len(k1)} ({pct(sum(k1), len(k1))}%)."]
    ide = read_jsonl(IDE_BLOCKS)
    if ide:
        e = sum(r["n_warnings"] == 0 for r in ide)
        ep = sum(all(r["n_warnings"] == 0 for r in ide if r["pair"] == i) for i in {r["pair"] for r in ide})
        lines += ["", f"ide block empty (no analyzer warning on target or listed callees): {e}/{len(ide)} functions "
                      f"({pct(e, len(ide))}%), {ep}/{len(ide) // 2} pairs empty on both sides."]
    text = "\n".join(lines) + "\n"
    (OUT / "summary.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
