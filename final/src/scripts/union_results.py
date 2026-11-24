"""Pure union script: aggregate saved evaluation results across arms/runs with 0 LLM & 0 sandbox calls.

Run from repo root:
    PYTHONPATH=. final/.venv/bin/python -m final.src.scripts.union_results \
        --sources final/out/run_a final/out/run_b --per-task
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from final.src.scripts._formatting import (
    collect_run_results,
    render_arm_union_tables,
    render_banner,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        type=Path,
        nargs="+",
        required=True,
        help="One or more evaluation run directories containing tasks/*/result.json",
    )
    parser.add_argument("--arms", nargs="+", help="Optional subset of arm names to include in the union")
    parser.add_argument("--task-ids", nargs="+", help="Optional subset of full task IDs to include")
    parser.add_argument("--per-task", action="store_true", help="Also print per-task breakdown table")
    parser.add_argument("--export-json", type=Path, help="Optional path to save union summary JSON")
    return parser


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)

    stats = collect_run_results(
        options.sources,
        arms=options.arms,
        task_ids=options.task_ids,
    )
    print(render_banner("Pure Union of Saved Evaluation Results"))
    print("Sources:")
    for source in stats["sources"]:
        print(f"  - {source}")
    print(
        f"Tasks: {stats['eligible_tasks']} eligible / {stats['scored_tasks']} scored "
        f"(skipped: {len(stats['skipped_tasks'])}) | Eligible PUTs: {stats['eligible_puts']}\n"
    )
    print(render_arm_union_tables(stats, show_per_task=options.per_task, show_gain=True))

    if options.export_json is not None:
        options.export_json.parent.mkdir(parents=True, exist_ok=True)
        options.export_json.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n")
        print(f"\nExported union JSON to: {options.export_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
