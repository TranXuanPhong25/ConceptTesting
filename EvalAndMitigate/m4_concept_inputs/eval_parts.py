"""Evaluate an arm, resuming after crashes (host python). Copy of m3_concept_spec/eval_parts.py, paths moved to m4_concept_inputs.

The upstream evaluation keeps no state between runs and crashes now and then on transient Docker filesystem errors
(ENOENT on a checkout directory that exists). A crash restarts all 78 methods from scratch. Here, after a crash,
the methods whose log block finished are kept and the rest go into a new part (FILE_POST_FIX <arm>_part<k>).
The plan is saved to out/<arm>_parts.json, and m4_concept_inputs/analyze.py merges the part logs in that order.

A block whose fixed or buggy run "failed" with an empty error report is an infrastructure failure (the upstream
counters then turn passing tests into M). `--redo i j ...` re-evaluates those record indexes once in a
<arm>_redo<k> part; analyze.py uses the redo block in place of the original.

usage: python3 m4_concept_inputs/eval_parts.py <arm FILE_POST_FIX> [--redo i j ...]
"""
import glob, json, os, re, subprocess, sys

RQ1 = "data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_{}_with_completion.jsonl"
LOGS = "data/rq1/logs/Gemini-2-5-flash_gen_test_evaluate_buggy_gen_test_non_private_or_default_{}_log_*.log"


def latest_log(fpf):
    logs = glob.glob(LOGS.format(fpf))
    return max(logs, key=lambda p: int(re.search(r"_log_(\d+)\.log$", p).group(1))) if logs else None


def block_sigs(log):
    return [b.split("method signature: ")[1].split("\n")[0].strip() for b in open(log).read().split("INFO - Processing Project:")[1:]]


def run(fpf):
    with open(f"m4_concept_inputs/out/eval_{fpf}.console", "w") as con:
        return subprocess.run(["bash", "run/dock.sh", "eval_env"], env={**os.environ, "FILE_POST_FIX": fpf},
                              stdout=con, stderr=subprocess.STDOUT).returncode == 0


def main(arm, redo):
    records = [json.loads(l) for l in open(RQ1.format(arm))]
    plan_path = f"m4_concept_inputs/out/{arm}_parts.json"
    parts = json.load(open(plan_path)) if os.path.exists(plan_path) else []
    if redo:
        fpf = f"{arm}_redo{sum('idx' in p for p in parts) + 1}"
        with open(RQ1.format(fpf), "w") as f:
            f.writelines(json.dumps(records[i]) + "\n" for i in redo)
        ok = run(fpf)
        sigs = block_sigs(latest_log(fpf))
        assert ok and sigs == [records[i]["method_signature"] for i in redo], "redo run crashed; rerun it"
        parts.append({"fpf": fpf, "idx": redo, "n": len(redo)})
        json.dump(parts, open(plan_path, "w"), indent=1)
        return print(parts[-1])
    done = sum(p["n"] for p in parts if "idx" not in p)
    while done < len(records):
        fpf = arm if not parts else f"{arm}_part{len(parts) + 1}"
        assert latest_log(fpf) is None, f"{fpf} already has a log; move it away first"
        if fpf != arm:
            with open(RQ1.format(fpf), "w") as f:
                f.writelines(json.dumps(r) + "\n" for r in records[done:])
        ok = run(fpf)
        sigs = block_sigs(latest_log(fpf))
        # the block the crash hit is incomplete, unless its counters were all written: the upstream per-item log line
        # divides by the cumulative compiled-test count and crashes right after a finished block when that is still 0
        last_done = "Total test generated:" in open(latest_log(fpf)).read().split("INFO - Processing Project:")[-1]
        n = len(sigs) if ok or last_done else len(sigs) - 1
        assert sigs[:n] == [r["method_signature"] for r in records[done:done + n]], "log order does not match records"
        parts.append({"fpf": fpf, "start": done, "n": n, "crashed": not ok})
        json.dump(parts, open(plan_path, "w"), indent=1)
        print(parts[-1], flush=True)
        if n <= 0 and len(parts) > 1 and parts[-2]["n"] <= 0:
            sys.exit("two parts in a row made no progress")
        done += n


if __name__ == "__main__":
    main(sys.argv[1], [int(i) for i in sys.argv[3:]] if sys.argv[2:3] == ["--redo"] else [])
