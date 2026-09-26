"""Phase I: evaluation-tool calibration (CodeHacker Sec. 3.3, Algorithms 1-2).

Composition used here (both papers together):
  initial validator V0 = AutoCode Algorithm 1 selection (40 cases, 3 candidates)
  then CodeHacker Algorithm 1: bypass (invalid accepted) / rejection (valid
  rejected) attacks via the Appendix L validator-hack prompt; refine on failure;
  stop after K consecutive clean rounds (K=2, as in the official demo).
  initial checker C0 = AutoCode Algorithm 3 selection
  then CodeHacker Algorithm 2: deception (wrong accepted) / rejection (valid
  alternative rejected) attacks, with the anti-hallucination pipeline
  (small inputs only, explicit reasoning, independent LLM judge) and
  y_gt from the oracle (standard solution).

Guard (our addition, flagged): a refined tool replaces the current one only if
it does not lose accuracy on the accumulated labelled regression set
(AutoCode cases + earlier probes). Algorithm 1 trusts the attacker's labels;
without a guard one hallucinated label can regress a correct validator.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from codehacker_concept import prompts
from codehacker_concept.autocode import (
    checker_accuracy,
    normalize_input,
    run_validator,
    select_checker,
    select_validator,
    validator_accuracy,
)
from codehacker_concept.data import Problem, data_dir
from codehacker_concept.judge import checker_verdict
from codehacker_concept.llm import LLM, extract_code, extract_json
from codehacker_concept.sandbox import compile_cpp, run_binary

K_STABLE = 2
MAX_ROUNDS = 5
SMALL_INPUT_CHARS = 400


@dataclass
class PhaseOneResult:
    problem_id: str
    validator: str
    checker: str
    validator_log: dict[str, Any] = field(default_factory=dict)
    checker_log: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def phase1_path(problem_id: str) -> Path:
    path = data_dir() / "phase1"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{problem_id}.json"


def load_phase1(problem_id: str) -> PhaseOneResult | None:
    path = phase1_path(problem_id)
    if not path.exists():
        return None
    return PhaseOneResult(**json.loads(path.read_text()))


def _std_output(problem: Problem, stdin: str) -> str | None:
    compiled = compile_cpp(problem.correct_code)
    if not compiled.ok or compiled.binary is None:
        return None
    run = run_binary(compiled.binary, stdin, problem.time_limit_ms, problem.memory_limit_mb)
    return run.stdout if run.status == "OK" else None


# ------------------------------------------------------------ Algorithm 1


def refine_validator(
    llm: LLM, problem: Problem, validator: str, regression: list[dict[str, Any]], key: str
) -> tuple[str, dict[str, Any]]:
    rounds = []
    clean = 0
    refinements = 0
    for round_index in range(MAX_ROUNDS):
        reply = llm.chat([("user", prompts.render(prompts.APPENDIX_L_VALIDATOR_HACK,
                                                  problem_description=problem.description,
                                                  validator_code=validator))],
                         tag="codehacker.validator_hack", sample_key=f"{key}#r{round_index}")
        data = extract_json(reply.text)
        probes = []
        for item in (data.get("test_cases") if isinstance(data, dict) else data) or []:
            if not isinstance(item, dict) or "test_input" not in item:
                continue
            expected = str(item.get("expected_validity", "")).lower()
            if expected not in {"valid", "invalid"}:
                expected = "invalid" if item.get("bug_type") == "false_positive" else "valid"
            probes.append({"input": normalize_input(str(item["test_input"])), "valid": expected == "valid",
                           "reason": str(item.get("strategy", ""))[:200], "source": "codehacker_probe"})
        failures = []
        for probe in probes:
            got = run_validator(validator, probe["input"])
            if got is None or got != probe["valid"]:
                failures.append({**probe, "validator_said": got})
        entry: dict[str, Any] = {"round": round_index, "probes": len(probes), "failures": len(failures)}
        if failures:
            clean = 0
            failure_text = "\n\n".join(
                f"Input:\n{f['input'][:600]}\nGround truth: {'VALID' if f['valid'] else 'INVALID'} ({f['reason']})\n"
                f"Validator said: {'VALID' if f['validator_said'] else 'INVALID'}" for f in failures[:6])
            refined_reply = llm.chat([("user", prompts.render(prompts.GLUE_REFINE_VALIDATOR,
                                                              problem_description=problem.description,
                                                              code=validator, failures=failure_text))],
                                     tag="codehacker.validator_refine", sample_key=f"{key}#r{round_index}")
            candidate = extract_code(refined_reply.text) or ""
            new_regression = regression + probes
            old_score, _ = validator_accuracy(validator, new_regression)
            new_score, _ = validator_accuracy(candidate, new_regression) if candidate else (-1, [])
            accepted = new_score >= old_score and new_score >= 0
            entry.update({"old_score": old_score, "new_score": new_score, "accepted": accepted,
                          "regression_size": len(new_regression)})
            if accepted:
                validator = candidate
                refinements += 1
            regression = new_regression
        else:
            clean += 1
            regression = regression + probes
        rounds.append(entry)
        if clean >= K_STABLE:
            break
    return validator, {"rounds": rounds, "refinements": refinements, "converged": clean >= K_STABLE,
                       "regression": regression}


# ------------------------------------------------------------ Algorithm 2


def refine_checker(
    llm: LLM, problem: Problem, checker: str, validator: str, regression: list[dict[str, Any]], key: str
) -> tuple[str, dict[str, Any]]:
    rounds = []
    clean = 0
    refinements = 0
    judge_calls = 0
    for round_index in range(MAX_ROUNDS):
        reply = llm.chat([("user", prompts.render(prompts.APPENDIX_L_CHECKER_HACK,
                                                  problem_description=problem.description,
                                                  checker_code=checker)
                           + "\n\nFor every test case also include a field \"reasoning\" that derives, step by step,"
                             " why fake_output is wrong (false_positive) or valid (false_negative).")],
                         tag="codehacker.checker_hack", sample_key=f"{key}#r{round_index}")
        data = extract_json(reply.text)
        compiled = compile_cpp(checker)
        verified_failures = []
        probes_seen = 0
        dropped = {"large": 0, "invalid_input": 0, "no_oracle": 0, "judge_rejected": 0}
        for item in (data.get("test_cases") if isinstance(data, dict) else data) or []:
            if not isinstance(item, dict) or "test_input" not in item:
                continue
            probes_seen += 1
            stdin = normalize_input(str(item["test_input"]))
            output = str(item.get("fake_output", ""))
            claimed_ok = item.get("bug_type") == "false_negative"
            # (1) small-scale inputs only
            if len(stdin) > SMALL_INPUT_CHARS:
                dropped["large"] += 1
                continue
            if not run_validator(validator, stdin):
                dropped["invalid_input"] += 1
                continue
            y_gt = _std_output(problem, stdin)  # oracle O(Phi, x)
            if y_gt is None:
                dropped["no_oracle"] += 1
                continue
            if not compiled.ok or compiled.binary is None:
                said = "FAIL"
            else:
                said, _ = checker_verdict(compiled.binary, stdin, output, y_gt)
            is_fp = (not claimed_ok) and said == "AC"
            is_fn = claimed_ok and said != "AC"
            if not (is_fp or is_fn):
                continue
            # (2)+(3) explicit reasoning audited by an independent LLM judge
            judge_calls += 1
            verdict = llm.chat([("user", prompts.render(prompts.GLUE_CHECKER_JUDGE,
                                                        problem_description=problem.description, input=stdin,
                                                        output=output,
                                                        reasoning=str(item.get("reasoning", item.get("strategy", "")))[:2000]))],
                               tag="codehacker.checker_judge", sample_key=f"{key}#r{round_index}#{probes_seen}")
            audit = extract_json(verdict.text) or {}
            judged_valid = bool(audit.get("output_is_valid")) if isinstance(audit, dict) else None
            if judged_valid is None or judged_valid != claimed_ok:
                dropped["judge_rejected"] += 1
                continue
            verified_failures.append({"input": stdin, "contestant_output": output, "ref_output": y_gt,
                                      "verdict": "AC" if claimed_ok else "WA", "checker_said": said,
                                      "reason": str(item.get("strategy", ""))[:200], "source": "codehacker_probe"})
        entry: dict[str, Any] = {"round": round_index, "probes": probes_seen, "verified_failures": len(verified_failures),
                                 "dropped": dropped}
        if verified_failures:
            clean = 0
            failure_text = "\n\n".join(
                f"Input:\n{f['input']}\nContestant output:\n{f['contestant_output'][:400]}\n"
                f"Jury answer (reference solution):\n{f['ref_output'][:400]}\nCorrect verdict: {f['verdict']}"
                f" (checker said {f['checker_said']}; {f['reason']})" for f in verified_failures[:6])
            refined_reply = llm.chat([("user", prompts.render(prompts.GLUE_REFINE_CHECKER,
                                                              problem_description=problem.description,
                                                              code=checker, failures=failure_text))],
                                     tag="codehacker.checker_refine", sample_key=f"{key}#r{round_index}")
            candidate = extract_code(refined_reply.text) or ""
            new_regression = regression + verified_failures
            old_score, _ = checker_accuracy(checker, new_regression)
            new_score, _ = checker_accuracy(candidate, new_regression) if candidate else (-1.0, [])
            accepted = new_score >= old_score and new_score >= 0
            entry.update({"old_score": round(old_score, 3), "new_score": round(new_score, 3), "accepted": accepted})
            if accepted:
                checker = candidate
                refinements += 1
            regression = new_regression
        else:
            clean += 1
        rounds.append(entry)
        if clean >= K_STABLE:
            break
    return checker, {"rounds": rounds, "refinements": refinements, "converged": clean >= K_STABLE,
                     "judge_calls": judge_calls, "regression": regression}


# ------------------------------------------------------------ Phase I driver


def run_phase1(llm: LLM, problem: Problem, tlocal_samples: list[str] | None = None) -> PhaseOneResult:
    cached = load_phase1(problem.id)
    if cached is not None:
        return cached
    key = f"phase1:{problem.id}"
    extra = [{"input": normalize_input(s), "valid": True, "reason": "CodeContests+ local test", "source": "tlocal"}
             for s in (tlocal_samples or []) if len(s) <= 50000][:10]
    selection = select_validator(llm, problem.description, key, extra_cases=extra)
    validator, vlog = refine_validator(llm, problem, selection.source, selection.cases, key)
    vlog.update({"autocode_scores": selection.scores, "autocode_cases": len(selection.cases)})

    def validate(stdin: str) -> bool | None:
        return run_validator(validator, stdin)

    checker_sel = select_checker(llm, problem.description, problem.correct_code, key, validate,
                                 lambda s: _std_output(problem, s))
    checker, clog = refine_checker(llm, problem, checker_sel.source, validator, checker_sel.scenarios, key)
    clog.update({"autocode_scores": checker_sel.scores, "autocode_scenarios": len(checker_sel.scenarios)})
    result = PhaseOneResult(problem.id, validator, checker, vlog, clog)
    phase1_path(problem.id).write_text(json.dumps(result.to_json()))
    return result


def audit_against_gold(problem: Problem, result: PhaseOneResult, extra_inputs: list[str] | None = None) -> dict[str, Any]:
    """Compare calibrated tools with the authors' released (human-audited) tools."""
    inputs = [case["input"] for case in result.validator_log.get("regression", [])]
    inputs += [normalize_input(s) for s in (extra_inputs or [])]
    agree = fp = fn = gold_valid = 0
    seen = set()
    for stdin in inputs:
        if stdin in seen:
            continue
        seen.add(stdin)
        gold = run_validator(problem.validator, stdin)
        ours = run_validator(result.validator, stdin)
        if gold is None or ours is None:
            continue
        gold_valid += int(gold)
        if gold == ours:
            agree += 1
        elif ours and not gold:
            fp += 1  # ours too loose
        else:
            fn += 1  # ours too strict
    checker_agree = checker_total = 0
    gold_bin = compile_cpp(problem.checker)
    ours_bin = compile_cpp(result.checker)
    for scenario in result.checker_log.get("regression", []):
        if not (gold_bin.ok and ours_bin.ok):
            break
        g, _ = checker_verdict(gold_bin.binary, scenario["input"], scenario["contestant_output"], scenario["ref_output"])
        o, _ = checker_verdict(ours_bin.binary, scenario["input"], scenario["contestant_output"], scenario["ref_output"])
        checker_total += 1
        checker_agree += int(g == o)
    total = agree + fp + fn
    return {"validator_inputs": total, "validator_agree": agree, "validator_too_loose": fp, "validator_too_strict": fn,
            "gold_valid": gold_valid, "checker_scenarios": checker_total, "checker_agree": checker_agree}
