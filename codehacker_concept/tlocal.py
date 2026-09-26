"""Stage 0: rebuild T_local (CodeContests+ tests) and derive S_target.

CodeHacker targets S_target = {s : J(s, T_local) = AC and J(s, T_official) != AC}
(Sec. 3.1). The released ``incorrect_codes`` are officially incorrect, so
S_target is the subset that passes every CodeContests+ test. CodeContests+
tests are produced by running its testlib generator with each line of
``generator_cmd``; expected outputs come from the standard solution.

Per problem, this also records CodeContests+ validity (VPR under the
released refined validator) and which extra correct submissions pass T_local
(needed for TPR and for the consensus oracle).
"""

from __future__ import annotations

import argparse
import gzip
import json
import shlex
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from codehacker_concept.data import Problem, code_fingerprint, data_dir, load_ccplus, load_plus
from codehacker_concept.judge import ProblemJudge
from codehacker_concept.sandbox import compile_cpp, run_binary

GEN_TL_MS = 10000
MAX_INCORRECT = 40
MAX_CORRECT = 8


def tlocal_dir() -> Path:
    path = data_dir() / "tlocal"
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_generator_cmds(generator_cmd: str) -> list[list[str]]:
    commands = []
    for line in (generator_cmd or "").splitlines():
        line = line.strip()
        if not line:
            continue
        line = line.split(">")[0].strip()  # drop "> $" style redirections
        try:
            tokens = shlex.split(line)
        except ValueError:
            tokens = line.split()
        if not tokens:
            continue
        commands.append(tokens[1:])  # drop "./gen"
    return commands


def save_inputs(problem_id: str, inputs: list[str]) -> Path:
    path = tlocal_dir() / f"{problem_id}.inputs.jsonl.gz"
    with gzip.open(path, "wt") as handle:
        for text in inputs:
            handle.write(json.dumps(text) + "\n")
    return path


def load_inputs(problem_id: str) -> list[str]:
    path = tlocal_dir() / f"{problem_id}.inputs.jsonl.gz"
    if not path.exists():
        return []
    with gzip.open(path, "rt") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def summary_path(problem_id: str) -> Path:
    return tlocal_dir() / f"{problem_id}.json"


def load_summary(problem_id: str) -> dict[str, Any] | None:
    path = summary_path(problem_id)
    return json.loads(path.read_text()) if path.exists() else None


def passes_all(judge: ProblemJudge, source: str, inputs: list[str], answers: list[str]) -> tuple[bool, str, int]:
    compiled = compile_cpp(source)
    if not compiled.ok or compiled.binary is None:
        return False, "CE", -1
    for index, (stdin, answer) in enumerate(zip(inputs, answers)):
        run = run_binary(compiled.binary, stdin, judge.time_limit_ms, judge.memory_limit_mb)
        if run.status != "OK":
            return False, run.status, index
        verdict, _ = judge.check(stdin, run.stdout, answer)
        if verdict != "AC":
            return False, verdict, index
    return True, "AC", len(inputs)


def build_problem(problem: Problem, ccplus: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"id": problem.id, "judge_type": problem.judge_type}
    commands = parse_generator_cmds(ccplus.get("generator_cmd", ""))
    generator = compile_cpp(ccplus.get("generator") or "")
    summary["n_commands"] = len(commands)
    if not generator.ok or generator.binary is None or not commands:
        summary["error"] = "generator unavailable"
        return summary
    raw_inputs: list[str] = []
    for args in commands:
        run = run_binary(generator.binary, "", GEN_TL_MS, 2048, args=args)
        if run.status == "OK" and run.stdout.strip():
            raw_inputs.append(run.stdout)
    judge = ProblemJudge([problem.validator], problem.checker, problem.correct_code,
                         problem.time_limit_ms, problem.memory_limit_mb)
    valid_inputs: list[str] = []
    for stdin in raw_inputs:
        if judge.validate(stdin)[0]:
            valid_inputs.append(stdin)
    summary["n_generated"] = len(raw_inputs)
    summary["n_valid"] = len(valid_inputs)
    inputs: list[str] = []
    answers: list[str] = []
    std_fail = 0
    for stdin in valid_inputs:
        std, _ = judge.std_output(stdin)
        if std is None or std.status != "OK":
            std_fail += 1
            continue
        inputs.append(stdin)
        answers.append(std.stdout)
    summary["n_tests"] = len(inputs)
    summary["std_fail"] = std_fail
    if not inputs:
        summary["error"] = "no usable T_local tests"
        return summary
    save_inputs(problem.id, inputs)
    incorrect = []
    seen: set[str] = set()
    for index, code in enumerate(problem.incorrect_codes):
        fp = code_fingerprint(code)
        if fp in seen:
            continue
        seen.add(fp)
        incorrect.append(index)
        if len(incorrect) >= MAX_INCORRECT:
            break
    results = []
    for index in incorrect:
        ok, verdict, where = passes_all(judge, problem.incorrect_codes[index], inputs, answers)
        results.append({"index": index, "passes_tlocal": ok, "verdict": verdict, "fail_test": where})
    summary["incorrect"] = results
    summary["s_target"] = [r["index"] for r in results if r["passes_tlocal"]]
    correct = []
    for index, sub in enumerate((ccplus.get("correct_submissions") or [])[:MAX_CORRECT]):
        ok, verdict, where = passes_all(judge, sub["code"], inputs, answers)
        correct.append({"index": index, "passes_tlocal": ok, "verdict": verdict, "fail_test": where})
    summary["correct"] = correct
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--ids-file")
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()
    problems = {p.id: p for p in load_plus()}
    ccplus = load_ccplus()
    ids = list(args.ids or [])
    if args.ids_file:
        ids += [line.strip() for line in Path(args.ids_file).read_text().splitlines() if line.strip()]
    todo = [pid for pid in ids if pid in problems and pid in ccplus and load_summary(pid) is None]
    print(f"{len(todo)} problems to build ({len(ids)} requested)", flush=True)

    def work(pid: str) -> dict[str, Any]:
        try:
            summary = build_problem(problems[pid], ccplus[pid])
        except Exception as exc:  # noqa: BLE001 - keep the batch going
            summary = {"id": pid, "error": f"{type(exc).__name__}: {exc}"}
        summary_path(pid).write_text(json.dumps(summary))
        return summary

    with ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(work, pid) for pid in todo]
        for future in as_completed(futures):
            s = future.result()
            print(json.dumps({k: s.get(k) for k in ("id", "judge_type", "n_tests", "n_valid", "n_generated", "s_target", "error")}), flush=True)


if __name__ == "__main__":
    main()
