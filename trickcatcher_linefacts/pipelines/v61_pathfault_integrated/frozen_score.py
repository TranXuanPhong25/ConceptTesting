"""P0A raw-final scorer primitives.

The module can audit a frozen generation and label raw final entries, but it does
not know or load a reference implementation. P0B supplies a separately reviewed
evaluator after P1 routes/budgets are frozen.
"""
from __future__ import annotations

import ast
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable


ARMS = ("plain", "concept", "equal_evidence_raw", "inputs_only")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable_artifact:{path.name}") from exc


def audit_freeze(root: Path) -> dict[str, Any]:
    manifest = _load_json(root / "generation_frozen.json")
    missing, mismatches = [], []
    for rel, expected in manifest.items():
        path = root / rel
        if not path.exists():
            missing.append(rel)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            mismatches.append(rel)
    return {"entries": len(manifest), "missing": missing, "mismatches": mismatches,
            "ok": not missing and not mismatches}


def raw_final_slots(root: Path, case_ids: list[str]) -> list[dict[str, Any]]:
    """Return exactly one six-item primary slot list per case/arm.

    The source is raw `response.json`, before any replay/parser feedback. A failed
    or truncated final response still yields six explicit missing slots.
    """
    rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        for arm in ARMS:
            path = root / case_id / arm / "final" / "response.json"
            if not path.exists():
                rows.extend({"case_id": case_id, "arm": arm, "position": i,
                             "raw_status": "missing_final_slot", "raw": None} for i in range(6))
                continue
            response = _load_json(path)
            if response.get("error") is not None:
                rows.extend({"case_id": case_id, "arm": arm, "position": i,
                             "raw_status": "failed_final_slot:" + str(response["error"]), "raw": None}
                            for i in range(6))
                continue
            value = response.get("value")
            tests = value.get("tests") if isinstance(value, dict) else None
            if not isinstance(tests, list):
                rows.extend({"case_id": case_id, "arm": arm, "position": i,
                             "raw_status": "missing_tests_list", "raw": None} for i in range(6))
                continue
            for i in range(6):
                rows.append({"case_id": case_id, "arm": arm, "position": i,
                             "raw_status": "present" if i < len(tests) else "absent_test_item",
                             "raw": tests[i] if i < len(tests) else None})
    return rows


def normalize_slot(slot: dict[str, Any]) -> dict[str, Any]:
    row = dict(slot)
    raw = row.get("raw")
    if row["raw_status"] != "present":
        row["parse_status"] = row["raw_status"]
        return row
    if not isinstance(raw, dict) or not isinstance(raw.get("arguments"), str) or not isinstance(raw.get("expected"), str):
        row["parse_status"] = "malformed_test_item"
        return row
    try:
        args = ast.literal_eval(raw["arguments"])
        expected = ast.literal_eval(raw["expected"])
    except (ValueError, SyntaxError, TypeError):
        row["parse_status"] = "unparseable_literal"
        return row
    if type(args) is not tuple:
        row["parse_status"] = "arguments_not_tuple"
        return row
    row.update(parse_status="parsed", arguments=args, expected=expected,
               normalized_input=repr(args), normalized_expected=repr(expected))
    return row


def typed_key(value):
    """Type-preserving deduplication independent from assertion comparator."""
    if value is None or type(value) in (bool,int,float,str): return (type(value).__name__,repr(value))
    if type(value) in (tuple,list): return (type(value).__name__,tuple(typed_key(x) for x in value))
    if type(value) is dict: return ('dict',tuple(sorted((typed_key(k),typed_key(v)) for k,v in value.items())))
    if type(value) is set:return ('set',tuple(sorted(typed_key(x) for x in value)))
    raise ValueError('unsupported_input_topology')


def dedup_annotations(rows):
    groups={}
    for row in rows:
        if row.get('parse_status')!='parsed':continue
        key=(row['case_id'],row['arm'],typed_key(row['arguments']))
        groups.setdefault(key,[]).append(row)
    for group in groups.values():
        conflict=len({typed_key(r['expected']) for r in group})>1
        for index,row in enumerate(group):
            row['duplicate_input']=index>0
            row['conflicting_expected']=conflict
    return rows


def label_slots(slots: list[dict[str, Any]], evaluate: Callable[[str, tuple[Any, ...], Any], dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach evaluator labels. `evaluate` must return an explicit status.

    Valid statuses: confirmed, input_discrepancy_wrong_expected, passing_test,
    false_alarm, invalid_input, unresolved. The scorer never converts evaluator
    timeout/error into invalid input.
    """
    out = []
    for raw in slots:
        row = normalize_slot(raw)
        if row.get("parse_status") != "parsed":
            row["label_status"] = "unresolved_parse"
        else:
            label = evaluate(row["case_id"], row["arguments"], row["expected"])
            if not isinstance(label, dict) or label.get("status") not in {
                "confirmed", "input_discrepancy_wrong_expected", "passing_test",
                "false_alarm", "invalid_input", "unresolved",
            }:
                raise ValueError("invalid_evaluator_label")
            row["label_status"] = label["status"]
            row["evaluator"] = {k: v for k, v in label.items() if k != "status"}
        out.append(row)
    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for arm in ARMS:
        selected = [r for r in rows if r["arm"] == arm]
        labels = Counter(r.get("label_status", "unlabeled") for r in selected)
        valid=[r for r in selected if r.get('label_status') in {'confirmed','input_discrepancy_wrong_expected','passing_test','false_alarm'}]
        attack=labels['confirmed']+labels['input_discrepancy_wrong_expected']
        output_correct=labels['confirmed']+labels['passing_test']
        ratio=lambda x,n: x/n if n else None
        result[arm] = {"raw_slots": len(selected), "labels": dict(labels),
                       "parsed_slots": sum(r.get("parse_status") == "parsed" for r in selected),
                       "confirmed_slots": labels["confirmed"],
                       'tasks_total':len({r['case_id'] for r in selected}),
                       'tasks_confirmed':sorted({r['case_id'] for r in selected if r.get('label_status')=='confirmed'}),
                       'tasks_input_discrepancy':sorted({r['case_id'] for r in selected if r.get('label_status') in ('confirmed','input_discrepancy_wrong_expected')}),
                       'valid_resolved_slots':len(valid),'attack_rate_valid_resolved':ratio(attack,len(valid)),
                       'output_accuracy_valid_resolved':ratio(output_correct,len(valid)),
                       'joint_valid_resolved':ratio(labels['confirmed'],len(valid)),
                       'joint_all_raw_slots':ratio(labels['confirmed'],len(selected)),
                       'oracle_accuracy_revealing_inputs':ratio(labels['confirmed'],attack),
                       'duplicates':sum(r.get('duplicate_input',False) for r in selected),
                       'conflicting_expected_slots':sum(r.get('conflicting_expected',False) for r in selected)}
    return result
