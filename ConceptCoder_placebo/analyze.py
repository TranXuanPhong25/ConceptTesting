#!/usr/bin/env python3
"""F1 table, paired tests (exact McNemar + paired-bootstrap dF1) and concept probing for the placebo study.

  python analyze.py out            # out/<arm>[_s<seed>]/{metrics.json,preds_test.jsonl,preds_robust.jsonl}
  python analyze.py --selftest
"""
import sys, json, glob, os
from math import comb
import numpy as np

# pre-registered comparisons (README.md); first = primary
PAIRS = [("conceptcoder", "placebo"), ("placebo", "regular"), ("conceptcoder", "regular"),
         ("regular", "regular_paperhead"), ("conceptcoder", "regular_paperhead")]


def mcnemar(a_ok, b_ok):
    """exact two-sided McNemar on paired correctness -> (b, c, p)."""
    b = int(np.sum(a_ok & ~b_ok)); c = int(np.sum(~a_ok & b_ok)); n = b + c
    p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
    return b, c, p


def f1(y, p):
    tp = (y & p).sum(-1); fp = (~y & p).sum(-1); fn = (y & ~p).sum(-1)
    return 100 * 2 * tp / np.maximum(1, 2 * tp + fp + fn)


def boot_df1(y, pa, pb, n=2000, seed=0):
    idx = np.random.default_rng(seed).integers(0, len(y), (n, len(y)))
    d = f1(y[idx], pa[idx]) - f1(y[idx], pb[idx])
    return f1(y, pa) - f1(y, pb), np.percentile(d, 2.5), np.percentile(d, 97.5)


def load_preds(path):
    r = [json.loads(l) for l in open(path)]
    return [x["idx"] for x in r], np.array([x["label"] for x in r], bool), np.array([x["pred"] for x in r], bool)


def main(root):
    runs = {os.path.basename(os.path.dirname(m)): json.load(open(m)) for m in sorted(glob.glob(os.path.join(root, "*", "metrics.json")))}
    if not runs:
        sys.exit("no */metrics.json under %s" % root)
    any_run = next(iter(runs))
    _, y, _ = load_preds(os.path.join(root, any_run, "preds_test.jsonl"))
    pos = y.mean()
    print("## VD test split: n=%d, vulnerable=%.2f%%; predict-all-vulnerable F1=%.2f, acc=%.2f\n"
          % (len(y), 100 * pos, 100 * 2 * pos / (1 + pos), 100 * pos))
    print("| run | train min | test F1 | acc | prec | rec | pred+ % | robust F1 | head macroF1 test (true) | head fit train true | head fit train placebo | linear probe macroF1 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    g = lambda r, *k: (lambda v: "%.2f" % v if isinstance(v, (int, float)) else "–")(_dig(r, k))
    for name, r in runs.items():
        print("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name, r.get("train_min"), g(r, "test", "f1"), g(r, "test", "acc"), g(r, "test", "prec"), g(r, "test", "rec"),
            g(r, "test", "pred_pos_rate"), g(r, "robust", "f1"), g(r, "concept_head_test", "macro_f1"),
            g(r, "fit_train_true_labels", "macro_f1"), g(r, "fit_train_placebo_labels", "macro_f1"), g(r, "linear_probe", "macro_f1")))
    print("\n## Paired comparisons (A vs B): exact McNemar on correctness, paired-bootstrap 95% CI of F1(A)-F1(B)\n")
    print("| split | A | B | b (A right, B wrong) | c | McNemar p | dF1 | 95% CI |")
    print("|---|---|---|---|---|---|---|---|")
    split_name = lambda s: (s.rsplit("_s", 1) + [""])[:2] if s.rsplit("_s", 1)[-1].isdigit() else [s, ""]
    for split in ("test", "robust"):
        for ra in runs:
            for rb in runs:
                (a, sa), (b_, sb) = split_name(ra), split_name(rb)       # run dir = <arm> or <arm>_s<seed>
                if (a, b_) not in PAIRS or sa != sb:
                    continue
                pa_, pb_ = (os.path.join(root, r, "preds_%s.jsonl" % split) for r in (ra, rb))
                if not (os.path.exists(pa_) and os.path.exists(pb_)):
                    continue
                ia, ya, pa = load_preds(pa_); ib, yb, pb = load_preds(pb_)
                assert ia == ib and (ya == yb).all(), "unpaired predictions"
                b, c, p = mcnemar(pa == ya, pb == yb)
                d, lo, hi = boot_df1(ya, pa, pb)
                print("| %s | %s | %s | %d | %d | %.4g | %+.2f | [%+.2f, %+.2f] |" % (split, ra, rb, b, c, p, d, lo, hi))
    print("\n## Threshold-free (p(vul) ranking): AUROC / average precision\n")
    from sklearn.metrics import roc_auc_score, average_precision_score
    for name in runs:
        out = []
        for split in ("test", "robust"):
            r = [json.loads(l) for l in open(os.path.join(root, name, "preds_%s.jsonl" % split))]
            yy = [x["label"] for x in r]; pp = [x["p1"] for x in r]
            out.append("%s AUROC %.3f AP %.3f" % (split, roc_auc_score(yy, pp), average_precision_score(yy, pp)))
        print("- %s: %s" % (name, " | ".join(out)))
    print("\n## Concept head per-concept F1 (test, true labels) / predicted vs true positive rate\n")
    for name, r in runs.items():
        h = r.get("concept_head_test")
        if h:
            print("- %s: F1 %s | pred+ %s | true+ %s" % (name, h["per_concept_f1"], h["pred_pos_rate"], h["true_pos_rate"]))


def _dig(d, ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def selftest():
    assert mcnemar(np.array([1] * 5 + [0] * 0, bool), np.array([0] * 5, bool)) == (5, 0, 0.0625)
    assert mcnemar(np.ones(4, bool), np.ones(4, bool))[2] == 1.0
    y = np.array([1, 1, 0, 0, 1, 0, 0, 0], bool); pa = np.array([1, 1, 0, 1, 0, 0, 0, 0], bool)
    assert abs(f1(y, pa) - 100 * 2 * 2 / (2 * 2 + 1 + 1)) < 1e-9
    d, lo, hi = boot_df1(np.tile(y, 50), np.tile(pa, 50), np.tile(y, 50))
    assert d < 0 and lo <= d <= hi
    print("selftest ok")


if __name__ == "__main__":
    selftest() if sys.argv[1:] == ["--selftest"] else main(sys.argv[1] if len(sys.argv) > 1 else "out")
