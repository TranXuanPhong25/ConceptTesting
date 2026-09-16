#!/usr/bin/env python3
"""Run a quick bench ablation for the TEstEval-style concept prompt.

Example:
  LLM_PROVIDER=router ROUTER_API_KEY=... CONDS=bench_concept_en,concept_testeval_en \
    .venv/bin/python -m concept_annotator.experiment
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))

import common  # type: ignore  # noqa: E402
from lab import generate, load_cache, report  # type: ignore  # noqa: E402
from prompts import BUILD as BASE_BUILD  # type: ignore  # noqa: E402
from prompts import _harness_note_en  # type: ignore  # noqa: E402

from .annotator import annotate_function, render_prompt_block


def build_concept_testeval_en(item: dict) -> list[dict[str, str]]:
    func = item["func_vuln"]
    ann = annotate_function(func, item.get("lines_concept"))
    fn = common.focal(func) or item.get("focal") or "focal"
    user = (
        "Function under test:\n```c\n%s\n```\n\n"
        "%s\n\n"
        "REQUIREMENTS:\n"
        "- First satisfy the target line/branch/path goals above.\n"
        "- Then craft the malicious input that triggers the sanitizer oracle.\n"
        "- Write one plain C `int main()` that calls `%s(...)`.\n"
        "- Return ONLY a single ```c ... ``` block."
        % (func, render_prompt_block(ann), fn)
    )
    user += _harness_note_en(item, fn)
    return [
        {
            "role": "system",
            "content": "You are a C/C++ security test engineer using static concept coverage targets.",
        },
        {"role": "user", "content": user},
    ]


def main() -> None:
    gold = os.environ.get("GOLD", os.path.join(ROOT, "bench", "items", "gold_juliet.jsonl"))
    cache_path = os.environ.get("CONCEPT_ANNOTATOR_CACHE", os.path.join(ROOT, "concept_annotator", "cache.jsonl"))
    cond_names = [x for x in os.environ.get("CONDS", "bench_concept_en,concept_testeval_en").split(",") if x]
    conds = {}
    for name in cond_names:
        if name == "concept_testeval_en":
            conds[name] = build_concept_testeval_en
        else:
            conds[name] = BASE_BUILD[name]

    items = [json.loads(line) for line in open(gold) if line.strip()]
    if os.environ.get("GENERATE", "1") == "1":
        cache = generate(items, conds, cache_path)
    else:
        cache = load_cache(cache_path)
    pairs = [("concept_testeval_en", "bench_concept_en")] if set(conds) >= {"concept_testeval_en", "bench_concept_en"} else []
    report(items, conds, cache, mcnemar_pairs=pairs)


if __name__ == "__main__":
    main()
