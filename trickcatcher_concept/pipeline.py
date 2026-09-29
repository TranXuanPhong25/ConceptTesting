"""Full TrickCatcher pipeline (paper Sec. 4) with an optional concept layer.

Stages per PUT and arm, each persisted as JSON so a killed run resumes:
  card       [concept] enumerated input rules + PUT-specific fault hypotheses
  validator  [concept] AutoCode-style selected validator
  variants   10 PUT-guided variants (paper Fig. 3), filtered by the existing tests (Sec. 4.1)
  inputs     LLM-written input generator (paper Fig. 4) run to produce 100 inputs (Sec. 4.2);
             [concept] rules/hypotheses appended and inputs filtered by the validator
  outputs    PUT and every kept variant executed on every input (Sec. 4.3)
  verify     [concept] AnyPoC-style independent re-execution of each discrepancy
Scoring (diversity-driven oracle + paper metric) lives in ``oracle.py``/``evaluate.py``.
"""

from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import os
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trickcatcher_concept import prompts
from trickcatcher_concept.data import Task
from trickcatcher_concept.llm import LLM, extract_code, extract_json
from trickcatcher_concept.provenance import read_template, sha256_text
from trickcatcher_concept.sandbox import (OK, Program, compile_cpp, normalize_output, python_program, run_program,
                                          run_script)
from trickcatcher_concept.validator import (VALID, mechanical_negatives, parse_cases, parse_validators,
                                            run_validator, select_validator)

ARMS = ("baseline", "concept")
N_VARIANTS = 10
N_INPUTS = 100
MIN_USABLE_INPUTS = 10
MAX_GENERATOR_ATTEMPTS = 3
MAX_INPUT_BYTES = 8_000_000


@dataclass
class Config:
    run_dir: Path
    artifact: Path
    variant_temperature: float = 1.0
    generator_temperature: float = 1.0
    card_temperature: float = 0.0
    variant_max_tokens: int = 8192
    generator_max_tokens: int = 8192
    card_max_tokens: int = 6000
    steer_fraction: float = 1.0  # share of the 10 variants that receive a hypothesis
    exec_timeout: float = 5.0
    exec_workers: int = 12


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1))
    os.replace(tmp, path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text()) if path.is_file() else None


class Executor:
    """Shared bounded pool for program executions."""

    def __init__(self, workers: int):
        self.pool = cf.ThreadPoolExecutor(max_workers=workers)

    def map(self, fn, items):
        return list(self.pool.map(lambda item: fn(*item), items))


class ArmRunner:
    def __init__(self, task: Task, arm: str, cfg: Config, llm: LLM, executor: Executor):
        if arm not in ARMS:
            raise ValueError(arm)
        self.task, self.arm, self.cfg, self.llm, self.ex = task, arm, cfg, llm, executor
        self.root = Path(cfg.run_dir) / task.lang / task.pid
        self.dir = self.root / arm
        self.bin_cache = Path(cfg.run_dir) / "_bin"
        self.concept = arm == "concept"
        self.log: list[str] = []

    # ---------- helpers ----------
    def _name(self, stage: str) -> str:
        return f"{self.task.lang}/{self.task.pid}/{self.arm}/llm/{stage}"

    def _program(self, source: str) -> tuple[Program | None, str]:
        if self.task.lang == "cpp":
            return compile_cpp(source, self.bin_cache)
        return python_program(source, self.bin_cache), ""

    def put_program(self) -> Program:
        program, error = self._program(self.task.put_source)
        if program is None:
            raise RuntimeError(f"PUT does not compile: {error[:300]}")
        return program

    # ---------- concept stages ----------
    def card(self) -> dict:
        path = self.dir / "card.json"
        cached = _read_json(path)
        if cached is not None:
            return cached
        prompt = prompts.card_prompt(self.task.lang, self.task.description, self.task.put_source)
        card: dict[str, Any] = {"constraints": [], "hypotheses": [], "parse_error": ""}
        for attempt in range(2):
            record = self.llm.call(self._name(f"card_{attempt}"), prompt, temperature=self.cfg.card_temperature,
                                   max_tokens=self.cfg.card_max_tokens)
            try:
                parsed = extract_json(record["response"])
                card["constraints"] = [c for c in parsed.get("constraints", []) if isinstance(c, dict)]
                card["hypotheses"] = [h for h in parsed.get("hypotheses", []) if isinstance(h, dict)][:5]
                card["parse_error"] = ""
                break
            except (ValueError, AttributeError) as exc:
                card["parse_error"] = str(exc)
        _write_json(path, card)
        return card

    def validator(self, card: dict) -> dict:
        path = self.dir / "validator.json"
        cached = _read_json(path)
        if cached is not None:
            return cached
        record = self.llm.call(self._name("validators"), prompts.validator_prompt(self.task.description, card),
                               temperature=self.cfg.variant_temperature, max_tokens=self.cfg.generator_max_tokens)
        candidates = parse_validators(record["response"])
        cases_record = self.llm.call(self._name("validator_cases"), prompts.cases_prompt(self.task.description, card),
                                     temperature=self.cfg.card_temperature, max_tokens=4000)
        labelled = parse_cases(cases_record["response"])
        positives = [inp for inp, _ in self.task.existing_tests]
        negatives = mechanical_negatives(positives)
        selection = select_validator(candidates, positives, labelled, negatives, self.dir / "validator")
        result = {"n_candidates": len(candidates), "n_labelled": len(labelled), "n_negatives": len(negatives),
                  "selected": selection.index, "reason": selection.reason, "scores": selection.scores,
                  "code_path": None}
        if selection.code is not None:
            chosen = self.dir / "validator" / "selected.py"
            chosen.write_text(selection.code)
            result["code_path"] = str(chosen)
        _write_json(path, result)
        return result

    # ---------- paper stages ----------
    def _variant_hypothesis(self, index: int, card: dict | None) -> dict | None:
        if not self.concept or not card or not card.get("hypotheses"):
            return None
        steered = round(N_VARIANTS * self.cfg.steer_fraction)
        if index >= steered:
            return None
        hyps = card["hypotheses"]
        return hyps[index % len(hyps)]

    def variants(self, card: dict | None) -> list[dict]:
        path = self.dir / "variants.json"
        cached = _read_json(path)
        if cached is not None:
            return cached
        template = read_template(self.cfg.artifact, "genprog_tc")

        def one(index: int) -> dict:
            hypothesis = self._variant_hypothesis(index, card)
            prompt = prompts.variant_prompt(template, self.task.description, self.task.put_source, hypothesis)
            entry: dict[str, Any] = {"index": index, "hypothesis": (hypothesis or {}).get("id"),
                                     "prompt_lineage": "verbatim_original" if hypothesis is None else "paper_prompt+hypothesis"}
            try:
                record = self.llm.call(self._name(f"variant_{index}"), prompt,
                                       temperature=self.cfg.variant_temperature, max_tokens=self.cfg.variant_max_tokens)
            except RuntimeError as exc:
                entry.update(status="llm_error", error=str(exc)[:300])
                return entry
            code = extract_code(record["response"], self.task.lang)
            ext = "cpp" if self.task.lang == "cpp" else "py"
            source_path = self.dir / "variants" / f"v{index}.{ext}"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(code)
            program, error = self._program(code)
            if program is None:
                entry.update(status="compile_error", error=error[:300])
                return entry
            entry["program"] = program.path
            passed = 0
            for stdin_text, expected in self.task.existing_tests:
                result = run_program(program, stdin_text, timeout=self.cfg.exec_timeout)
                if result.status != OK or result.output != normalize_output(expected):
                    entry.update(status="filtered_out", passed=passed, failed_status=result.status)
                    return entry
                passed += 1
            entry.update(status="kept", passed=passed)
            return entry

        with cf.ThreadPoolExecutor(max_workers=N_VARIANTS) as pool:
            entries = list(pool.map(one, range(N_VARIANTS)))
        _write_json(path, entries)
        return entries

    def inputs(self, card: dict | None, validator: dict | None) -> list[dict]:
        path = self.dir / "inputs.json"
        cached = _read_json(path)
        if cached is not None:
            return cached
        template = read_template(self.cfg.artifact, "geninput_generator")
        prompt = prompts.generator_prompt(template, self.task.pid, self.task.description, card if self.concept else None)
        validator_path = Path(validator["code_path"]) if validator and validator.get("code_path") else None
        attempts = []
        chosen: list[dict] = []
        for attempt in range(MAX_GENERATOR_ATTEMPTS):
            try:
                record = self.llm.call(self._name(f"generator_{attempt}"), prompt,
                                       temperature=self.cfg.generator_temperature, max_tokens=self.cfg.generator_max_tokens)
            except RuntimeError as exc:
                attempts.append({"attempt": attempt, "status": "llm_error", "error": str(exc)[:300]})
                continue
            items, info = self._run_generator(attempt, extract_code(record["response"], "python"), validator_path)
            attempts.append(info)
            if info["usable"] >= MIN_USABLE_INPUTS:
                chosen = items
                break
            if len([i for i in items if i["usable"]]) > len([i for i in chosen if i["usable"]]):
                chosen = items  # keep the best attempt if all fall short
        result = {"attempts": attempts, "inputs": chosen}
        _write_json(path, result)
        return result

    def _run_generator(self, attempt: int, code: str, validator_path: Path | None) -> tuple[list[dict], dict]:
        work = self.dir / f"gen_{attempt}"
        if work.exists():
            shutil.rmtree(work)
        (work / "gen").mkdir(parents=True)
        out_dir = work / "chat_generated_inputs" / self.task.pid
        out_dir.mkdir(parents=True)
        script = work / "gen" / "generator.py"
        script.write_text(code)
        status, stderr = run_script(script, work / "gen")
        files = sorted(out_dir.glob("chatGenInput_*.in"),
                       key=lambda p: int(p.stem.split("_")[-1]) if p.stem.split("_")[-1].isdigit() else 10**9)
        items = []
        seen: set[str] = set()
        for file in files[:N_INPUTS]:
            if file.stat().st_size > MAX_INPUT_BYTES or file.stat().st_size == 0:
                continue
            text = file.read_text(errors="replace")
            digest = hashlib.sha256(text.encode()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            items.append({"id": f"a{attempt}_{file.stem.split('_')[-1]}", "sha256": digest, "path": str(file)})

        def check(item: dict) -> dict:
            if validator_path is None:
                item["method_validity"] = "unchecked"
                item["usable"] = True
            else:
                verdict = run_validator(validator_path, Path(item["path"]).read_text())
                item["method_validity"] = verdict
                item["usable"] = verdict == VALID
            return item

        items = self.ex.map(check, [(item,) for item in items])
        info = {"attempt": attempt, "status": str(status), "stderr": stderr[-500:], "files": len(files),
                "kept": len(items), "usable": sum(i["usable"] for i in items)}
        return items, info

    def outputs(self, variants: list[dict], inputs: dict) -> dict:
        path = self.dir / "outputs.json"
        cached = _read_json(path)
        if cached is not None:
            return cached
        programs = {"put": self.put_program()}
        for entry in variants:
            if entry.get("status") == "kept":
                programs[f"v{entry['index']}"] = Program(self.task.lang if self.task.lang == "cpp" else "py", entry["program"])
        usable = [i for i in inputs["inputs"] if i["usable"]]
        jobs = [(name, program, item) for name, program in programs.items() for item in usable]

        def run(name: str, program: Program, item: dict):
            result = run_program(program, Path(item["path"]).read_text(), timeout=self.cfg.exec_timeout)
            return name, item["id"], result.status, result.output

        table: dict[str, dict[str, list[str]]] = {name: {} for name in programs}
        for name, input_id, status, output in self.ex.map(run, jobs):
            table[name][input_id] = [status, output]
        result = {"programs": sorted(programs), "outputs": table}
        _write_json(path, result)
        return result

    def verify(self, variants: list[dict], inputs: dict, outputs: dict) -> dict:
        """AnyPoC-style check: re-execute every discrepancy in a fresh process."""
        path = self.dir / "verify.json"
        cached = _read_json(path)
        if cached is not None:
            return cached
        table = outputs["outputs"]
        by_id = {i["id"]: i for i in inputs["inputs"]}
        programs = {f"v{e['index']}": Program("cpp" if self.task.lang == "cpp" else "py", e["program"])
                    for e in variants if e.get("status") == "kept"}
        programs["put"] = self.put_program()
        jobs = []
        for input_id, (status, put_out) in table["put"].items():
            if status != OK:
                continue
            differing = [v for v in programs if v != "put" and table[v].get(input_id, [None])[0] == OK
                         and table[v][input_id][1] != put_out]
            if differing:
                jobs.append((input_id, differing))

        def check(input_id: str, differing: list[str]):
            text = Path(by_id[input_id]["path"]).read_text()
            put_again = run_program(programs["put"], text, timeout=self.cfg.exec_timeout * 2)
            stable = {v: run_program(programs[v], text, timeout=self.cfg.exec_timeout * 2).output == table[v][input_id][1]
                      for v in differing}
            return input_id, {"put_reproduced": put_again.status == OK and put_again.output == table["put"][input_id][1],
                              "variants_reproduced": stable}

        result = dict(self.ex.map(check, jobs))
        _write_json(path, result)
        return result

    # ---------- driver ----------
    def run(self) -> dict:
        done = self.dir / "done.json"
        if done.is_file():
            return json.loads(done.read_text())
        card = validator = None
        if self.concept:
            card = self.card()
            validator = self.validator(card)
        variants = self.variants(card)
        inputs = self.inputs(card, validator)
        outputs = self.outputs(variants, inputs)
        verify = self.verify(variants, inputs, outputs) if self.concept else None
        summary = {
            "task": self.task.key, "arm": self.arm,
            "variants_kept": sum(v.get("status") == "kept" for v in variants),
            "variant_status": [v.get("status") for v in variants],
            "inputs_usable": sum(i["usable"] for i in inputs["inputs"]),
            "inputs_generated": len(inputs["inputs"]),
            "generator_attempts": len(inputs["attempts"]),
            "hypotheses": len(card["hypotheses"]) if card else 0,
            "validator_selected": validator.get("selected") if validator else None,
            "verified_discrepancies": len(verify) if verify is not None else None,
        }
        _write_json(done, summary)
        return summary


_put_check_lock = threading.Lock()


def put_existing_check(task: Task, cfg: Config) -> dict:
    """Sanity check that the PUT is plausible under our toolchain (passes existing tests)."""
    path = Path(cfg.run_dir) / task.lang / task.pid / "put_check.json"
    cached = _read_json(path)
    if cached is not None:
        return cached
    bin_cache = Path(cfg.run_dir) / "_bin"
    program, error = (compile_cpp(task.put_source, bin_cache) if task.lang == "cpp"
                      else (python_program(task.put_source, bin_cache), ""))
    result = {"compiled": program is not None, "error": error[:300], "passed": 0, "total": len(task.existing_tests),
              "existing_source": task.existing_source}
    if program is not None:
        for stdin_text, expected in task.existing_tests:
            run = run_program(program, stdin_text, timeout=cfg.exec_timeout * 2)
            result["passed"] += run.status == OK and run.output == normalize_output(expected)
    _write_json(path, result)
    return result


def sha(text: str) -> str:
    return sha256_text(text)
