"""Reference-informed concept cards: an intentionally leaky *ceiling* experiment.

The output cards may be shown to a generator only in the upper-bound arm.
They must never be mistaken for concepts available in real bug discovery.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from magma.llm_client import make_llm, model_id
from trickcatcher_pilot.run import _Invoker


SYSTEM = (
    "You see a buggy Python program and a correct reference implementation. "
    "Distill their semantic difference into exactly one JSON object with string "
    "fields expected_property, suspected_shortcut, and separating_input_relation. "
    "Identify an actual shortcut in the buggy code and a valid input relation "
    "that would make outputs differ. Do not quote or reveal the reference code, "
    "specific output values, or concrete test inputs. This is an upper-bound "
    "research diagnostic, not a deployable bug detector."
)


def run(args: argparse.Namespace, llm: Any | None = None) -> dict[str, int]:
    references = {
        row["task_num"]: row
        for row in (json.loads(line) for line in Path(args.references).read_text().splitlines() if line.strip())
    }
    if llm is None:
        llm = make_llm(temperature=0, timeout=args.request_timeout, max_retries=0, max_tokens=args.max_output_tokens)
    if llm is None:
        raise SystemExit("LLM provider is not configured")
    invoke = _Invoker(llm, args.request_delay, args.retries)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    completed: set[int] = set()
    if args.resume and output.exists():
        completed = {
            row["task_num"] for row in (json.loads(line) for line in output.read_text().splitlines() if line.strip())
            if row.get("plan")
        }
    written = errors = 0
    with output.open("a" if args.resume else "w") as handle:
        for task_num in range(args.start, args.start + args.limit):
            source_path = Path(args.artifact) / "Datasets" / "EvalPlus" / "PUTs" / f"HumanEval_{task_num}" / "put0.py"
            if not source_path.is_file() or task_num in completed:
                continue
            reference = references[task_num]["canonical_source"]
            source = source_path.read_text()
            user = f"Buggy program:\n```python\n{source}\n```\n\nCorrect reference:\n```python\n{reference}\n```"
            row = {"task_num": task_num, "model": model_id(), "plan": "", "error": ""}
            try:
                row["plan"] = invoke(SYSTEM, user)
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
                errors += 1
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            written += 1
            print(f"task={task_num} reference_concept error={bool(row['error'])}", flush=True)
    return {"written": written, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", required=True, help="PRIVATE exported canonical JSONL")
    parser.add_argument("--artifact", default="/tmp/TrickCatcher-upstream")
    parser.add_argument("--out", required=True)
    parser.add_argument("--start", type=int, default=13)
    parser.add_argument("--limit", type=int, default=13)
    parser.add_argument("--request-timeout", type=float, default=60)
    parser.add_argument("--max-output-tokens", type=int, default=700)
    parser.add_argument("--request-delay", type=float, default=3)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--resume", action="store_true")
    print(json.dumps(run(parser.parse_args())))


if __name__ == "__main__":
    main()
