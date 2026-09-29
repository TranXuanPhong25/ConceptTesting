"""Deterministic reconstruction of KITE's 172 method-level Defects4J tasks.

KITE (Table I) reports 172 tasks: Cli 24, Compress 32, Csv 11, JacksonDatabind 51,
Jsoup 54. It starts from 305 bugs, keeps 256 single-class patches, then keeps patches
"stably localizable to one focal method". The paper does not publish the 172 IDs, so
this module applies a declared, deterministic rule and records every rejection:

  1. the bug is active in Defects4J and its ``classes.modified`` set has exactly one class;
  2. the official ``src.patch`` touches exactly one ``.java`` file;
  3. every changed fixed-side line (see ``d4jclient.Hunk.changed_fixed_lines``) falls
     inside one and the same *named* method or constructor of that file (anonymous-class
     and enum-constant bodies roll up to their enclosing named method, see ``javasrc``);
  4. the buggy version contains a method with the identical (class_path, name, params)
     signature, and its body text differs from the fixed body (the change is real, not
     e.g. a comment/import-only diff that the line-mapping mis-attributed).

Anything else is rejected with a specific reason string so the manifest is auditable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import d4jclient as d4j
from . import javasrc

PAPER_COUNTS = {"Cli": 24, "Compress": 32, "Csv": 11, "JacksonDatabind": 51, "Jsoup": 54}


def localize(project: str, bug: int) -> dict[str, Any]:
    task_id = f"{project}-{bug}"
    base = {"task_id": task_id, "project": project, "bug_id": bug}
    classes = d4j.modified_classes(project, bug)
    if len(classes) != 1:
        return base | {"reject": f"modified_classes={len(classes)}"}

    patch_text = d4j.read_src_patch(project, bug)
    file_patches = d4j.parse_unified_diff(patch_text)
    if len(file_patches) != 1:
        return base | {"reject": f"patch_files={len(file_patches)}"}
    file_patch = file_patches[0]

    try:
        fixed_dir = d4j.checkout(project, bug, "fixed")
    except RuntimeError as exc:
        return base | {"reject": f"checkout_failed: {exc}"[:300]}
    fixed_file = fixed_dir / file_patch.path
    if not fixed_file.exists():
        return base | {"reject": f"fixed_file_missing:{file_patch.path}"}
    fixed_src = fixed_file.read_text(encoding="utf-8", errors="replace")

    try:
        fixed_spans = javasrc.find_named_methods(fixed_src)
    except javasrc.UnparseableSource as exc:
        return base | {"reject": f"unparseable_fixed: {exc}"[:200]}

    changed_lines = [ln for hunk in file_patch.hunks for ln in hunk.changed_fixed_lines()]
    owners = {javasrc.enclosing_method(fixed_spans, ln) for ln in changed_lines}
    if None in owners:
        return base | {"reject": "change_outside_method"}
    if len(owners) != 1:
        return base | {"reject": f"methods={len(owners)}", "owners": sorted(o.signature_key for o in owners)}
    span = owners.pop()

    try:
        buggy_dir = d4j.checkout(project, bug, "buggy")
    except RuntimeError as exc:
        return base | {"reject": f"checkout_failed_buggy: {exc}"[:300]}
    buggy_file = buggy_dir / file_patch.path
    if not buggy_file.exists():
        return base | {"reject": f"buggy_file_missing:{file_patch.path}"}
    buggy_src = buggy_file.read_text(encoding="utf-8", errors="replace")
    try:
        buggy_spans = javasrc.find_named_methods(buggy_src)
    except javasrc.UnparseableSource as exc:
        return base | {"reject": f"unparseable_buggy: {exc}"[:200]}

    buggy_span = javasrc.find_method_by_signature(buggy_spans, span.class_path, span.name, span.params)
    if buggy_span is None:
        return base | {"reject": "signature_changed"}

    fixed_method = javasrc.method_source(fixed_src, span)
    buggy_method = javasrc.method_source(buggy_src, buggy_span)
    if fixed_method.strip() == buggy_method.strip():
        return base | {"reject": "no_method_change"}

    return base | {
        "focal_class": classes[0],
        "class_path": span.class_path,
        "focal_method": f"{span.name}({','.join(span.params)})",
        "method_name": span.name,
        "params": list(span.params),
        "is_constructor": span.is_constructor,
        "focal_file": file_patch.path,
        "fixed_lines": [span.start_line, span.end_line],
        "buggy_lines": [buggy_span.start_line, buggy_span.end_line],
        "fixed_method_source": fixed_method,
        "buggy_method_source": buggy_method,
        "trigger_tests": d4j.trigger_tests(project, bug),
        "n_hunks": len(file_patch.hunks),
    }


def build_all(out_path: Path, projects: tuple[str, ...] = d4j.BENCH_PROJECTS) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for project in projects:
            for bug in d4j.active_bugs(project):
                try:
                    row = localize(project, bug)
                except Exception as exc:  # keep going; record the failure
                    row = {"task_id": f"{project}-{bug}", "project": project, "bug_id": bug,
                           "reject": f"error:{type(exc).__name__}:{exc}"[:300]}
                rows.append(row)
                handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
                print(row["task_id"], row.get("reject", "OK"), flush=True)
    return rows


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    from collections import Counter

    summary: dict[str, dict[str, int]] = {}
    for project in PAPER_COUNTS:
        project_rows = [r for r in rows if r["project"] == project]
        accepted = [r for r in project_rows if "reject" not in r]
        rejects = Counter(r["reject"].split(":")[0].split("=")[0] for r in project_rows if "reject" in r)
        summary[project] = {"active": len(project_rows), "accepted": len(accepted), "paper": PAPER_COUNTS[project], **rejects}
    return summary
