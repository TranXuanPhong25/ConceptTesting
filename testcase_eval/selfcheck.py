#!/usr/bin/env python3
"""Sandbox self-check: every accepted submission must reproduce the sample output.

Runs each `right_submission` in `submission_lite` on the problem's first
official example and compares with the example output using the official
checker.  This validates the C++/Java/Python toolchains before any LLM run
and warms the compile cache.  Prints per-language pass rates.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from testcase_eval.data import load_rows
from testcase_eval.metrics import validate_outputs
from testcase_eval.sandbox import Executor, language_family


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--type", default="right_submission", choices=("right_submission", "wrong_submission"))
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    problems = {p["problem_id"]: p for p in load_rows("problem")}
    subs = [s for s in load_rows("submission_lite") if s["type"] == args.type]
    executor = Executor()

    def check(sub: dict) -> dict:
        examples = problems[sub["problem_id"]]["examples"]
        if not examples or language_family(sub["language"]) is None:
            return {"id": sub["id"], "language": sub["language"], "status": "skipped"}
        sample_in, sample_out = examples[0]
        run = executor.execute(sub["language"], sub["source"], sample_in)
        if run["result"] != "success_run":
            status = run["result"]
        else:
            status = "match" if validate_outputs(run["output"], sample_out) else "mismatch"
        return {"id": sub["id"], "problem_id": sub["problem_id"], "language": sub["language"], "status": status,
                "time": run.get("time"), "error": run.get("error", "")[:300]}

    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(check, subs))
    by_lang = Counter((r["language"], r["status"]) for r in results)
    summary = {}
    for (lang, status), n in sorted(by_lang.items()):
        summary.setdefault(lang, {})[status] = n
    print(json.dumps(summary, indent=2))
    if args.out:
        with open(args.out, "w") as handle:
            for r in results:
                handle.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
