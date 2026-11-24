"""Shared terminal table formatting, dataset selection, and result union helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

from final.src.benchmarks.datasets import DatasetLoader
from final.src.benchmarks.pipeline import adapter_task


def format_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    alignments: Sequence[str] | None = None,
) -> str:
    """Render a clean ASCII table for terminal output."""
    str_headers = [str(header) for header in headers]
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(header) for header in str_headers]
    for row in str_rows:
        for index, cell in enumerate(row):
            if index < len(widths):
                widths[index] = max(widths[index], len(cell))
    aligns = list(alignments) if alignments is not None else ["<"] * len(str_headers)

    def _fmt(cells: Sequence[str]) -> str:
        parts = []
        for index, cell in enumerate(cells):
            align = aligns[index] if index < len(aligns) else "<"
            parts.append(f" {cell:{align}{widths[index]}} ")
        return "|" + "|".join(parts) + "|"

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border, _fmt(str_headers), border]
    for row in str_rows:
        if len(row) == 1 and row[0] == "---":
            lines.append(border)
        else:
            lines.append(_fmt(row))
    lines.append(border)
    return "\n".join(lines)


def render_banner(title: str, width: int = 78) -> str:
    bar = "=" * max(width, len(title) + 4)
    return f"\n{bar}\n  {title}\n{bar}"


def format_rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "n/a"
    return f"{(100.0 * numerator / denominator):.1f}%"


def load_dataset_bundle(dataset_type: str):
    """Load (DatasetLoader, tasks, metadata) for he-py or mbpp-py."""
    dataset = DatasetLoader(dataset_type)
    tasks = dataset.load_tasks()
    if dataset.config == "he-py":
        metadata = dataset.load_metadata()
    else:
        tasks = [adapter_task(task) for task in tasks]
        metadata = {task["task_id"]: {"contract": "", "atol": 0} for task in tasks}
    return dataset, tasks, metadata


def select_tasks(
    tasks: Sequence[dict],
    *,
    task_ids: Sequence[str] | None = None,
    num_tasks: int | None = None,
) -> list[dict]:
    """Select tasks by full ID / trailing number or first N tasks."""
    if task_ids:
        by_id = {task["task_id"]: task for task in tasks}
        by_number = {task["task_id"].rsplit("/", 1)[-1]: task["task_id"] for task in tasks}
        selected_ids = [by_number.get(identifier, identifier) for identifier in task_ids]
        if len(set(selected_ids)) != len(selected_ids):
            raise ValueError("Duplicate task IDs in selection")
        missing = [identifier for identifier in selected_ids if identifier not in by_id]
        if missing:
            raise ValueError("Unknown task IDs: " + ", ".join(missing))
        return [by_id[identifier] for identifier in selected_ids]
    if num_tasks is not None:
        if num_tasks < 1:
            raise ValueError("num_tasks must be >= 1")
        if num_tasks > len(tasks):
            raise ValueError(f"num_tasks ({num_tasks}) exceeds available tasks ({len(tasks)})")
        return list(tasks[:num_tasks])
    return list(tasks)


def collect_run_results(
    sources: Sequence[Path | str],
    *,
    arms: Sequence[str] | None = None,
    task_ids: Sequence[str] | None = None,
) -> dict:
    """Aggregate per-arm evaluation results and their UNION across one or more run directories.

    Never executes models or sandboxed programs; reads saved tasks/*/result.json only.
    """
    source_paths = [Path(source).resolve() for source in sources]
    if not source_paths:
        raise ValueError("At least one source directory is required")

    requested_arms = set(arms) if arms else None
    requested_tasks = set(task_ids) if task_ids else None

    per_task: dict[str, dict] = {}
    arm_order: list[str] = []

    for source in source_paths:
        result_files = sorted(source.glob("tasks/*/result.json"))
        if not result_files:
            raise FileNotFoundError(f"No saved tasks/*/result.json found in {source}")
        for result_path in result_files:
            row = json.loads(result_path.read_text())
            task_id = row["task_id"]
            if requested_tasks is not None and task_id not in requested_tasks:
                continue
            entry = per_task.setdefault(
                task_id,
                {
                    "task_id": task_id,
                    "skip": row.get("skip"),
                    "base_pass": 0 if row.get("skip") else int(row.get("base_pass", 0)),
                    "arms": {},
                },
            )
            if row.get("skip"):
                continue
            entry["skip"] = None
            base_pass = int(row.get("base_pass", 0))
            if entry["base_pass"] and entry["base_pass"] != base_pass:
                raise ValueError(
                    f"Inconsistent base_pass for {task_id}: {entry['base_pass']} vs {base_pass}"
                )
            entry["base_pass"] = base_pass
            for arm_name, arm_data in row.get("arms", {}).items():
                if requested_arms is not None and arm_name not in requested_arms:
                    continue
                if arm_name in entry["arms"]:
                    raise ValueError(
                        f"Duplicate arm '{arm_name}' for task {task_id} across source directories"
                    )
                if arm_name not in arm_order:
                    arm_order.append(arm_name)
                detected_ids = sorted(
                    {str(put_id) for put_id in arm_data.get("detected_put_ids", [])}
                )
                entry["arms"][arm_name] = {
                    "valid_inputs": int(arm_data.get("valid_inputs", 0)),
                    "detected": len(detected_ids),
                    "detected_put_ids": detected_ids,
                }

    if not per_task:
        raise ValueError("No matching task results found for the requested filters")

    if requested_arms is not None:
        missing_arms = sorted(requested_arms - set(arm_order))
        if missing_arms:
            raise ValueError("Requested arms not found in saved results: " + ", ".join(missing_arms))

    # Sort tasks numerically when task_id ends with /<int>.
    def _task_sort_key(task_id: str):
        prefix, _, suffix = task_id.rpartition("/")
        return (prefix, int(suffix) if suffix.isdigit() else -1, task_id)

    ordered_task_ids = sorted(per_task, key=_task_sort_key)

    eligible_tasks = 0
    eligible_puts = 0
    skipped_tasks: list[str] = []
    arm_totals = {
        name: {
            "valid_inputs": 0,
            "detected_keys": set(),
            "tasks_detected": 0,
            "tasks_present": 0,
        }
        for name in arm_order
    }
    union_keys: set[tuple[str, str]] = set()
    union_tasks_detected = 0
    per_task_rows: list[dict] = []

    for task_id in ordered_task_ids:
        entry = per_task[task_id]
        if entry["skip"]:
            skipped_tasks.append(task_id)
            continue
        eligible_tasks += 1
        eligible_puts += entry["base_pass"]
        task_union: set[str] = set()
        task_arm_counts: dict[str, int] = {}
        for arm_name in arm_order:
            arm_data = entry["arms"].get(arm_name)
            if arm_data is None:
                continue
            totals = arm_totals[arm_name]
            totals["valid_inputs"] += arm_data["valid_inputs"]
            totals["tasks_present"] += 1
            for put_id in arm_data["detected_put_ids"]:
                totals["detected_keys"].add((task_id, put_id))
                union_keys.add((task_id, put_id))
                task_union.add(put_id)
            if arm_data["detected_put_ids"]:
                totals["tasks_detected"] += 1
            task_arm_counts[arm_name] = len(arm_data["detected_put_ids"])
        if task_union:
            union_tasks_detected += 1
        per_task_rows.append(
            {
                "task_id": task_id,
                "base_pass": entry["base_pass"],
                "arms": task_arm_counts,
                "union_detected": len(task_union),
                "union_put_ids": sorted(task_union),
            }
        )

    arms_summary: dict[str, dict] = {}
    pairwise_gain: list[dict] = []
    for arm_name in arm_order:
        totals = arm_totals[arm_name]
        other_keys: set[tuple[str, str]] = set()
        for other_name in arm_order:
            if other_name != arm_name:
                other_keys |= arm_totals[other_name]["detected_keys"]
        unique_only = totals["detected_keys"] - other_keys
        detected_count = len(totals["detected_keys"])
        gain = len(union_keys - totals["detected_keys"])
        arms_summary[arm_name] = {
            "valid_inputs": totals["valid_inputs"],
            "detected": detected_count,
            "tasks_detected": totals["tasks_detected"],
            "tasks_present": totals["tasks_present"],
            "unique_only": len(unique_only),
        }
        pairwise_gain.append(
            {
                "arm": arm_name,
                "arm_detected": detected_count,
                "union_detected": len(union_keys),
                "gain": gain,
                "unique_only": len(unique_only),
            }
        )

    return {
        "sources": [str(path) for path in source_paths],
        "arm_order": arm_order,
        "scored_tasks": len(ordered_task_ids),
        "eligible_tasks": eligible_tasks,
        "skipped_tasks": skipped_tasks,
        "eligible_puts": eligible_puts,
        "arms": arms_summary,
        "union": {
            "detected": len(union_keys),
            "tasks_detected": union_tasks_detected,
            "detected_pairs": sorted(union_keys),
        },
        "pairwise_gain": pairwise_gain,
        "per_task": per_task_rows,
    }


def render_arm_union_tables(
    stats: dict,
    *,
    show_per_task: bool = False,
    show_gain: bool = True,
) -> str:
    """Format per-arm, UNION, gain, and optional per-task tables as a string."""
    eligible_puts = stats["eligible_puts"]
    eligible_tasks = stats["eligible_tasks"]
    sections: list[str] = []

    rows = []
    for arm_name in stats["arm_order"]:
        arm = stats["arms"][arm_name]
        rows.append(
            [
                arm_name,
                arm["valid_inputs"],
                f"{arm['detected']}/{eligible_puts}",
                format_rate(arm["detected"], eligible_puts),
                f"{arm['tasks_detected']}/{eligible_tasks}",
                arm["unique_only"],
            ]
        )
    if len(stats["arm_order"]) >= 1:
        rows.append(["---"])
        union = stats["union"]
        rows.append(
            [
                "UNION",
                "-",
                f"{union['detected']}/{eligible_puts}",
                format_rate(union["detected"], eligible_puts),
                f"{union['tasks_detected']}/{eligible_tasks}",
                "-",
            ]
        )

    sections.append(
        format_table(
            ["Arm", "Valid Inputs", "Detected / Eligible PUTs", "Rate", "Tasks Detected", "Unique PUTs"],
            rows,
            alignments=["<", ">", ">", ">", ">", ">"],
        )
    )

    if show_gain and len(stats["arm_order"]) > 1:
        gain_rows = [
            [
                item["arm"],
                f"{item['arm_detected']}/{eligible_puts}",
                f"{item['union_detected']}/{eligible_puts}",
                f"+{item['gain']}",
                item["unique_only"],
            ]
            for item in stats["pairwise_gain"]
        ]
        sections.append(
            "\nUnion Gain vs Individual Arms:\n"
            + format_table(
                ["Arm", "Arm Detected", "Union Detected", "Union Gain", "Unique-Only by Arm"],
                gain_rows,
                alignments=["<", ">", ">", ">", ">"],
            )
        )

    if show_per_task and stats["per_task"]:
        arm_order = stats["arm_order"]
        headers = ["Task ID", "Eligible PUTs", *arm_order, "UNION"]
        aligns = ["<", ">", *(">" for _ in arm_order), ">"]
        task_rows = []
        for task in stats["per_task"]:
            task_rows.append(
                [
                    task["task_id"],
                    task["base_pass"],
                    *(task["arms"].get(name, "-") for name in arm_order),
                    task["union_detected"],
                ]
            )
        sections.append("\nPer-Task Breakdown:\n" + format_table(headers, task_rows, alignments=aligns))

    return "\n".join(sections)
