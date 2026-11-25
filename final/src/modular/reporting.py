"""Task-clustered comparison and report rendering, with descriptive intermediate names."""
import hashlib
import random

import numpy
from scipy.stats import binomtest, permutation_test

from .cohort import call_usage


class Reporter:
    """Aggregate per-task evaluation results, compare arms, and render markdown reports."""

    @staticmethod
    def summarize_saved(artifacts, task_ids=None):
        """Aggregate recorded verdicts without constructing generation or execution jobs."""
        summary = artifacts.read("modular_summary.json") if artifacts.exists("modular_summary.json") else {}
        rows = [
            artifacts.read(str(path.relative_to(artifacts.directory)))
            for path in sorted(artifacts.directory.glob("tasks/*/result.json"))
        ]
        if task_ids is not None:
            requested = set(task_ids)
            selected = [row for row in rows if row["task_id"] in requested]
            missing = requested - {row["task_id"] for row in selected}
            if missing:
                raise FileNotFoundError("Missing saved task results: " + ", ".join(sorted(missing)))
            if len(selected) != len(rows):
                summary = {}
            rows = selected
        if not rows:
            raise FileNotFoundError("No saved task evaluation results")
        summary.update(Reporter.result_counts(rows))
        return summary

    @staticmethod
    def result_counts(rows):
        totals = {}
        eligible_puts = 0
        tested_puts = 0
        for row in rows:
            if row.get("skip"):
                continue
            base_pass = row["base_pass"]
            eligible_puts += base_pass
            if any(arm["valid_inputs"] for arm in row["arms"].values()):
                tested_puts += base_pass
            for name, arm in row["arms"].items():
                total = totals.setdefault(name, {
                    "valid_inputs": 0, "detected": 0, "tasks_detected": 0, "tested_base_pass": 0,
                })
                valid_inputs = arm["valid_inputs"]
                total["valid_inputs"] += valid_inputs
                if valid_inputs:
                    total["tested_base_pass"] += base_pass
                total["detected"] += len(arm["detected_put_ids"])
                total["tasks_detected"] += bool(arm["detected_put_ids"])
        return {
            "scored_tasks": len(rows),
            "arms": totals,
            # Historical field name for the eligible PUT denominator.
            "evaluated_base_pass": eligible_puts,
            "tested_base_pass": tested_puts,
        }

    def build_summary(self, contexts, cohort):
        rows = [context.result for context in contexts]
        summary = {
            **self.result_counts(rows),
            "expected_tasks": len(contexts),
            "generated": sum(task["generated"] for task in cohort["tasks"]),
            "base_pass": sum(task["base_pass"] for task in cohort["tasks"]),
            "comparisons": [],
            "skips": [{"task_id": row["task_id"], "reason": row["skip"]} for row in rows if row.get("skip")],
        }
        artifacts = contexts[0].artifacts
        summary["writer_calls"] = cohort.get("generation_usage", {})
        summary["tester_calls"] = call_usage(artifacts.directory)
        summary["diagnostics"] = self.collect_diagnostics(contexts)
        observers = []
        for record_path in (artifacts.directory / "keepalive").glob("*.json"):
            observers.append(artifacts.read(str(record_path.relative_to(artifacts.directory))))
        observer_totals = {
            "attempts": len(observers),
            "received": 0,
            "unknown": 0,
            "known_total_tokens": 0,
            "not_sent": 0,
            "unknown_completions": 0,
        }
        for observer in observers:
            observer_totals["received"] += observer["state"] == "received"
            observer_totals["not_sent"] += observer["state"] == "not_sent"
            if observer["state"] not in ("received", "not_sent"):
                observer_totals["unknown"] += 1
                observer_totals["unknown_completions"] += bool(observer.get("completion_started", True))
            observer_totals["known_total_tokens"] += observer.get("usage", {}).get("total_tokens", 0)
        summary["keepalive_calls"] = observer_totals
        missing_footer_count = 0
        for response_path in (artifacts.directory / "tasks").glob("*/calls/*/response.json"):
            response = artifacts.read(str(response_path.relative_to(artifacts.directory)))
            if response.get("usage", {}).get("usage_footer_complete") is False:
                missing_footer_count += 1
        summary["responses_with_missing_usage_footer"] = missing_footer_count
        cache_receipts = [
            receipt
            for context in contexts
            for receipt in context.extensions.get("input_execution_cache", {}).values()
        ]
        if cache_receipts:
            summary["input_execution_cache"] = self.cache_accounting(cache_receipts)
        return summary

    @staticmethod
    def cache_accounting(receipts):
        summary = {
            "input_records": 0,
            "hits": 0,
            "misses": 0,
            "executed_inputs": 0,
            "not_cached": 0,
            "corrupt_entries": 0,
            "missing_receipts": 0,
        }
        for receipt in receipts:
            for name in summary:
                if name != "missing_receipts":
                    summary[name] += receipt.get(name, 0)
            summary["missing_receipts"] += receipt.get("state") == "receipt_missing"
        return summary

    def collect_diagnostics(self, contexts):
        diagnostics = {"visible_puts": 0, "generation_rejections": {}, "oracle_rejections": {}}
        for context in contexts:
            packet = context.packet or {}
            if context.inputs.get("skip"):
                continue
            diagnostics["visible_puts"] += len(packet.get("visible_put_ids", []))
            for arm_name, arm_record in context.inputs["arms"].items():
                for rejection in arm_record.get("rejected", []):
                    self.increment(diagnostics["generation_rejections"], f"{arm_name}:{rejection['reason']}")
            for rejection in context.oracle["rejected"]:
                self.increment(diagnostics["oracle_rejections"], rejection["reason"])
        return diagnostics

    @staticmethod
    def increment(counters, category):
        counters[category] = counters.get(category, 0) + 1

    def render(self, summary):
        lines = [
            "# Fixed-program input-generation benchmark, reference-program oracle",
            "",
            f"Đã ghi {summary['scored_tasks']}/{summary['expected_tasks']} task records. "
            f"Có {summary['generated']} PUT đã sinh, {summary['base_pass']} PUT vượt base test "
            f"và {summary['tested_base_pass']}/{summary['evaluated_base_pass']} PUT đủ điều kiện đã nhận test bổ sung.",
            "",
            "| Arm | Novel valid inputs | PUT đã nhận test bổ sung | PUT phát hiện sai khác | Task có phát hiện |",
            "|---|---:|---:|---:|---:|",
        ]
        for arm_name, totals in summary["arms"].items():
            lines.append(
                f"| {arm_name} | {totals['valid_inputs']} | {totals['tested_base_pass']} | "
                f"{totals['detected']} | {totals['tasks_detected']} |"
            )
        lines.append("")
        for comparison in summary["comparisons"]:
            lines.append(
                f"- {comparison['left']} vs {comparison['right']}: macro detected fraction "
                f"{comparison['left_macro_fraction']} vs {comparison['right_macro_fraction']}; "
                f"paired p={comparison['paired_permutation_pvalue']:.5g}; "
                f"tasks with more detections {comparison['tasks_left_more']}–{comparison['tasks_right_more']}."
            )
        lines.extend([
            "",
            f"Writer accounting (shared frozen-cohort cost): {summary['writer_calls']}.",
            f"Tester accounting: {summary['tester_calls']}.",
            f"Diagnostics: {summary['diagnostics']}.",
            f"Explicit skips: {summary['skips']}.",
        ])
        if "input_execution_cache" in summary:
            lines.extend(["", f"Per-input execution cache: {summary['input_execution_cache']}."])
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def detected_count(result, selected_indices):
        selected_set = set(selected_indices)
        detected_programs = 0
        for outcome in result["outcomes"].values():
            if selected_set.intersection(outcome["failing"]):
                detected_programs += 1
        return detected_programs

    def compare(self, rows, left_arm, right_arm):
        left_rates = []
        right_rates = []
        matched_rows = []
        for result in rows:
            if result.get("skip"):
                continue
            left_indices = result["arm_indices"][left_arm]
            right_indices = result["arm_indices"][right_arm]
            matched_count = min(len(left_indices), len(right_indices))
            seed_text = f"{result['task_id']}:{left_arm}:{right_arm}"
            seed_value = int(hashlib.sha256(seed_text.encode()).hexdigest()[:16], 16)
            random_generator = random.Random(seed_value)
            left_detected = self.detected_count(result, random_generator.sample(left_indices, matched_count))
            right_detected = self.detected_count(result, random_generator.sample(right_indices, matched_count))
            left_rates.append(left_detected / result["base_pass"])
            right_rates.append(right_detected / result["base_pass"])
            left_repeated_total = 0
            right_repeated_total = 0
            for _ in range(100):
                left_repeated_total += self.detected_count(result, random_generator.sample(left_indices, matched_count))
                right_repeated_total += self.detected_count(result, random_generator.sample(right_indices, matched_count))
            matched_rows.append({
                "task_id": result["task_id"],
                "inputs_each": matched_count,
                "left": left_detected,
                "right": right_detected,
                "mean_left_100": left_repeated_total / 100,
                "mean_right_100": right_repeated_total / 100,
            })
        left_array = numpy.array(left_rates)
        right_array = numpy.array(right_rates)
        if len(left_array) >= 2 and numpy.any(left_array != right_array):
            test = permutation_test(
                (left_array, right_array),
                self.mean_paired_difference,
                permutation_type="samples",
                vectorized=True,
                n_resamples=10000,
                alternative="two-sided",
                rng=numpy.random.default_rng(20261030),
            )
            permutation_probability = float(test.pvalue)
        else:
            permutation_probability = 1.0
        left_wins = 0
        right_wins = 0
        zero_budget_tasks = 0
        for matched_result in matched_rows:
            left_wins += matched_result["left"] > matched_result["right"]
            right_wins += matched_result["left"] < matched_result["right"]
            zero_budget_tasks += matched_result["inputs_each"] == 0
        sign_probability = float(binomtest(left_wins, left_wins + right_wins).pvalue) if left_wins + right_wins else 1.0
        return {
            "left": left_arm,
            "right": right_arm,
            "task_count": len(left_array),
            "left_macro_fraction": float(left_array.mean()) if len(left_array) else None,
            "right_macro_fraction": float(right_array.mean()) if len(right_array) else None,
            "paired_permutation_pvalue": permutation_probability,
            "tasks_left_more": left_wins,
            "tasks_right_more": right_wins,
            "directional_sign_pvalue": sign_probability,
            "rows": matched_rows,
            "zero_valid_budget_tasks": zero_budget_tasks,
        }

    @staticmethod
    def mean_paired_difference(left_values, right_values, axis):
        return numpy.mean(left_values - right_values, axis=axis)
