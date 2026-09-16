#!/usr/bin/env python3
"""Build de-leaked concept targets for vulnerability test generation.

The shape borrows TEstEval's useful split: target lines, target branches, and
target paths. The content is still this repo's concept-guided memory-safety
setting: source + static concept facts only, never patch/fix/fault_cond.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Iterable

PROPS = [
    "null_assignment",
    "null_check",
    "ptr_deref",
    "buffer_allocation",
    "buffer_access",
    "bound_check",
    "free",
    "if_statement",
]

IDX = {name: i for i, name in enumerate(PROPS)}
N_PROPS = len(PROPS)

_CONTROL_RE = re.compile(r"\b(?:if|while|for|switch)\s*\(")
_BOUND_RE = re.compile(r"\b(?:if|while|for)\s*\([^)]*(?:<=|>=|<|>)[^)]*\)")
_NULL_CHECK_RE = re.compile(r"\b(?:if|while)\s*\([^)]*(?:NULL|nullptr|!\s*[A-Za-z_]\w*)[^)]*\)")
_NULL_ASSIGN_RE = re.compile(r"(?<![=!<>])=\s*(?:NULL|nullptr)\b")
_FREE_RE = re.compile(r"\bfree\s*\(")
_ALLOC_RE = re.compile(r"\b(?:malloc|calloc|realloc|alloca)\s*\(")
_ARRAY_DECL_RE = re.compile(
    r"\b(?:const\s+|static\s+|unsigned\s+|signed\s+)*"
    r"(?:char|short|int|long|float|double|wchar_t|size_t|u?int\d+_t|[A-Za-z_]\w*)"
    r"\s+\*?\s*[A-Za-z_]\w*\s*\[[^\]]+\]"
)
_BUFFER_CALL_RE = re.compile(
    r"\b(?:memcpy|memmove|memset|memcmp|strcpy|strncpy|strcat|strncat|sprintf|snprintf|"
    r"read|fread|recv)\s*\("
)
_DEREF_RE = re.compile(r"(?:^|[=({[,;]\s*)\*\s*[A-Za-z_]\w*|\w+\s*->\s*\w+")
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")

_CALL_ARG_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\((.*)\)")
_HIGH_RISK_CALL_RE = re.compile(r"\b(?:memcpy|memmove|strcpy|strncpy|strcat|strncat|sprintf|read|fread|recv)\s*\(")


def heuristic_lines_concept(func: str) -> dict[str, list[int]]:
    """Best-effort C-ish concept tags for each source line.

    Existing pipelines can pass `lines_concept` from tree-sitter; this fallback
    keeps the annotator runnable for quick ablations and toy examples.
    """

    out: dict[str, list[int]] = {}
    for i, line in enumerate(func.splitlines()):
        vec = [0] * N_PROPS
        stripped = line.strip()
        is_array_decl = bool(_ARRAY_DECL_RE.search(stripped))

        if _NULL_ASSIGN_RE.search(stripped):
            vec[IDX["null_assignment"]] = 1
        if _NULL_CHECK_RE.search(stripped):
            vec[IDX["null_check"]] = 1
        if _DEREF_RE.search(stripped):
            vec[IDX["ptr_deref"]] = 1
        if is_array_decl or _ALLOC_RE.search(stripped):
            vec[IDX["buffer_allocation"]] = 1
        if (("[" in stripped and "]" in stripped and not is_array_decl) or _BUFFER_CALL_RE.search(stripped)):
            vec[IDX["buffer_access"]] = 1
        if _BOUND_RE.search(stripped):
            vec[IDX["bound_check"]] = 1
        if _FREE_RE.search(stripped):
            vec[IDX["free"]] = 1
        if _CONTROL_RE.search(stripped):
            vec[IDX["if_statement"]] = 1
        out[str(i)] = vec
    return out


def annotate_function(func: str, lines_concept: dict[str, Iterable[int]] | None = None) -> dict[str, Any]:
    """Return concept targets for a single function body."""

    lc = _normalize_lines_concept(func, lines_concept)
    family = _infer_family(func, lc)
    concept_lines = _concept_lines(func, lc)
    targets = _build_targets(func, lc, family)
    ann = {
        "schema": "concept_annotator.v1",
        "family_pred": family,
        "props": list(PROPS),
        "lines_concept": lc,
        "concept_lines": concept_lines,
        "targets": targets,
        "summary": _summary(family, targets),
    }
    ann["testeval"] = to_testeval_metadata(ann)
    return ann


def annotate_item(item: dict[str, Any], func_field: str | None = None) -> dict[str, Any]:
    """Annotate a benchmark item without mutating the caller's dictionary."""

    out = copy.deepcopy(item)
    field = func_field or _pick_func_field(out)
    if not field:
        raise ValueError("item has no function source field (expected func_vuln, func, or code)")
    ann = annotate_function(str(out[field]), out.get("lines_concept"))
    out["concept_annotation"] = ann
    return out


def to_testeval_metadata(annotation: dict[str, Any]) -> dict[str, Any]:
    """Export compact TEstEval-shaped metadata."""

    target_lines: list[int] = []
    blocks: list[dict[str, int]] = []
    sampled_paths: list[list[int]] = []
    sampled_condition_paths: list[list[str]] = []

    for target in annotation.get("targets", []):
        if target.get("kind") == "target_line":
            _append_unique(target_lines, int(target["line"]))
        elif target.get("kind") == "target_branch":
            block = {"start": int(target["line"]), "end": int(target["end_line"])}
            if block not in blocks:
                blocks.append(block)
        elif target.get("kind") == "target_path":
            waypoints = [int(x) for x in target.get("waypoints", [])]
            if waypoints and waypoints not in sampled_paths:
                sampled_paths.append(waypoints)
                sampled_condition_paths.append([_waypoint_label(annotation, line) for line in waypoints])

    return {
        "target_lines": target_lines,
        "blocks": blocks,
        "sampled_paths": sampled_paths,
        "sampled_condition_paths": sampled_condition_paths,
    }


def render_prompt_block(annotation: dict[str, Any], max_targets: int = 6) -> str:
    """Human-readable block to append to an LLM prompt."""

    lines = ["TEstEval-inspired concept targets (static, de-leaked):"]
    family = annotation.get("family_pred") or "no_target"
    lines.append(f"- inferred family: {family}")
    for target in annotation.get("targets", [])[:max_targets]:
        kind = target.get("kind")
        tags = ", ".join(target.get("tags") or [])
        if kind == "target_line":
            lines.append(
                "- target line L%d [%s]: %s"
                % (target["line"], tags, target.get("code", "").strip())
            )
        elif kind == "target_branch":
            controls = ", ".join(target.get("controllable_vars") or []) or "unknown"
            lines.append(
                "- branch L%d -> L%d [%s], controls: %s: %s"
                % (target["line"], target["end_line"], tags, controls, target.get("code", "").strip())
            )
        elif kind == "target_path":
            lines.append(
                "- path %s: %s"
                % (" -> ".join("L%d" % x for x in target.get("waypoints", [])), target.get("goal", ""))
            )
    lines.append("Use these as coverage goals before trying to trigger the sanitizer oracle.")
    return "\n".join(lines)


def _normalize_lines_concept(func: str, lines_concept: dict[str, Iterable[int]] | None) -> dict[str, list[int]]:
    heuristic = heuristic_lines_concept(func)
    n_lines = len(func.splitlines())
    out: dict[str, list[int]] = {}
    for i in range(n_lines):
        base = list(heuristic.get(str(i), [0] * N_PROPS))
        given = list((lines_concept or {}).get(str(i), []))
        given = (given + [0] * N_PROPS)[:N_PROPS]
        out[str(i)] = [1 if base[j] or given[j] else 0 for j in range(N_PROPS)]
    return out


def _pick_func_field(item: dict[str, Any]) -> str | None:
    for field in ("func_vuln", "func", "code", "python_solution"):
        if field in item and item[field]:
            return field
    return None


def _infer_family(func: str, lc: dict[str, list[int]]) -> str | None:
    free_lines = _lines_with(lc, "free")
    deref_lines = _lines_with(lc, "ptr_deref")
    if len(free_lines) >= 2:
        return "double_free"
    if free_lines and any(line > free_lines[0] for line in deref_lines):
        return "uaf"
    if _has(lc, "buffer_allocation") and _has(lc, "buffer_access"):
        return "oob"
    if _has(lc, "buffer_access") and not _has(lc, "bound_check"):
        return "oob"
    if _has(lc, "ptr_deref") and not _has(lc, "null_check"):
        return "null_deref"
    return None


def _build_targets(func: str, lc: dict[str, list[int]], family: str | None) -> list[dict[str, Any]]:
    source_lines = func.splitlines()
    params = _params(func)
    sinks = _sink_lines(source_lines, lc, family)
    targets: list[dict[str, Any]] = []

    for line in sinks:
        targets.append(_target_line(source_lines, lc, params, line, family))

    for sink in sinks:
        for branch in _control_lines_before(source_lines, lc, sink):
            targets.append(_target_branch(source_lines, lc, params, branch, sink))

    for path in _path_waypoints(source_lines, lc, family, sinks):
        targets.append(_target_path(source_lines, lc, family, path))

    return _dedupe_targets(sorted(targets, key=lambda t: (-int(t["priority"]), t["id"])))


def _target_line(
    source_lines: list[str],
    lc: dict[str, list[int]],
    params: list[str],
    line: int,
    family: str | None,
) -> dict[str, Any]:
    code = source_lines[line].strip()
    return {
        "id": f"line:L{line}:sink",
        "kind": "target_line",
        "line": line,
        "code": code,
        "tags": _tags(lc, line),
        "controllable_vars": _controllable_vars(code, params),
        "goal": _line_goal(family, line),
        "priority": _line_priority(code, lc, line, family),
    }


def _target_branch(
    source_lines: list[str],
    lc: dict[str, list[int]],
    params: list[str],
    branch: int,
    sink: int,
) -> dict[str, Any]:
    code = source_lines[branch].strip()
    return {
        "id": f"branch:L{branch}:to:L{sink}",
        "kind": "target_branch",
        "line": branch,
        "end_line": sink,
        "code": code,
        "tags": _tags(lc, branch),
        "controllable_vars": _controllable_vars(code, params),
        "goal": f"take the branch that reaches target line L{sink}",
        "priority": 80,
    }


def _target_path(source_lines: list[str], lc: dict[str, list[int]], family: str | None, path: list[int]) -> dict[str, Any]:
    if family == "uaf" and len(path) >= 2:
        goal = f"cover free first, then reach later use at L{path[-1]}"
    elif family == "double_free" and len(path) >= 2:
        goal = f"cover first free, then reach second free at L{path[-1]}"
    else:
        goal = f"cover control/data waypoints before target line L{path[-1]}"
    return {
        "id": "path:" + "->".join("L%d" % p for p in path),
        "kind": "target_path",
        "waypoints": path,
        "code": [_line_label(source_lines, p) for p in path],
        "tags": sorted({tag for p in path for tag in _tags(lc, p)}),
        "goal": goal,
        "priority": 70,
    }


def _sink_lines(source_lines: list[str], lc: dict[str, list[int]], family: str | None) -> list[int]:
    if family == "uaf":
        frees = _lines_with(lc, "free")
        first_free = frees[0] if frees else -1
        return [line for line in _lines_with(lc, "ptr_deref") if line > first_free]
    if family == "double_free":
        frees = _lines_with(lc, "free")
        return frees[1:] or frees
    if family == "null_deref":
        return _lines_with(lc, "ptr_deref")

    candidates = _lines_with(lc, "buffer_access")
    if family == "oob":
        candidates = [line for line in candidates if not _is_only_allocation(source_lines[line], lc, line)]
    if not candidates:
        candidates = _lines_with(lc, "free") or _lines_with(lc, "ptr_deref")
    return sorted(candidates, key=lambda line: -_line_priority(source_lines[line].strip(), lc, line, family))


def _control_lines_before(source_lines: list[str], lc: dict[str, list[int]], sink: int, window: int = 10) -> list[int]:
    start = max(0, sink - window)
    out: list[int] = []
    for line in range(start, sink):
        tags = _tags(lc, line)
        if "if_statement" in tags or "bound_check" in tags or _CONTROL_RE.search(source_lines[line]):
            out.append(line)
    return out[-2:]


def _path_waypoints(source_lines: list[str], lc: dict[str, list[int]], family: str | None, sinks: list[int]) -> list[list[int]]:
    if not sinks:
        return []
    paths: list[list[int]] = []
    if family in ("uaf", "double_free"):
        free_lines = _lines_with(lc, "free")
        if free_lines:
            for sink in sinks[:2]:
                controls = _control_lines_before(source_lines, lc, sink)
                path = _unique_sorted_by_position([free_lines[0], *controls, sink])
                if len(path) > 1:
                    paths.append(path)
            return paths

    for sink in sinks[:3]:
        controls = _control_lines_before(source_lines, lc, sink)
        path = _unique_sorted_by_position([*controls, sink])
        if len(path) > 1:
            paths.append(path)
    return paths


def _params(func: str) -> list[str]:
    match = re.search(r"[A-Za-z_]\w*\s*\(([^)]*)\)\s*\{", func)
    if not match:
        return []
    out: list[str] = []
    for param in match.group(1).split(","):
        words = _IDENT_RE.findall(param)
        if words and words[-1] != "void":
            out.append(words[-1])
    return out


def _controllable_vars(code: str, params: list[str]) -> list[str]:
    if not params:
        return []
    tokens = _IDENT_RE.findall(code)
    seen = [p for p in params if p in tokens]
    call = _CALL_ARG_RE.search(code)
    if call:
        args = [_IDENT_RE.findall(part) for part in _split_args(call.group(2))]
        arg_vars = [tok for group in args for tok in group if tok in params]
        if call.group(1) in {"memcpy", "memmove", "memset", "strncpy", "strncat", "read", "fread", "recv"}:
            arg_vars = list(reversed(arg_vars))
        seen = arg_vars + seen
    return _unique(seen)


def _split_args(arg_src: str) -> list[str]:
    args: list[str] = []
    cur: list[str] = []
    depth = 0
    for ch in arg_src:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            args.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        args.append(tail)
    return args


def _concept_lines(func: str, lc: dict[str, list[int]]) -> list[dict[str, Any]]:
    lines = func.splitlines()
    out: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        tags = _tags(lc, i)
        if tags:
            out.append({"line": i, "code": line.strip(), "tags": tags})
    return out


def _line_priority(code: str, lc: dict[str, list[int]], line: int, family: str | None) -> int:
    tags = set(_tags(lc, line))
    if family == "uaf" and "ptr_deref" in tags:
        return 105
    if family == "double_free" and "free" in tags:
        return 105
    if _HIGH_RISK_CALL_RE.search(code):
        return 100
    if "ptr_deref" in tags:
        return 90
    if "buffer_access" in tags:
        return 85
    if "free" in tags:
        return 80
    return 50


def _line_goal(family: str | None, line: int) -> str:
    if family == "oob":
        return f"execute the dangerous buffer access at L{line}"
    if family == "uaf":
        return f"execute the use after an earlier free at L{line}"
    if family == "double_free":
        return f"execute repeated free at L{line}"
    if family == "null_deref":
        return f"execute pointer dereference at L{line}"
    return f"execute concept-bearing line L{line}"


def _waypoint_label(annotation: dict[str, Any], line: int) -> str:
    for item in annotation.get("concept_lines", []):
        if int(item["line"]) == line:
            return "L%d [%s] %s" % (line, ",".join(item["tags"]), item["code"])
    return f"L{line}"


def _line_label(source_lines: list[str], line: int) -> str:
    return "L%d %s" % (line, source_lines[line].strip())


def _is_only_allocation(code: str, lc: dict[str, list[int]], line: int) -> bool:
    tags = set(_tags(lc, line))
    return "buffer_allocation" in tags and "buffer_access" in tags and not _BUFFER_CALL_RE.search(code)


def _summary(family: str | None, targets: list[dict[str, Any]]) -> str:
    fam = family or "no clear family"
    return "%s; %d target(s): %s" % (
        fam,
        len(targets),
        ", ".join(t["id"] for t in targets[:4]),
    )


def _lines_with(lc: dict[str, list[int]], prop: str) -> list[int]:
    idx = IDX[prop]
    return sorted(int(line) for line, vec in lc.items() if len(vec) > idx and vec[idx])


def _has(lc: dict[str, list[int]], prop: str) -> bool:
    return bool(_lines_with(lc, prop))


def _tags(lc: dict[str, list[int]], line: int) -> list[str]:
    vec = lc.get(str(line), [])
    return [PROPS[i] for i, value in enumerate(vec[:N_PROPS]) if value]


def _dedupe_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for target in targets:
        if target["id"] not in seen:
            out.append(target)
            seen.add(target["id"])
    return out


def _append_unique(items: list[int], value: int) -> None:
    if value not in items:
        items.append(value)


def _unique(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


def _unique_sorted_by_position(lines: Iterable[int]) -> list[int]:
    return sorted(set(lines))
