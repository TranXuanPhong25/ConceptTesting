"""Reporting-only heldout/real-bug cohorts; labels never enter generation."""
import collections
import contextlib
import io
import json
from pathlib import Path
import tempfile


def cohorts(paths):
    labels = json.loads((paths.root / "labels_manual.json").read_text())
    ids = set(paths.ids())
    if ids - set(map(int, labels)):
        raise ValueError("manual reporting labels missing selected tasks")
    return [("heldout", ids), ("real-bug", {n for n in ids if labels[str(n)].startswith("real-bug:")})]


def evaluation_report(paths):
    """Reuse every v4 report metric and comparison on reporting-only copies.

    v4's report recognizes dev/pilot only. Temporary copies map each cohort to
    dev for that report, then relabel its output; real bundles/rows stay heldout.
    """
    from trickcatcher_linefacts import v4_evaluation as ev
    bundle = json.loads((paths.generation / "tasks.json").read_text())
    rows = [json.loads(l) for l in (paths.generation / "eval.jsonl").read_text().splitlines()]
    metrics, text = {}, []
    for label, ids in cohorts(paths):
        if not ids: continue
        with tempfile.TemporaryDirectory(prefix="heldout_report_", dir=paths.generation) as scratch:
            tp, ep = Path(scratch) / "tasks.json", Path(scratch) / "eval.jsonl"
            tp.write_text(json.dumps(dict(bundle, tasks=[dict(t, split="dev") for t in bundle["tasks"] if t["task"] in ids])))
            ep.write_text("".join(json.dumps(r) + "\n" for r in rows if r["task"] in ids))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                result = ev.report(tp, ep)
            metrics.update({k.replace("dev/", label + "/", 1): v for k, v in result.items()})
            text.append(buf.getvalue().replace("dev /", label + " /"))
    (paths.generation / "eval.metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    report = "\n".join(text)
    (paths.generation / "report.txt").write_text(report)
    print(report)
    return metrics


def oracle_report(paths, ex, jd):
    """oracle_b01.score's assertion counting/decisions, ref/full only.

    Same per-sample deduplication, contract-invalid false alarms, any-of-K and
    paired per-task sign test; cohort selection is reporting-only.
    """
    from trickcatcher_linefacts import oracle_b01 as ob
    tasks, rows = ob.load_run(paths.generation)
    oracles = ("ref", "full")
    stats = {}
    for r in rows:
        t, entry = str(r["task"]), tasks[r["task"]]["entry"]
        seen = set()
        result = {o: dict(emit=0, fa=0, inv=0, det=False, flag=False) for o in oracles}
        for a in r["asserts"]:
            c = ob.call_of(a["src"], entry)
            if c is None or c in seen: continue
            seen.add(c)
            rec = ex[t]["calls"].get(c, {})
            valid = rec.get("valid", True)
            for o in oracles:
                emit, cok, pok = ob.decide(o, rec, jd.get((t, c)), ob.expected_of(a["src"]), a)
                if emit:
                    bad = not cok or not valid
                    s = result[o]
                    s["emit"] += 1; s["fa"] += bad; s["inv"] += not valid
                    s["det"] |= cok and not pok and valid
                    s["flag"] |= bad
        stats[r["task"], r["arm"], r["sample"]] = result
    report = ["MBPP+ held-out oracle report: ref/full. dpp/tc unavailable; skipped."]
    output = {}
    for label, ids in cohorts(paths):
        if not ids: continue
        keys = [k for k in stats if k[0] in ids]
        k = 3
        arms = sorted({key[1] for key in keys})
        report.append(f"\n{label}: {len(ids)} tasks, K={k}; detection/sample, any-of-K, FA/assertion, assertions/sample, flags/sample")
        metrics = {}
        for arm in arms:
            metrics[arm] = {}
            for o in oracles:
                ss = [stats[key][o] for key in keys if key[1] == arm]
                em = sum(s["emit"] for s in ss); fa = sum(s["fa"] for s in ss)
                m = dict(detect_sample=sum(s["det"] for s in ss) / k,
                         any_of_k=sum(any(stats[t, arm, sample][o]["det"] for sample in range(k)) for t in ids),
                         false_alarm=fa / max(1, em), assertions_per_sample=em / len(ss),
                         flagged_samples=sum(s["flag"] for s in ss) / len(ss),
                         contract_invalid=sum(s["inv"] for s in ss), emitted=em)
                metrics[arm][o] = m
                report.append(f"{arm:16s} {o:4s} {m['detect_sample']:.2f} {m['any_of_k']} "
                              f"{m['false_alarm']:.3f} {m['assertions_per_sample']:.2f} {m['flagged_samples']:.3f}")
        comparisons = []
        for a, b in (("concept-hybrid", "plain-hybrid"), ("concept", "plain"),
                     ("concept-hybrid", "toolinput"), ("concept-hybrid", "placebo-hybrid")):
            for o in oracles:
                wins = losses = 0
                for t in ids:
                    x = sum(stats[t, a, s][o]["det"] for s in range(k))
                    y = sum(stats[t, b, s][o]["det"] for s in range(k))
                    wins += x > y; losses += x < y
                c = dict(first=a, second=b, oracle=o, wins=wins, losses=losses, sign_p=ob.sign_p(wins, losses))
                comparisons.append(c)
                report.append(f"{a} vs {b} / {o}: {wins}/{losses}, sign p={c['sign_p']:.6g}")
        output[label] = dict(tasks=sorted(ids), k=k, arms=metrics, comparisons=comparisons)
    counters = collections.Counter()
    for v in ex.values():
        counters["ref_variants"] += v["n_variants"]["ref"]
        counters["ref_survivors"] += v["n_survivors"]["ref"]
        for name in ("n_post", "n_post_kept", "n_pairs"): counters[name] += v[name]
        for rec in v["calls"].values():
            if not rec.get("ref", {}).get("emit"):
                counters["ref_abstain_" + rec.get("ref", {}).get("why", "missing")] += 1
            counters["judge_cands"] += "judge_cands" in rec
    output["diagnostics"] = dict(counters)
    output["judge"] = dict(asked=len(jd), picks=dict(collections.Counter(r.get("pick") for r in jd.values())),
                           correct=sum(bool(r.get("pick")) and ex[t]["calls"][c]["judge_cands"][r["pick"]]["canon_ok"]
                                       for (t, c), r in jd.items()))
    report.append("\n" + json.dumps(dict(diagnostics=output["diagnostics"], judge=output["judge"])))
    text = "\n".join(report) + "\n"
    (paths.oracle / "report.txt").write_text(text)
    (paths.oracle / "metrics.json").write_text(json.dumps(output, indent=2) + "\n")
    print(text)
    return output
