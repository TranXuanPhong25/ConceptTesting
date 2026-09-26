"""Evaluation oracle, input validity and paper metrics for saved pipeline runs.

Ground truth follows the paper (Sec. 5.3): canonical outputs come from the
TrickyBugs reference programs; an input is valid by reference when every
compiled reference exits normally and all agree ("input_valid_byref").
The paper verified TrickyBugs input validity manually; here an *evaluation
validator* stands in for that step. It is built independently of every arm:
a different model (``gemini-3.1-pro-preview`` by default), no concept card, and
selection that requires accepting every original and additional TrickyBugs test
input (known valid) while rejecting truncated inputs and LLM-written illegal
cases. Every counted exposure must satisfy both checks ("strict" validity).
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from trickcatcher_concept import prompts
from trickcatcher_concept.data import Task, parse_examples
from trickcatcher_concept.llm import LLM
from trickcatcher_concept.oracle import PutScore, TestCase, aggregate, eligible_variants, score_put, test_cases_for
from trickcatcher_concept.pipeline import Config, _read_json, _write_json
from trickcatcher_concept.sandbox import OK, compile_cpp, run_program
from trickcatcher_concept.validator import (VALID, mechanical_negatives, parse_cases, parse_validators,
                                            run_validator, select_validator)

KS = tuple(range(2, 11))
EVAL_MODEL = "gemini-3.1-pro-preview"
_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


def _lock(key: str) -> threading.Lock:
    with _guard:
        return _locks.setdefault(key, threading.Lock())


class TaskEvaluator:
    def __init__(self, task: Task, cfg: Config, eval_llm: LLM | None, executor):
        self.task, self.cfg, self.llm, self.ex = task, cfg, eval_llm, executor
        self.root = Path(cfg.run_dir) / task.lang / task.pid / "eval"
        self.bin_cache = Path(cfg.run_dir) / "_bin"

    def references(self) -> list:
        programs = []
        for path in self.task.references:
            program, _ = compile_cpp(path.read_text(errors="replace"), self.bin_cache)
            if program is not None:
                programs.append(program)
        return programs

    def eval_validator(self) -> dict:
        path = self.root / "eval_validator.json"
        with _lock(str(path)):
            cached = _read_json(path)
            if cached is not None:
                return cached
            if self.llm is None:
                raise RuntimeError("evaluation validator missing and no eval LLM configured")
            empty_card: dict[str, Any] = {"constraints": []}
            name = f"{self.task.lang}/{self.task.pid}/eval/llm"
            record = self.llm.call(f"{name}/validators", prompts.validator_prompt(self.task.description, empty_card),
                                   temperature=1.0, max_tokens=12000)
            candidates = parse_validators(record["response"])
            cases = self.llm.call(f"{name}/cases", prompts.cases_prompt(self.task.description, empty_card),
                                  temperature=0.0, max_tokens=6000)
            labelled = parse_cases(cases["response"])
            positives = [i for i, _ in self.task.existing_tests] + [i for i, _ in self.task.additional_tests]
            positives += [i for i, _ in parse_examples(self.task.description)]
            positives = list(dict.fromkeys(positives))
            negatives = mechanical_negatives(positives)
            selection = select_validator(candidates, positives, labelled, negatives, self.root / "validator")
            result = {"model": self.llm.model_name(), "selected": selection.index, "reason": selection.reason,
                      "scores": selection.scores, "n_positives": len(positives), "code_path": None}
            if selection.code is not None:
                chosen = self.root / "validator" / "selected.py"
                chosen.write_text(selection.code)
                result["code_path"] = str(chosen)
            _write_json(path, result)
            return result

    def input_facts(self, items: list[dict]) -> dict[str, dict]:
        """Reference outputs and evaluation validity for each input, cached by content hash."""
        validator = self.eval_validator()
        vpath = Path(validator["code_path"]) if validator.get("code_path") else None
        refs = self.references()
        cache_dir = self.root / "facts"

        def one(item: dict):
            cache = cache_dir / f"{item['sha256'][:32]}.json"
            cached = _read_json(cache)
            if cached is not None:
                return item["id"], cached
            text = Path(item["path"]).read_text()
            results = [run_program(ref, text, timeout=self.cfg.exec_timeout * 2) for ref in refs]
            outs = {r.output for r in results if r.status == OK}
            byref = bool(refs) and all(r.status == OK for r in results) and len(outs) == 1
            facts = {"n_refs": len(refs), "byref": byref, "ref_out": next(iter(outs)) if byref else None,
                     "ref_status": [r.status for r in results],
                     "eval_validity": run_validator(vpath, text) if vpath else "no_validator"}
            _write_json(cache, facts)
            return item["id"], facts

        return dict(self.ex.map(one, [(item,) for item in items]))


def score_arm(task_dir: Path, arm: str, facts: dict[str, dict], validity: str, use_verify: bool,
              ks=KS) -> dict[str, Any] | None:
    outputs = _read_json(task_dir / arm / "outputs.json")
    if outputs is None:
        return None
    table = outputs["outputs"]
    verify = _read_json(task_dir / arm / "verify.json") if use_verify else None

    def input_valid(input_id: str) -> bool:
        f = facts.get(input_id)
        if f is None or not f["byref"]:
            return False
        if validity == "strict":
            return f["eval_validity"] == VALID
        return True

    def is_true(case: TestCase) -> bool:
        return input_valid(case.input_id) and facts[case.input_id]["ref_out"] == case.oracle

    allowed = None
    if verify is not None:
        def allowed(input_id: str) -> bool:
            v = verify.get(input_id)
            return bool(v and v["put_reproduced"] and any(v["variants_reproduced"].values()))

    per_k = {}
    for k in ks:
        s = score_put(table, k, is_true, input_valid, allowed)
        per_k[k] = {"total": s.total, "tp": s.tp, "fp": s.fp, "fp_bad_input": s.fp_bad_input,
                    "tp_rate": s.tp_rate, "precision": s.precision, "n_variants": s.n_variants}
    # bug exposure at k = all kept variants: any reported test case that is a true positive
    cases = test_cases_for(table, eligible_variants(table), allowed) if eligible_variants(table) else []
    exposing = sorted({c.input_id for c in cases if is_true(c)})
    return {"per_k": per_k, "reported_cases": len(cases), "true_cases": sum(is_true(c) for c in cases),
            "exposing_inputs": len(exposing), "task_exposed": bool(exposing), "witnesses": exposing[:5],
            "invalid_reported_cases": sum(not input_valid(c.input_id) for c in cases)}


def summarize(rows: list[dict], arm_key: str, n_puts: int, k: int) -> dict:
    scores = []
    for row in rows:
        r = row.get(arm_key)
        if not r:
            continue
        pk = r["per_k"][str(k)] if str(k) in r["per_k"] else r["per_k"][k]
        scores.append(PutScore(pk["n_variants"], k, pk["total"], pk["tp"], pk["fp"], pk["fp_bad_input"],
                               (pk["tp"] + pk["fp"]) > 0))
    return aggregate(scores, n_puts)


def dump(rows: list[dict], path: Path) -> None:
    """Atomic write so a concurrent reader (e.g. trickcatcher_concept.report) never sees a
    truncated file mid-write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    os.replace(tmp, path)
