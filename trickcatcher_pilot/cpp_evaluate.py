"""Differentially score generated TrickyBugs C++ inputs against references."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
from pathlib import Path
from typing import Any


def _compile(source: Path, binary: Path) -> str:
    try:
        result = subprocess.run(
            ["g++", "-std=gnu++17", "-O2", "-w", "-include", "cassert", str(source), "-o", str(binary)],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except subprocess.TimeoutExpired:
        return "compile timeout"
    return "" if result.returncode == 0 else result.stderr[-400:]


def _limit_child() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))


def _run(binary: Path, stdin: str) -> dict[str, Any]:
    if len(stdin.encode()) > 20_000:
        return {"status": "input_too_large"}
    try:
        result = subprocess.run(
            [str(binary)], input=stdin, capture_output=True, text=True,
            timeout=3, check=False, preexec_fn=_limit_child,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    return {
        "status": "pass" if result.returncode == 0 else "runtime_error",
        "returncode": result.returncode,
        "output": " ".join(result.stdout.split())[:20_000],
        "stderr": result.stderr[-300:],
    }


def evaluate(pred: Path, problems: Path, puts: Path, out: Path, bin_cache: Path) -> dict[str, int]:
    summary = {"tasks": 0, "evaluable_tasks": 0, "exposed_tasks": 0, "reference_agreed_inputs": 0, "exposing_inputs": 0}
    latest = {}
    for line in pred.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            latest[row["problem_id"]] = row
    rows = list(latest.values())
    bin_cache.mkdir(parents=True, exist_ok=True)
    with out.open("w") as destination:
        for row in rows:
            pid = row["problem_id"]
            put_source = puts / pid / row["put_name"]
            references = sorted((problems / pid / "reference_programs").rglob("*.cpp"))
            binaries = []
            compile_errors = []
            for name, source in [("put", put_source)] + [(f"ref{i}", p) for i, p in enumerate(references[:3])]:
                source_hash = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
                binary = bin_cache / f"{pid}_{name}_{source_hash}"
                error = "" if binary.is_file() else _compile(source, binary)
                if error:
                    compile_errors.append({"source": str(source), "error": error})
                else:
                    binaries.append((name, binary))
            evaluable = not compile_errors and len(binaries) >= 3
            results = []
            for stdin in row.get("inputs", []):
                if not evaluable:
                    break
                ref_runs = [_run(binary, stdin) for name, binary in binaries if name != "put"]
                agreed = all(r["status"] == "pass" for r in ref_runs) and len({r.get("output") for r in ref_runs}) == 1
                put_run = _run(binaries[0][1], stdin) if agreed else None
                exposed = bool(agreed and put_run and (
                    put_run["status"] != "pass" or put_run.get("output") != ref_runs[0].get("output")
                ))
                results.append({"input": stdin, "reference_agreed": agreed, "references": ref_runs,
                                "put": put_run, "exposed": exposed})
            result = {
                "problem_id": pid, "arm": row["arm"], "evaluable": evaluable,
                "compile_errors": compile_errors, "generated": len(row.get("inputs", [])),
                "reference_agreed": sum(r["reference_agreed"] for r in results),
                "exposing": sum(r["exposed"] for r in results),
                "task_exposed": any(r["exposed"] for r in results), "results": results,
            }
            destination.write(json.dumps(result, ensure_ascii=False) + "\n")
            summary["tasks"] += 1
            summary["evaluable_tasks"] += evaluable
            summary["exposed_tasks"] += result["task_exposed"]
            summary["reference_agreed_inputs"] += result["reference_agreed"]
            summary["exposing_inputs"] += result["exposing"]
            print(f"{pid} {row['arm']} agreed={result['reference_agreed']} exposed={result['exposing']} evaluable={evaluable}", flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pred", required=True)
    parser.add_argument("--problems", default="/tmp/TrickyBugs-selected/problems")
    parser.add_argument("--puts", default="/tmp/TrickCatcher-upstream/Datasets/TrickyBugs/PUT_cpp")
    parser.add_argument("--out", required=True)
    parser.add_argument("--bin-cache", default="/tmp/trickcatcher-cpp-binaries")
    args = parser.parse_args()
    print(json.dumps(evaluate(Path(args.pred), Path(args.problems), Path(args.puts), Path(args.out), Path(args.bin_cache))))


if __name__ == "__main__":
    main()
