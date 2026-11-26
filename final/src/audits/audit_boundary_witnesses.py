"""Post-run boundary feasibility audit, separate from the frozen LLM comparison.

Uses public task specs/contracts, saved PUTs and hand-specified boundary corpora.
Never imports hidden tests or calls a model. Bulk screening is sandboxed; claimed
witnesses are replayed individually twice through the shared execution cache.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import itertools
import json
import math
from pathlib import Path

from final.src.runtime.execution import execute
from final.src.runtime.artifacts import digest

ROOT = Path(__file__).resolve().parents[3]
REFERENCES = ROOT / "final/data/humanevalplus_v0.1.10_references.json"
FROZEN_RUN = ROOT / "final/out/boundary_all_plain_bva_compiled_20261105"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def adjacent(x):
    if isinstance(x, float):
        return [math.nextafter(x, -math.inf), x, math.nextafter(x, math.inf)]
    return [x - 1, x, x + 1]


def words(alphabet, maximum):
    return ["".join(items) for n in range(maximum + 1)
            for items in itertools.product(alphabet, repeat=n)]


def small_lists(alphabet, minimum=0, maximum=4):
    return [list(items) for n in range(minimum, maximum + 1)
            for items in itertools.product(alphabet, repeat=n)]


def candidates(number):
    records = []
    seen = set()

    def add(args, boundary):
        record = {"args": repr(tuple(args)), "kwargs": "{}", "boundary": boundary}
        key = record["args"]
        if key not in seen:
            if len(key) > 16000:
                raise ValueError(f"Audit literal too large: {number}")
            seen.add(key)
            records.append(record)

    if number == 0:
        for xs in [[], [0.0], [0.0, 0.0], [0.0, 1.0], [-1.0, 1.0],
                   [0.0, 1.0, 2.0], [1e16, 1e16 + 2.0], [1.0, 1.0, 3.0]]:
            for t in [5e-324, *adjacent(0.5), *adjacent(1.0), *adjacent(2.0)]:
                add((xs, t), "length 0/1/2; adjacent gap versus threshold")
    elif number == 2:
        for t in [5e-324, 1e-300, *[x for n in [1., 2., 10., 2.**52, 2.**53] for x in adjacent(n)]]:
            add((t,), "positive domain edge; float neighbors of integer transitions")
    elif number == 5:
        for xs in small_lists([-1, 0, 1], maximum=3) + [list(range(10))]:
            for d in [-1, 0, 1]: add((xs, d), "length 0/1/2 and insertion positions")
    elif number in (10, 14, 23, 38, 80, 140):
        alphabet = "abc" if number == 80 else "a " if number == 140 else "ab"
        maximum = 8 if number == 140 else 6
        for text in words(alphabet, maximum) + ["", "é", "a\tb", "a\nb", "😀a😀", "abcdefghij"]:
            add((text,), "empty/singleton; length 2/3/4; suffix/group/window/run transitions")
        if number == 140:
            for n in range(8):
                for left, right in [("", ""), ("a", ""), ("", "b"), ("a", "b")]:
                    add((left + " " * n + right,), "maximum consecutive space run 2/3 and string ends")
    elif number in (15, 36, 41, 60, 79, 96, 107, 138, 156):
        if number in (107, 156): values = range(1, 1001)
        elif number == 96: values = range(201)
        elif number == 36: values = list(range(1, 161)) + [999, 1000, 1001]
        elif number == 138: values = list(range(-20, 41)) + [10**20 - 1, 10**20, 10**20 + 1]
        elif number == 79: values = list(range(101)) + [x for k in range(1, 31) for x in adjacent(2**k)]
        elif number in (41, 60): values = list(range(1, 101)) + [10**12 - 1, 10**12, 10**12 + 1]
        else: values = list(range(31)) + [99, 100, 101, 999, 1000]
        for n in values: add((n,), "public domain endpoints; integer/parity/digit/loop transitions")
    elif number == 18:
        for text in words("ab", 5):
            for sub in words("ab", 3)[1:]:
                add((text, sub), "nonempty substring; len(text)-len(sub) -1/0/1; overlap")
    elif number in (20, 21, 47):
        minimum = 1 if number == 47 else 2
        for xs in small_lists([-1, 0, 1], minimum, 5 if number != 21 else 4):
            if number == 21 and min(xs) == max(xs): continue
            add((xs,), "minimum valid length; equal/tied extrema and odd/even lengths")
        for xs in [[0., math.nextafter(1., 0.), 1.], [0., 1e-300], [-1e200, 0., 1e200]]:
            add((xs,), "float gap/range near zero and large finite scale")
    elif number == 30:
        for xs in small_lists([-1, 0, 1]): add((xs,), "element sign around zero; length 0/1")
    elif number == 44:
        for base in range(2, 10):
            for n in list(range(101)) + [x for k in range(1, 7) for x in adjacent(base**k)]:
                add((n, base), "base domain 2..9; representation lengths at base**k")
    elif number == 45:
        for a, h in itertools.product([5e-324, 1e-100, 0.5, 1, 2, 10, 1e100], repeat=2):
            add((a, h), "strictly positive domain; finite numeric extremes")
    elif number == 52:
        for xs in small_lists([-1, 0, 1], maximum=3) + [[False, True]]:
            for t in [-1, 0, 1, 2]: add((xs, t), "each element versus t-1/t/t+1; empty list")
    elif number == 69:
        for xs in small_lists([1, 2, 3], maximum=5): add((xs,), "frequency versus integer value")
        for k in range(1, 10):
            for count in adjacent(k): add(([k] * count,), "count(value) == value +/- 1")
    elif number == 71:
        for a, b, c in itertools.product([1, 2, 3, 4], repeat=3):
            add((a, b, c), "triangle inequality equality and adjacent integers")
        for a, b in itertools.product([0.5, 1., 2., 10.], repeat=2):
            for c in adjacent(a + b): add((a, b, c), "float neighbors of a+b == c")
    elif number == 72:
        for xs in small_lists([-1, 0, 1]):
            for w in adjacent(sum(xs)): add((xs, w), "sum(q) == w +/- 1; palindrome endpoints")
    elif number == 74:
        lists = small_lists(["", "a", "ab"], maximum=3)
        for a, b in itertools.product(lists, repeat=2):
            add((a, b), "total character lengths below/equal/above; empty lists/strings")
    elif number == 77:
        for n in list(range(-100, 101)) + [s*x for k in [10, 100, 10**6] for x in adjacent(k**3) for s in [-1, 1]]:
            add((n,), "signed cube transitions at k**3 +/- 1")
    elif number == 81:
        for threshold in [0., .7, 1., 1.3, 1.7, 2., 2.3, 2.7, 3., 3.3, 3.7, 4.]:
            for x in adjacent(threshold):
                if 0 <= x <= 4: add(([x],), "immediate float neighbors of each grade threshold")
        add(([],), "empty grade list")
    elif number == 83:
        for n in list(range(1, 31)) + list(range(970, 1021)):
            add((n,), "n=1/2/3; implementation recursion depth transition near n=1000")
    elif number == 97:
        for a, b in itertools.product(range(-20, 21), repeat=2):
            add((a, b), "sign/zero and units-digit transitions at multiples of ten")
    elif number == 99:
        for n in range(-11, 12):
            for x in [*adjacent(float(n)), *adjacent(n + .5)]:
                add((repr(x),), "parsed numeric string: integer/sign and half-integer float neighbors")
        for text in ["-0.1", "-0.9", "-1e-10", "-14.5", "-14.49", "-14.51"]:
            add((text,), "negative rounding around half-integer boundary")
    elif number == 103:
        for n, m in itertools.product(range(1, 31), repeat=2):
            add((n, m), "n versus m; integer versus half-integer mean")
        for n in [2**53 - 1, 2**53, 2**53 + 1, 10**100]:
            for delta in [-1, 0, 1, 2, 3]: add((n, n + delta), "large exact integers near float precision transition")
    elif number == 115:
        for capacity in range(1, 11):
            for width in sorted(set([1, 2, 99, 100, capacity, capacity + 1])):
                for water in sorted(set([0, 1, max(0, capacity - 1), capacity, capacity + 1, width])):
                    if water <= width:
                        row = [1] * water + [0] * (width - water)
                        add(([row], capacity), "row water versus capacity; row length domain 1..100")
        for height in [1, 2, 99, 100]:
            for c in [1, 2, 9, 10]: add(([[1] for _ in range(height)], c), "grid height domain 1..100 and capacity endpoints")
    elif number == 120:
        for size in [1, 2, 3, 999, 1000]:
            xs = ([-1000, 0, 1000] * ((size + 2) // 3))[:size]
            for k in sorted(set([0, 1, size - 1, size])):
                add((xs, k), "array length endpoints; k=0/1/len-1/len; element extrema")
    elif number == 122:
        for x in [-101, -100, -99, -10, -9, -1, 0, 9, 10, 99, 100, 101]:
            for size in [1, 2, 99, 100]:
                for k in sorted(set([1, size])):
                    add(([x] * size, k), "two-digit magnitude +/-99/100; prefix and length endpoints")
    elif number == 124:
        for m in [0, 1, 2, 4, 12, 13]:
            for d in [0, 1, 28, 29, 30, 31, 32]:
                for y in ["", "0", "200", "2000", "20000"]:
                    add((f"{m:02d}-{d:02d}-{y}",), "parsed month/day endpoints; year width 3/4/5; total length 9/10/11")
        for text in ["", "01-01-2000 ", " 01-01-2000", "01-01-+200", "01-01-2_00", "01/01/2000", "1-01-2000"]:
            add((text,), "fixed date format width, character and separator boundaries")
    elif number == 133:
        for n in range(-4, 5):
            for x in adjacent(float(n)):
                for xs in [[], [x], [x, x]]: add((xs,), "ceil discontinuity immediately around signed integers")
    elif number == 146:
        for x in list(range(-12, 24)) + [99, 100, 101, 109, 110, 111, 999, 1000, 1001]:
            for xs in [[x], [x, x], [0, x, 10]]: add((xs,), "value >10; first/last odd digit and digit length transitions")
    elif number == 157:
        for a, b, c in itertools.product(range(1, 11), repeat=3):
            add((a, b, c), "positive side domain; Pythagorean equality")
        for a, b, c in itertools.permutations([3., 4., 5.]):
            for z in adjacent(c): add((a, b, z), "float neighbors of right-triangle equality across permutations")
    elif number == 159:
        for a, b, c in itertools.product([0, 1, 2, 500, 999, 1000], repeat=3):
            add((a, b, c), "all public domain endpoints; need versus remaining equality")
    else:
        raise ValueError(f"Missing task-specific boundary corpus: {number}")
    return records


def audit_task(task, ref, records, output):
    number = int(task["task_id"].split("/")[1])
    directory = output / "tasks" / str(number)
    directory.mkdir(parents=True, exist_ok=True)
    base_job = {"context": ref["prompt"], "source": ref["prompt"] + ref["canonical_solution"],
                "entry": ref["entry_point"], "timeout": 3, "seed": 271828 + number}
    oracle_job = {**base_job, "mode": "oracle", "contract": ref["contract"], "tests": records}
    oracle_path = directory / "screen_oracle.json"
    if oracle_path.exists(): oracle = json.loads(oracle_path.read_text())
    else:
        oracle = execute(oracle_job)
        write(oracle_path, oracle)
    valid = []
    candidate_indices = []
    base_keys = set(task["base_input_keys"])
    for index, (record, outcome) in enumerate(zip(records, oracle["tests"])):
        if outcome["status"] == "ok" and outcome["input_key"] not in base_keys:
            valid.append({**record, "expected": outcome["expected"]})
            candidate_indices.append(index)
    put = task["programs"][0]
    evaluation_job = {**base_job, "mode": "evaluate", "source": put["code"],
                      "atol": ref["atol"], "tests": valid}
    evaluation_path = directory / "screen_put.json"
    if evaluation_path.exists(): evaluated = json.loads(evaluation_path.read_text())
    else:
        evaluated = execute(evaluation_job) if valid else {"tests": []}
        write(evaluation_path, evaluated)
    witnesses = []
    failed = [(position, outcome) for position, outcome in enumerate(evaluated["tests"])
              if outcome["status"] in ("fail", "error", "timeout")]
    # Replay up to three representatives/statuses, fixed before execution.
    representatives = []
    for status in ["fail", "error", "timeout"]:
        match = next((position for position, outcome in failed if outcome["status"] == status), None)
        if match is not None: representatives.append(match)
    for position in representatives:
        record = valid[position]
        repeats = []
        for _ in range(2):
            reference_result = execute({**oracle_job, 'tests': [record]})
            put_result = execute({**evaluation_job, 'tests': [record]})
            repeats.append({"oracle": reference_result["tests"][0], "put": put_result["tests"][0]})
        stable = (all(x["oracle"]["status"] == "ok" and x["oracle"]["expected"] == record["expected"]
                      and x["put"]["status"] in ("fail", "error", "timeout") for x in repeats)
                  and repeats[0]["put"]["status"] == repeats[1]["put"]["status"])
        witnesses.append({"candidate_index": candidate_indices[position], "input": record,
                          "confirmed_in_two_isolated_runs": stable, "repeats": repeats})
    result = {"task_id": task["task_id"], "entry": ref["entry_point"], "program_id": put["id"],
              "candidate_count": len(records), "valid_novel_count": len(valid),
              "screen_failures": len(failed), "witnesses": witnesses,
              "oracle_statuses": {s: sum(x["status"] == s for x in oracle["tests"])
                                  for s in sorted({x["status"] for x in oracle["tests"]})},
              "status": "witness_found" if any(x["confirmed_in_two_isolated_runs"] for x in witnesses)
                        else "no_witness_in_bounded_search",
              "exhaustive_public_domain": number in (107, 156),
              "put_sha256": hashlib.sha256(put["code"].encode()).hexdigest()}
    write(directory / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    out = options.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cohort = json.loads(options.cohort.read_text())
    refs = json.loads(REFERENCES.read_text())["tasks"]
    corpora = {t["task_id"]: candidates(int(t["task_id"].split("/")[1])) for t in cohort["tasks"]}
    plan = {"schema": "posthoc-boundary-feasibility-1", "cohort_sha256": cohort["cohort_sha256"],
            "reference_sha256": hashlib.sha256(REFERENCES.read_bytes()).hexdigest(),
            "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "corpora": corpora, "corpora_sha256": digest(corpora), "llm_calls": 0,
            "policy": "public specs, contracts and PUT source; no hidden inputs; sandbox bulk screen; "
                      "up to three status representatives replayed twice in isolated cache slots; "
                      "no witness does not prove absence; resource failure is reported separately"}
    plan_path = out / "plan.json"
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError("Audit plan changed; preserve existing output")
    write(plan_path, plan)
    artifact_path = out / "frozen_run_artifacts.json"
    before = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
              for f in FROZEN_RUN.rglob("*") if f.is_file()}
    if artifact_path.exists() and json.loads(artifact_path.read_text()) != before:
        raise ValueError("Original frozen run changed")
    write(artifact_path, before)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(audit_task, t, refs[t["task_id"]], corpora[t["task_id"]], out): t["task_id"]
                for t in cohort["tasks"]}
        for job in concurrent.futures.as_completed(jobs):
            result = job.result()
            results.append(result)
            print(result["task_id"], result["status"], result["valid_novel_count"], flush=True)
    results.sort(key=lambda x: int(x["task_id"].split("/")[1]))
    changed = [name for name, sha in before.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha]
    summary = {"tasks": results, "task_count": len(results),
               "candidate_count": sum(x["candidate_count"] for x in results),
               "valid_novel_count": sum(x["valid_novel_count"] for x in results),
               "witness_tasks": [x["task_id"] for x in results if x["status"] == "witness_found"],
               "original_artifact_count": len(before), "original_artifacts_changed": changed,
               "llm_calls": 0, "corpora_sha256": plan["corpora_sha256"]}
    write(out / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "tasks"}), flush=True)


if __name__ == "__main__":
    main()
