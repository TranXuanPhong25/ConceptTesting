"""Read frozen v85 generation artifacts; never import or execute pipeline code.

The owner may still be generating references. This audit does not read reference
outputs or scores, acquire its lock, run its driver, or modify its snapshot.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HANDOFF = ROOT / "trickcatcher_linefacts/handoffs/v85_20261029"
WORK = HANDOFF / "work"
SNAPSHOT = WORK / "snapshot"
PIPELINE = SNAPSHOT / "trickcatcher_linefacts/pipelines/v85_retrievalhybrid"
OWNER = PIPELINE / "out/humaneval/handoff_20261029"
OUT = HERE / "owner_audit"


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Reader:
    def __init__(self):
        self.hashes = {}

    def read(self, path):
        data = path.read_bytes()
        self.hashes[str(path.relative_to(ROOT))] = digest(data)
        return data

    def json(self, path):
        return json.loads(self.read(path))


def assertion_call(text):
    """Normalize only the syntactic call; do not evaluate an assertion or args."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assert):
        return None
    test = tree.body[0].test
    if isinstance(test, ast.Compare) and isinstance(test.left, ast.Call):
        return ast.dump(test.left, include_attributes=False)
    return None


def call_key(text):
    try:
        return ast.dump(ast.parse(text, mode="eval").body, include_attributes=False)
    except SyntaxError:
        return None


def span_record(source, target):
    evidence = target["retrieval_evidence"]
    start, end = evidence["line"], evidence.get("end_line", evidence["line"])
    lines = source.splitlines()
    expression = evidence["expression"]
    # An AST expression can be normalized by ast.unparse, so literal membership
    # is only a diagnostic. A false value is not a proved bad source binding.
    nodes = ast.walk(ast.parse(source))
    matches = [n for n in nodes if getattr(n, "lineno", None) == start
               and getattr(n, "end_lineno", None) == end
               and ast.unparse(n) == expression]
    return {
        "start_line": start, "end_line": end,
        "source_lines": lines[start - 1:end],
        "expression": expression,
        "exact_ast_expression_at_span": bool(matches),
        "target_line_inside_retrieved_span": start <= target.get("line", -1) <= end,
        "mechanism_alignment": "not_established_by_line_match",
    }


def target_record(index, target, row, source):
    attempts = [a for a in row["generator_attempts"] if a["fact_index"] == index]
    selected = {r["input_repr"] for r in row["selected_inputs"]}
    final_calls = {assertion_call(a) for a in row["assertions"]} - {None}
    retained = {
        r["input_repr"] for a in attempts for r in a["selected"]
        if r["input_repr"] in selected
    }
    delivered = {
        r["input_repr"] for r in row["selected_inputs"]
        if r["input_repr"] in retained and call_key(r["call"]) in final_calls
    }
    return {
        "index": index, "concept_id": target["card_id"],
        "gate": target["retrieval_gate"], "target_kind": target["kind"],
        "card_how": target["card"]["how"], "card_trigger": target["card"]["test"],
        "tool_target_text": target["tool_target_text"],
        "source_span": span_record(source, target),
        "round1_gate_hit_count": row["round1_input_summary"]["shown_hit_counts"][index],
        "missed_after_round1": index in row["missed_fact_indices"],
        "round2_attempts": len(attempts),
        "round2_attempt_errors": [a["error"] for a in attempts if a["error"]],
        "round2_selected_before_dedup_count": sum(len(a["selected"]) for a in attempts),
        "round2_retained_input_count": len(retained),
        "round2_delivered_assertion_input_count": len(delivered),
        "oracle_correctness": "not_scored",
        "gate_hit_is_semantic_confirmation": False,
    }


def summarize_targets(rows):
    result = {}
    for gate in sorted({r["gate"] for r in rows}):
        group = [r for r in rows if r["gate"] == gate]
        result[gate] = {
            "cards": len(group),
            "round1_hit": sum(r["round1_gate_hit_count"] > 0 for r in group),
            "round1_missed": sum(r["missed_after_round1"] for r in group),
            "round2_requested": sum(r["round2_attempts"] > 0 for r in group),
            "round2_selected": sum(r["round2_selected_before_dedup_count"] > 0 for r in group),
            "round2_delivered": sum(r["round2_delivered_assertion_input_count"] > 0 for r in group),
            "target_kinds": dict(Counter(r["target_kind"] for r in group)),
        }
    return result


def audit(reader):
    manifest = reader.json(HANDOFF / "MANIFEST.json")
    archive_ok = digest(reader.read(HANDOFF / "checkpoint.tar.gz")) == manifest["archive_sha256"]
    if not archive_ok:
        raise ValueError("handoff_archive_hash_mismatch")
    mismatches = []
    # Hash imported reference bytes as opaque data for integrity only. Do not
    # parse any reference/oracle result or infer success from owner activity.
    for name, expected in manifest["files"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe_manifest_path")
        path = WORK / relative
        if not path.is_file():
            mismatches.append({"path": name, "reason": "missing"})
            continue
        data = path.read_bytes()
        if name == manifest["ledger"]["path"]:
            data = data[:manifest["ledger"]["bytes"]]
        if digest(data) != expected:
            mismatches.append({"path": name, "reason": "hash_mismatch"})
    if mismatches:
        raise ValueError("imported_manifest_mismatch: " + json.dumps(mismatches))
    freeze = reader.json(OWNER / "PREPARATION_FREEZE.json")
    for name, expected in freeze.items():
        path = OWNER / name
        if not path.resolve().is_relative_to(OWNER):
            raise ValueError("unsafe_preparation_path")
        if digest(reader.read(path)) != expected:
            raise ValueError("prepared_hash_mismatch: " + name)
    for name in ("retrieval_adapter.py", "comparison.py", "run_v4.py", "fair_generation.py"):
        reader.read(PIPELINE / name)
    reader.read(HANDOFF / "resume.py")
    reader.read(HANDOFF / "README.md")
    reader.read(HANDOFF / "DESTINATION_STATUS.md")
    # Mutable status is recorded separately; no endpoint or free-form error text.
    status = reader.json(OWNER / "STATUS.json")
    status_safe = {k: status[k] for k in ("stage", "completed", "total", "error_type") if k in status}
    v2_inputs = reader.json(ROOT / "python_bug_concepts/retrieval_v2/evaluation/inputs.json")
    sources = {int(r["task_id"].split("/")[1]): r["code"] for r in v2_inputs}
    v6 = reader.json(ROOT / "python_bug_concepts/retrieval_v6/evaluation_v6/iter06/RESULTS.json")
    v6_by_task = {int(r["task_id"].split("/")[1]): r for r in v6["records"]}
    tasks, all_targets = [], []
    for path in sorted((OWNER / "prepared").glob("*.json"), key=lambda p: int(p.stem)):
        pair = reader.json(path)
        task = pair["retrieval"]
        n = task["task"]
        if task["put"] != pair["v11"]["put"] or task["put"] != sources[n]:
            raise ValueError("source_identity_mismatch: " + str(n))
        rows = {}
        for arm in ("v11", "retrieval"):
            row = reader.json(OWNER / "generation" / arm / str(n) / "artifacts" / str(n) / "0/concept-hybrid/result.json")
            if row["task"] != n or row["arm"] != "concept-hybrid":
                raise ValueError("generation_identity_mismatch")
            rows[arm] = row
        row = rows["retrieval"]
        if len(row["round1_input_summary"]["shown_hit_counts"]) != len(task["concept_meta"]):
            raise ValueError("shown_target_length_mismatch")
        targets = [target_record(i, m, row, task["put"]) for i, m in enumerate(task["concept_meta"])]
        all_targets.extend(targets)
        balanced = v6_by_task[n]["systems"]["balanced"]
        current_pairs = [(m["card_id"], m["retrieval_evidence"]["line"]) for m in task["concept_meta"]]
        new_pairs = [(m["concept_id"], m["line"]) for m in balanced["selected"]]
        tasks.append({
            "task": n, "source_sha256": digest(task["put"].encode()),
            "source_equals_saved_v2_v6_query": True,
            "bindings": pair["bindings"], "targets": targets,
            "arms": {arm: {
                "round1_assertions": len(r["round1_assertions"]),
                "round1_gate_hit_counts": r["round1_input_summary"]["shown_hit_counts"],
                "round2_strategy_requests": r["round2_strategy_requests"],
                "round2_retained_inputs": len(r["selected_inputs"]),
                "final_assertions": len(r["assertions"]),
                "strict_missing_expected": r.get("strict_missing_expected"),
                "missed_fact_indices": r["missed_fact_indices"],
            } for arm, r in rows.items()},
            "saved_v6_comparison": {
                "current_card_sites": current_pairs, "v6_balanced_card_sites": new_pairs,
                "unchanged_ordered_card_sites": current_pairs == new_pairs,
                "new_card_sites": [p for p in new_pairs if p not in current_pairs],
                "removed_card_sites": [p for p in current_pairs if p not in new_pairs],
                "actual_rebind_performed": False,
            },
        })
    if len(tasks) != 113:
        raise ValueError("incomplete_prepared_cohort")
    pool_paths = [p for p in manifest["files"] if "/facts/" in p and "/generation/" not in p]
    return {
        "kind": "descriptive_saved_generation_audit_not_efficacy_or_final_scoring",
        "integrity": {"archive_match": archive_ok, "imported_files_verified": len(manifest["files"]),
                      "ledger_check": "imported_byte_prefix_only", "prepared_files_verified": len(freeze),
                      "generation_pairs": len(tasks), "source_identity_matches": len(tasks)},
        "owner_status_observation": status_safe,
        "handoff_complete_marker_present": (OWNER / "HANDOFF_COMPLETE.json").exists(),
        "summary": {"delivered_cards": len(all_targets), "gate_funnel": summarize_targets(all_targets),
                    "tasks_with_round2_retained_inputs": {arm: sum(t["arms"][arm]["round2_retained_inputs"] > 0 for t in tasks) for arm in ("v11", "retrieval")},
                    "same_ordered_v6_card_sites": sum(t["saved_v6_comparison"]["unchanged_ordered_card_sites"] for t in tasks)},
        "p2_rebind": {"status": "unavailable_full_tool_candidate_pool_not_in_portable_snapshot" if not pool_paths else "requires_separate_review",
                      "pool_manifest_paths": pool_paths,
                      "saved_selection_comparison_only": True,
                      "reason": "prepared holds selected v11/retrieval targets, not the full fr[facts] pool used by adapter; no native rebuilding authorized"},
        "limits": ["Round1 hit measures adapter target, not truth of the card mechanism.",
                   "Round2 delivered means syntactic assertion contains retained call; expected output has not been judged.",
                   "Same source line does not imply same expression or fault mechanism.",
                   "v6 selections are development-informed cached results, not a new retrieval run or actual rebind.",
                   "Owner status can change after this snapshot observation; no controller or reference scoring was run."],
        "tasks": tasks,
    }


def report(result):
    summary = result["summary"]
    lines = ["# V85 saved-generation owner audit", "",
             "Descriptive audit of frozen generation; no new model calls, target execution, reference execution or final scoring.", "",
             f"Verified {result['integrity']['imported_files_verified']} imported file hashes, archive, 113 prepared hashes and 113 completed generation pairs. Imported ledger prefix only; active requests are outside this audit.", "",
             "| Adapter gate | Cards | Round1 hit | Round1 missed | Round2 requested | Selected | Delivered |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for gate, s in summary["gate_funnel"].items():
        lines.append(f"| {gate} | {s['cards']} | {s['round1_hit']} | {s['round1_missed']} | {s['round2_requested']} | {s['round2_selected']} | {s['round2_delivered']} |")
    lines += ["", "Counts after the first column are card/target counts, not independent tasks. Multiple targets can deliver the same input. Delivered only checks that the retained call appears in a final assertion; it does not validate the expected output.", "",
              "The adapter joins a card to the first ranked v11 fact whose line lies in the retrieved span. When none exists it creates a STMT line-reachability gate. Round1 hits suppress round2 targeting of that card, even though reaching the line does not establish its semantic trigger.", "",
              "Manual source-based examples (illustrative, not a measured semantic error rate):", "",
              "- Task102: evidence `x % 2 == 0` is attached to the `y % 2` → `y // 2` mutant on the same line. The expressions differ; the gate tests a different operand/operator.",
              "- Task110: index-out-of-bounds card at `lst1[i]` is attached to a `%` → `//` mutant in `lst1[i] % 2`. Mutation sensitivity does not test the required out-of-range index trigger.",
              "- Task10: negative-sentinel card at literal `string[-1]` is attached to the true branch of `string[0] == string[-1]`. The saved source uses a literal last-element lookup, not a computed missing-item sentinel.", "",
              f"Saved v6 comparison: all113 query sources match byte-for-byte; {summary['same_ordered_v6_card_sites']} tasks keep the identical ordered card/site list. These are cached selection differences only. Exact rebind is unavailable: the portable snapshot omits the full original tool candidate pool. The selected prepared targets cannot reconstruct its eligibility/ranking.", "",
              "Owner status at observation: `" + json.dumps(result["owner_status_observation"], sort_keys=True) + "`. This report does not diagnose or resume the owner's controller. No final detection result is reported.", "",
              "Reproduce from repo root: `python python_bug_concepts/retrieval_v7/owner_audit.py --check` verifies the existing report/source hashes without reading changed owner status. Run without `--check` only for a first report; existing differing outputs are never overwritten.", "",
              "Machine-readable per-task/card funnel, source-span checks and saved v6 differences are in `RESULTS.json`; `SOURCE_HASHES.json` records every interpreted input plus the archive/manifest/code hashes. Integrity hashing reads imported reference bytes opaquely but never interprets their outcomes."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        hashes = json.loads((OUT / "SOURCE_HASHES.json").read_text())
        # STATUS.json is a captured observation, intentionally mutable. Preserve
        # its recorded hash while checking all stable inputs and our own report.
        mutable = str((OWNER / "STATUS.json").relative_to(ROOT))
        bad = [name for name, value in hashes["inputs"].items()
               if name != mutable and digest((ROOT / name).read_bytes()) != value]
        bad += [name for name, value in hashes["outputs"].items()
                if digest((OUT / name).read_bytes()) != value]
        if bad:
            raise ValueError("audit_hash_mismatch: " + json.dumps(bad))
        print(json.dumps({"stable_input_and_output_hashes": "pass", "mutable_owner_status": "not_rechecked"}))
        return
    reader = Reader()
    reader.read(Path(__file__).resolve())
    result = audit(reader)
    output = {"RESULTS.json": json.dumps(result, indent=2, ensure_ascii=False) + "\n", "REPORT.md": report(result)}
    output["SOURCE_HASHES.json"] = json.dumps({"inputs": dict(sorted(reader.hashes.items())),
        "outputs": {name: digest(value.encode()) for name, value in output.items()}}, indent=2) + "\n"
    OUT.mkdir(exist_ok=True)
    for name, value in output.items():
        path = OUT / name
        if path.exists() and path.read_text() != value:
            raise ValueError("refuse_to_overwrite_existing_audit: " + name)
    for name, value in output.items():
        path = OUT / name
        if not path.exists():
            path.write_text(value)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
