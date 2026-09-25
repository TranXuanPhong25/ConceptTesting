"""Generate ten inputs per PUT with TrickCatcher's direct-input prompt.

The official generator example contains HumanEval/0, so experiments start at 1.
Canonical solutions and EvalPlus contracts are never loaded in this module.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from magma.llm_client import make_llm, model_id
from trickcatcher_pilot.prompt_provenance import ARTIFACT_COMMIT, TEMPLATE_SHA256, read_original_templates
from trickcatcher_pilot.static_concepts import static_concept


CONCEPT_SYSTEM = (
    "Given a Python function and its docstring, infer test-relevant intermediate "
    "semantics using only this material. Return exactly a JSON object with string "
    "fields expected_property, suspected_shortcut, and separating_input_relation. "
    "The suspected shortcut must quote or closely identify actual PUT code. "
    "The separating relation must respect the documented input domain. "
    "If uncertain, state a hypothesis rather than claiming a proven bug. "
    "Do not generate a test or an expected concrete output."
)
GENERIC_SYSTEM = (
    "Given a Python function and its docstring, write a compact list of three "
    "valid corner-case input ideas for testing it. Use only this material. "
    "Do not generate tests, code, or expected outputs."
)


def _response_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(
            item if isinstance(item, str) else item.get("text", "")
            for item in value if isinstance(item, (str, dict))
        )
    return ""


def parse_inputs(raw: str, arity: int) -> list[list[Any]]:
    """Only accept literal parameter lists; never evaluate generated Python."""
    text = re.sub(r"```(?:python)?|```", "", raw, flags=re.IGNORECASE)
    parsed: list[list[Any]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            value = ast.literal_eval(line)
        except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
            continue
        if not isinstance(value, list) or len(value) != arity:
            continue
        try:
            json.dumps(value)
        except (TypeError, ValueError, OverflowError):
            continue
        fingerprint = repr(value)
        if fingerprint not in seen:
            parsed.append(value)
            seen.add(fingerprint)
    return parsed[:10]


def _concept_text(raw: str) -> str:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    try:
        obj = json.loads(match.group(0) if match else raw)
    except (ValueError, AttributeError):
        return raw.strip()[:1000]
    return "\n".join(f"- {key}: {obj.get(key, '')}" for key in (
        "expected_property", "suspected_shortcut", "separating_input_relation"
    ))


def build_input_messages(source: str, system_template: str, user_template: str, arm: str, plan: str = "") -> tuple[str, str]:
    user = user_template.format(function_and_docstring=source)
    if arm in {"concept", "static_concept", "reference_concept", "shuffled_concept"}:
        user += "\n\nConcept hypothesis (verify against the docstring while choosing inputs):\n" + _concept_text(plan)
    elif arm == "generic":
        user += "\n\nEdge-case planning notes:\n" + plan.strip()[:1000]
    return system_template, user


class _Invoker:
    def __init__(self, llm: Any, delay: float, retries: int):
        self.llm = llm
        self.delay = delay
        self.retries = retries
        self.last_request: float | None = None

    def __call__(self, system: str, user: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        for attempt in range(self.retries + 1):
            if self.last_request is not None:
                time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                response = self.llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
                text = _response_text(getattr(response, "content", response)).strip()
                if not text:
                    raise ValueError("empty response")
                return text
            except Exception as exc:
                transient = any(s in str(exc) for s in ("429", "504", "ResourceExhausted", "DeadlineExceeded"))
                if not transient or attempt == self.retries:
                    raise
                time.sleep(15 * (attempt + 1))
        raise AssertionError("unreachable")


def _entry_arity(source: str) -> int:
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    if not functions:
        raise ValueError("PUT has no top-level function")
    return len(functions[-1].args.args)


def run(args: argparse.Namespace, llm: Any | None = None) -> dict[str, int]:
    artifact = Path(args.artifact)
    root = artifact / "Datasets" / "EvalPlus"
    if args.artifact_commit != ARTIFACT_COMMIT:
        raise ValueError(f"Unverified TrickCatcher artifact commit: {args.artifact_commit}")
    system_template, user_template = read_original_templates(root / "PromptTemplates")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    external_plans: dict[int, str] = {}
    if args.arm in {"reference_concept", "shuffled_concept"}:
        if not args.plan_file:
            raise SystemExit("--plan-file is required for external concept cards")
        with Path(args.plan_file).open() as handle:
            for line in handle:
                row = json.loads(line)
                if row.get("plan"):
                    external_plans[row["task_num"]] = row["plan"]
    elif args.plan_file:
        raise SystemExit("--plan-file applies only to external concept-card arms")
    completed: set[int] = set()
    if args.resume and output.exists():
        with output.open() as handle:
            for line in handle:
                row = json.loads(line)
                if row.get("raw_response"):
                    completed.add(row["task_num"])
    if llm is None and not args.dry_run:
        llm = make_llm(temperature=0, timeout=args.request_timeout, max_retries=0, max_tokens=args.max_output_tokens)
    if llm is None and not args.dry_run:
        raise SystemExit("LLM provider is not configured")
    invoke = _Invoker(llm, args.request_delay, args.retries) if llm is not None else None
    written = errors = 0
    with output.open("a" if args.resume else "w") as destination:
        for task_num in range(args.start, args.start + args.limit):
            if task_num in completed:
                continue
            source_file = root / "PUTs" / f"HumanEval_{task_num}" / "put0.py"
            if not source_file.is_file():
                continue
            if args.arm == "shuffled_concept" and task_num not in external_plans:
                continue
            source = source_file.read_text()
            arity = _entry_arity(source)
            plan = external_plans.get(task_num, "")
            static_rules: list[str] = []
            plan_system = CONCEPT_SYSTEM if args.arm == "concept" else GENERIC_SYSTEM
            if args.arm == "reference_concept" and not plan:
                plan_error = "missing private concept card"
            elif args.arm == "static_concept":
                plan, static_rules = static_concept(source)
                plan_error = ""
            elif args.arm not in {"baseline", "reference_concept"} and not args.dry_run:
                try:
                    plan = invoke(plan_system, source)  # type: ignore[misc]
                except Exception as exc:
                    plan = ""
                    plan_error = f"{type(exc).__name__}: {exc}"
                else:
                    plan_error = ""
            else:
                plan_error = ""
            system, user = build_input_messages(source, system_template, user_template, args.arm, plan)
            row = {
                "task_num": task_num, "arm": args.arm, "model": model_id(),
                "artifact_commit": args.artifact_commit,
                "paper_baseline": "TrickCatcher EvalPlus direct-input prompt",
                "prompt_lineage": "verbatim_original" if args.arm == "baseline" else "concept_or_plan_extension",
                "original_template_sha256": TEMPLATE_SHA256,
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "arity": arity, "plan": plan, "plan_error": plan_error,
                "static_rules": static_rules,
                "system_prompt_sha256": hashlib.sha256(system.encode()).hexdigest(),
                "user_prompt": user, "raw_response": "", "inputs": [], "error": "",
            }
            if plan_error == "missing private concept card":
                row["error"] = plan_error
                errors += 1
            elif not args.dry_run:
                try:
                    row["raw_response"] = invoke(system, user)  # type: ignore[misc]
                    row["inputs"] = parse_inputs(row["raw_response"], arity)
                except Exception as exc:
                    row["error"] = f"{type(exc).__name__}: {exc}"
                    errors += 1
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
            destination.flush()
            written += 1
            print(f"task={task_num} arm={args.arm} inputs={len(row['inputs'])} error={bool(row['error'])}", flush=True)
    return {"written": written, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default="/tmp/TrickCatcher-upstream")
    parser.add_argument("--artifact-commit", default=ARTIFACT_COMMIT)
    parser.add_argument("--arm", choices=("baseline", "generic", "concept", "static_concept", "reference_concept", "shuffled_concept"), required=True)
    parser.add_argument("--plan-file", help="Reference-informed cards; only for the leaky ceiling arm")
    parser.add_argument("--out", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--request-timeout", type=float, default=60)
    parser.add_argument("--max-output-tokens", type=int, default=1200)
    parser.add_argument("--request-delay", type=float, default=3)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    print(json.dumps(run(parser.parse_args())))


if __name__ == "__main__":
    main()
