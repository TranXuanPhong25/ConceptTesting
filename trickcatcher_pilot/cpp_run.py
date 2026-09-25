"""TrickCatcher C++ direct-input prompt with optional ConceptCoder VD card."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from magma.llm_client import make_llm, model_id
from trickcatcher_pilot.prompt_provenance import ARTIFACT_COMMIT
from trickcatcher_pilot.run import _response_text


DIRECT_PROMPT_SHA256 = "26d075a69cc99a00b7ddd6095634cdc0468fcc54c6a7b09bc6f4a87498f2832b"


def parse_inputs(raw: str) -> list[str]:
    """Parse at most ten INPUTn sections without changing their stdin content."""
    result: dict[int, list[str]] = {}
    current: int | None = None
    for line in raw.splitlines():
        match = re.match(r"^\s*INPUT\s*(\d+)\s*:\s*(.*)$", line, re.I)
        if match:
            number = int(match.group(1))
            current = number if 1 <= number <= 10 and number not in result else None
            if current is not None:
                result[current] = [match.group(2)] if match.group(2) else []
        elif current is not None and line.strip() not in {"```", "```text"}:
            result[current].append(line)
    return ["\n".join(result[i]).strip() + "\n" for i in sorted(result) if "\n".join(result[i]).strip()]


def concept_block(statements: list[dict[str, Any]]) -> str:
    lines = ["\n\nStatement-level code concepts (ConceptCoder VD annotator; use these source facts when choosing valid test inputs):"]
    for item in statements:
        lines.append(f"- L{item['line']} [{', '.join(item['labels'])}]: {item['source']}")
    return "\n".join(lines)


def build_prompt(template: str, description: str, code: str, statements: list[dict[str, Any]] | None = None) -> str:
    prompt = template.replace("{pro_des}", description).replace("{code}", code)
    return prompt + (concept_block(statements) if statements else "")


def run(args: argparse.Namespace, llm: Any | None = None) -> dict[str, int]:
    root = Path(args.artifact) / "Datasets" / "TrickyBugs"
    template_bytes = (root / "PromptTemplates" / "geninput_direct").read_bytes()
    digest = hashlib.sha256(template_bytes).hexdigest()
    if digest != DIRECT_PROMPT_SHA256 or args.artifact_commit != ARTIFACT_COMMIT:
        raise ValueError("TrickCatcher C++ original prompt or artifact revision does not match the pinned source")
    template = template_bytes.decode("utf-8")
    cards = [json.loads(line) for line in Path(args.cards).read_text().splitlines() if line.strip()]
    completed = set()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.resume and output.exists():
        completed = {
            row["problem_id"] for line in output.read_text().splitlines() if line.strip()
            for row in [json.loads(line)] if row.get("raw_response")
        }
    if llm is None:
        llm = make_llm(temperature=0, timeout=90, max_retries=0, max_tokens=args.max_tokens)
    if llm is None:
        raise RuntimeError("Gemini/Vertex provider is not configured")
    written = errors = 0
    with output.open("a" if args.resume else "w") as destination:
        for card in cards:
            pid = card["problem_id"]
            if pid in completed:
                continue
            source = (root / "PUT_cpp" / pid / card["put_name"]).read_text(errors="replace")
            source_hash = hashlib.sha256(source.encode()).hexdigest()
            if source_hash != card["source_sha256"]:
                raise ValueError(f"source changed for {pid}")
            description = (Path(args.problems) / pid / "problem_description.txt").read_text(errors="replace")
            statements = card["statements"] if args.arm == "concept" else None
            prompt = build_prompt(template, description, source, statements)
            row = {
                "problem_id": pid, "put_name": card["put_name"], "arm": args.arm,
                "model": model_id(), "artifact_commit": ARTIFACT_COMMIT,
                "paper_prompt_sha256": digest,
                "prompt_lineage": "verbatim_original" if args.arm == "baseline" else "concept_extension",
                "concept_annotator": card["annotator"] if statements else None,
                "source_sha256": source_hash,
                "description_sha256": hashlib.sha256(description.encode()).hexdigest(),
                "prompt": prompt, "raw_response": "", "inputs": [], "error": "",
            }
            try:
                for attempt in range(args.retries + 1):
                    try:
                        response = llm.invoke([HumanMessage(content=prompt)])
                        row["raw_response"] = _response_text(getattr(response, "content", response)).strip()
                        if not row["raw_response"]:
                            raise ValueError("empty response")
                        break
                    except Exception as exc:
                        transient = any(token in str(exc) for token in ("429", "504", "ResourceExhausted", "DeadlineExceeded"))
                        if attempt >= args.retries or not transient:
                            raise
                        time.sleep(15 * (attempt + 1))
                row["inputs"] = parse_inputs(row["raw_response"])
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
                errors += 1
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
            destination.flush()
            written += 1
            print(f"{pid} {args.arm} inputs={len(row['inputs'])} error={bool(row['error'])}", flush=True)
            time.sleep(args.delay)
    return {"written": written, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default="/tmp/TrickCatcher-upstream")
    parser.add_argument("--artifact-commit", default=ARTIFACT_COMMIT)
    parser.add_argument("--problems", default="/tmp/TrickyBugs-selected/problems")
    parser.add_argument("--cards", required=True)
    parser.add_argument("--arm", choices=("baseline", "concept"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-tokens", type=int, default=1600)
    parser.add_argument("--delay", type=float, default=5)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    print(json.dumps(run(parser.parse_args())))


if __name__ == "__main__":
    main()
