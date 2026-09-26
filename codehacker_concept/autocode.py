"""AutoCode (arXiv 2510.12803) components.

* Algorithm 1 BuildValidator: 40 LLM cases (10 valid + 30 near-valid illegal),
  3 candidate validators, keep the argmax of correctly classified cases.
* Algorithm 3 BuildChecker: 40 labelled scenarios (inputs filtered by the
  validator, reference output from the standard solution), 3 candidate
  checkers, keep the argmax accuracy.
* Algorithm 2 BuildGeneratorSuite: three strategies (ExhaustiveSmall,
  RandomExtreme, TLEInducing), validator filtering, signature dedup, bucket
  balancing, and coverage sampling.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from codehacker_concept import prompts
from codehacker_concept.judge import checker_verdict
from codehacker_concept.llm import LLM, extract_code, extract_json
from codehacker_concept.sandbox import compile_cpp, run_binary

N_CASES = 40
N_CANDIDATES = 3
GEN_TL_MS = 10000
GEN_OUTPUT_LIMIT = 48 << 20


def normalize_input(text: str) -> str:
    """LLM-written inputs often miss the final newline; testlib validators require it."""
    text = text.replace("\r\n", "\n")
    return text if text.endswith("\n") else text + "\n"


def run_validator(source: str, stdin: str) -> bool | None:
    compiled = compile_cpp(source)
    if not compiled.ok or compiled.binary is None:
        return None
    return run_binary(compiled.binary, stdin, 10000, 2048).status == "OK"


def validator_accuracy(source: str, cases: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
    compiled = compile_cpp(source)
    if not compiled.ok or compiled.binary is None:
        return -1, []
    score = 0
    wrong = []
    for case in cases:
        got = run_binary(compiled.binary, case["input"], 10000, 2048).status == "OK"
        if got == bool(case["valid"]):
            score += 1
        else:
            wrong.append({**case, "validator_said": got})
    return score, wrong


@dataclass
class ValidatorSelection:
    source: str
    cases: list[dict[str, Any]]
    scores: list[int]
    candidates: list[str] = field(default_factory=list)


def _parse_cases(text: str) -> list[dict[str, Any]]:
    data = extract_json(text)
    items = data.get("cases") if isinstance(data, dict) else data
    cases = []
    for item in items or []:
        if not isinstance(item, dict) or "input" not in item:
            continue
        valid = item.get("valid")
        if isinstance(valid, str):
            valid = valid.strip().lower() in {"true", "valid", "yes"}
        cases.append({"input": normalize_input(str(item["input"])), "valid": bool(valid),
                      "reason": str(item.get("reason", ""))[:200], "source": "autocode"})
    return cases


def select_validator(llm: LLM, description: str, key: str, extra_cases: list[dict[str, Any]] | None = None) -> ValidatorSelection:
    """AutoCode Algorithm 1."""
    reply = llm.chat([("user", prompts.render(prompts.AUTOCODE_VALIDATOR_CASES, problem_description=description))],
                     tag="autocode.validator_cases", sample_key=key)
    cases = _parse_cases(reply.text)[:N_CASES] + list(extra_cases or [])
    candidates = []
    for variant_index, variant in enumerate(prompts.AUTOCODE_VALIDATOR_VARIANTS[:N_CANDIDATES]):
        reply = llm.chat([("user", prompts.render(prompts.AUTOCODE_VALIDATOR_PROGRAM, problem_description=description,
                                                  variant=variant))],
                         tag="autocode.validator_program", sample_key=f"{key}#v{variant_index}")
        code = extract_code(reply.text) or ""
        candidates.append(code)
    scores = [validator_accuracy(code, cases)[0] if code else -1 for code in candidates]
    best = max(range(len(candidates)), key=lambda i: scores[i]) if candidates else 0
    return ValidatorSelection(candidates[best] if candidates else "", cases, scores, candidates)


@dataclass
class CheckerSelection:
    source: str
    scenarios: list[dict[str, Any]]
    scores: list[float]
    candidates: list[str] = field(default_factory=list)


def checker_accuracy(source: str, scenarios: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    compiled = compile_cpp(source)
    if not compiled.ok or compiled.binary is None or not scenarios:
        return -1.0, []
    hits = 0
    wrong = []
    for scenario in scenarios:
        verdict, _ = checker_verdict(compiled.binary, scenario["input"], scenario["contestant_output"], scenario["ref_output"])
        if verdict == scenario["verdict"]:
            hits += 1
        else:
            wrong.append({**scenario, "checker_said": verdict})
    return hits / len(scenarios), wrong


def select_checker(
    llm: LLM,
    description: str,
    reference_code: str,
    key: str,
    validator: Callable[[str], bool | None],
    reference_output: Callable[[str], str | None],
) -> CheckerSelection:
    """AutoCode Algorithm 3 (scenario inputs filtered by the selected validator)."""
    reply = llm.chat([("user", prompts.render(prompts.AUTOCODE_CHECKER_SCENARIOS, problem_description=description,
                                              reference_code=reference_code))],
                     tag="autocode.checker_scenarios", sample_key=key)
    data = extract_json(reply.text)
    items = data.get("scenarios") if isinstance(data, dict) else data
    scenarios = []
    for item in (items or [])[:N_CASES]:
        if not isinstance(item, dict) or "input" not in item:
            continue
        stdin = normalize_input(str(item["input"]))
        if not validator(stdin):
            continue
        ref = reference_output(stdin)
        if ref is None:
            continue
        verdict = str(item.get("verdict", "WA")).upper()
        scenarios.append({"input": stdin, "contestant_output": str(item.get("contestant_output", "")),
                          "ref_output": ref, "verdict": "AC" if verdict.startswith("AC") else "WA",
                          "source": "autocode"})
    candidates = []
    for variant_index, variant in enumerate(prompts.AUTOCODE_CHECKER_VARIANTS[:N_CANDIDATES]):
        reply = llm.chat([("user", prompts.render(prompts.AUTOCODE_CHECKER_PROGRAM, problem_description=description,
                                                  variant=variant))],
                         tag="autocode.checker_program", sample_key=f"{key}#c{variant_index}")
        candidates.append(extract_code(reply.text) or "")
    scores = [checker_accuracy(code, scenarios)[0] if code else -1.0 for code in candidates]
    best = max(range(len(candidates)), key=lambda i: scores[i]) if candidates else 0
    return CheckerSelection(candidates[best] if candidates else "", scenarios, scores, candidates)


# ------------------------------------------------------------ Algorithm 2


GENERATOR_STRATEGIES = {
    "exhaustive_small": prompts.AUTOCODE_GEN_EXHAUSTIVE,
    "random_extreme": prompts.AUTOCODE_GEN_RANDOM_EXTREME,
    "tle_inducing": prompts.AUTOCODE_GEN_TLE,
}


def run_generator(source: str, args: list[str]) -> tuple[str | None, str]:
    compiled = compile_cpp(source)
    if not compiled.ok or compiled.binary is None:
        return None, "generator compile error: " + compiled.error[-600:]
    run = run_binary(compiled.binary, "", GEN_TL_MS, 2048, args=args)
    if run.status != "OK":
        return None, f"generator {run.status} (exit {run.exit_code}) {run.stderr[-300:]}"
    if not run.stdout.strip():
        return None, "generator printed nothing"
    if len(run.stdout) > GEN_OUTPUT_LIMIT:
        return None, "generator output too large"
    return normalize_input(run.stdout), ""


def signature(stdin: str) -> str:
    """Normalization-based dedup signature (whitespace-insensitive)."""
    return hashlib.sha1(" ".join(stdin.split()).encode()).hexdigest()


def size_bucket(stdin: str) -> str:
    n = len(stdin)
    return "tiny" if n < 200 else "small" if n < 5000 else "medium" if n < 200000 else "large"


def build_generator_suite(
    llm: LLM,
    description: str,
    key: str,
    validator: Callable[[str], bool | None],
    runs_per_strategy: int = 8,
    target_size: int = 18,
) -> dict[str, Any]:
    """AutoCode Algorithm 2 -> {"tests": [...], "log": {...}}."""
    union: list[dict[str, Any]] = []
    log: dict[str, Any] = {}
    for name, template in GENERATOR_STRATEGIES.items():
        reply = llm.chat([("user", prompts.render(template, problem_description=description))],
                         tag=f"autocode.gen.{name}", sample_key=key)
        code = extract_code(reply.text) or ""
        produced = invalid = 0
        errors = []
        for idx in range(runs_per_strategy):
            stdin, error = run_generator(code, [str(idx)])
            if stdin is None:
                errors.append(error)
                continue
            produced += 1
            if not validator(stdin):
                invalid += 1
                continue
            union.append({"input": stdin, "strategy": name, "bucket": size_bucket(stdin)})
        log[name] = {"produced": produced, "invalid": invalid, "errors": errors[:2]}
    seen: set[str] = set()
    deduped = []
    for item in union:
        sig = signature(item["input"])
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(item)
    # BalanceBuckets + SampleWithCoverage: round-robin over (strategy, size bucket)
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in deduped:
        buckets.setdefault((item["strategy"], item["bucket"]), []).append(item)
    chosen: list[dict[str, Any]] = []
    while len(chosen) < target_size and any(buckets.values()):
        for bucket_key in sorted(buckets):
            if buckets[bucket_key] and len(chosen) < target_size:
                chosen.append(buckets[bucket_key].pop(0))
    log["union"] = len(union)
    log["deduped"] = len(deduped)
    log["selected"] = len(chosen)
    return {"tests": chosen, "log": log}


_HASH_HINT = re.compile(r"hash|Hash|HASH")
