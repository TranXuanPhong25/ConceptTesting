#!/usr/bin/env python3
"""Concept annotations tailored to the TestEval Python benchmark."""

from __future__ import annotations

import ast
import copy
import re
from typing import Any, Iterable


def annotate_record(record: dict[str, Any], path_record: dict[str, Any] | None = None) -> dict[str, Any]:
    """Annotate one TestEval `leetcode-py*.jsonl` record.

    The input schema follows TestEval: `python_solution`, `target_lines`,
    `blocks`, and optionally `sampled_paths` / `sampled_condition_paths` from
    `tgt_paths.jsonl`.
    """

    out = copy.deepcopy(record)
    source = record["python_solution"]
    tree = ast.parse(source)
    index = _AstIndex(source, tree, record.get("func_name"))
    path_record = path_record or {}

    line_targets = [_line_target(line, index) for line in record.get("target_lines", [])]
    branch_targets = [_branch_target(block, index) for block in record.get("blocks", [])]
    path_targets = [
        _path_target(i, path, conds)
        for i, (path, conds) in enumerate(
            zip(path_record.get("sampled_paths", []), path_record.get("sampled_condition_paths", []))
        )
    ]

    out["concept_annotation_py"] = {
        "schema": "concept_annotator_py.v2",
        "source": "TestEval",
        "task_num": record.get("task_num"),
        "task_title": record.get("task_title"),
        "func_name": record.get("func_name"),
        "program_concepts": index.program_concepts(),
        "line_targets": line_targets,
        "branch_targets": branch_targets,
        "path_targets": path_targets,
        "summary": _summary(line_targets, branch_targets, path_targets),
    }
    return out


def render_prompt_block(annotation: dict[str, Any], max_lines: int = 6, max_branches: int = 4, max_paths: int = 3) -> str:
    """Render a compact prompt block for TestEval target generation."""

    lines = ["Target-specific symbolic concept:"]

    for target in annotation.get("line_targets", [])[:max_lines]:
        symbolic = target.get("symbolic", {})
        lines.append("- target L%d: %s" % (target["line"], target["code"]))
        if symbolic.get("intent"):
            lines.append("  intent: " + symbolic["intent"])
        for constraint in symbolic.get("path_constraints", []):
            lines.append(
                "  required path constraint (L%d): %s"
                % (constraint["line"], constraint["input_expression"])
            )
            if constraint["source_expression"] != constraint["expanded_expression"]:
                lines.append("    derived from source guard: " + constraint["source_expression"])
        for relation in symbolic.get("avoid_relations", []):
            lines.append("  avoid: " + relation)
        if symbolic.get("state_transition"):
            lines.append("  state transition: " + symbolic["state_transition"])
        for strategy in symbolic.get("boundary_strategy", []):
            lines.append("  boundary strategy: " + strategy)

    for branch in annotation.get("branch_targets", [])[:max_branches]:
        lines.append(
            "- branch L%d->L%d (%s) [%s]: %s"
            % (
                branch["start"],
                branch["end"],
                branch["type"],
                ", ".join(branch["concepts"]),
                branch["condition"] or "(fallthrough)",
            )
        )

    for path in annotation.get("path_targets", [])[:max_paths]:
        lines.append("- path %d: %s" % (path["index"] + 1, path["summary"]))

    lines.append("Use the required relations and state transition to choose the smallest concrete input that reaches the target.")
    return "\n".join(lines)


class _AstIndex:
    def __init__(self, source: str, tree: ast.AST, func_name: str | None):
        self.source = source
        self.lines = source.splitlines()
        self.tree = tree
        self.func_name = func_name
        self.function = next(
            (node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name),
            None,
        )
        self.parameters = (
            [arg.arg for arg in self.function.args.args if arg.arg not in {"self", "cls"}]
            if self.function is not None
            else []
        )
        self.parents: dict[ast.AST, ast.AST] = {}
        self.nodes: list[ast.AST] = []
        self._index(tree)

    def line_code(self, line: int) -> str:
        if 1 <= line <= len(self.lines):
            return self.lines[line - 1].strip()
        return ""

    def node_at(self, line: int) -> ast.AST | None:
        matches = [
            node
            for node in self.nodes
            if hasattr(node, "lineno") and getattr(node, "lineno") <= line <= getattr(node, "end_lineno", getattr(node, "lineno"))
        ]
        if not matches:
            return None
        return min(matches, key=lambda node: (getattr(node, "end_lineno", line) - getattr(node, "lineno"), -getattr(node, "lineno")))

    def control_node_starting_at(self, line: int) -> ast.AST | None:
        for node in self.nodes:
            if isinstance(node, (ast.If, ast.For, ast.While)) and getattr(node, "lineno", None) == line:
                return node
        return None

    def control_context(self, line: int) -> list[dict[str, Any]]:
        return [info for _, info in reversed(self.control_path(line))]

    def control_path(self, line: int) -> list[tuple[ast.AST, dict[str, Any]]]:
        path: list[tuple[ast.AST, dict[str, Any]]] = []
        for node in self.nodes:
            if isinstance(node, ast.If):
                if _line_in_statements(node.body, line):
                    info = {**_control_info(node), "required_truth": True}
                elif _line_in_statements(node.orelse, line):
                    info = {**_control_info(node), "required_truth": False}
                else:
                    continue
            elif isinstance(node, ast.While):
                if not _line_in_statements(node.body, line):
                    continue
                info = {**_control_info(node), "required_truth": True}
            elif isinstance(node, ast.For):
                if not _line_in_statements(node.body, line):
                    continue
                info = {**_control_info(node), "required_truth": True}
            else:
                continue
            path.append((node, info))
        return sorted(path, key=lambda pair: pair[1]["line"])

    def bindings_before(self, line: int) -> dict[str, ast.AST]:
        bindings: dict[str, ast.AST] = {}
        scope = self.function or self.tree
        target_statement = _statement_node(self.node_at(line), self)
        writes: dict[str, list[tuple[ast.stmt, ast.AST | None]]] = {}
        statements = sorted(
            (node for node in ast.walk(scope) if isinstance(node, ast.stmt) and node.lineno < line),
            key=lambda node: node.lineno,
        )
        for node in statements:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                writes.setdefault(node.targets[0].id, []).append((node, node.value))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
                writes.setdefault(node.target.id, []).append((node, node.value))
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                writes.setdefault(node.target.id, []).append((node, None))
            elif isinstance(node, ast.For):
                for name in _stored_names(node.target):
                    writes.setdefault(name, []).append((node, None))
        for name, name_writes in writes.items():
            if target_statement is None or not all(
                _statement_dominates(write, target_statement, self.parents) for write, _ in name_writes
            ):
                continue
            value = name_writes[-1][1]
            if value is not None and all(item is not None and _safe_symbolic_value(item) for _, item in name_writes):
                bindings[name] = value
        return bindings

    def program_concepts(self) -> list[str]:
        tags: list[str] = []
        for node in ast.walk(self.tree):
            _extend_unique(tags, _concepts_for_node(node, self.func_name))
        return tags

    def _index(self, root: ast.AST) -> None:
        for parent in ast.walk(root):
            for child in ast.iter_child_nodes(parent):
                self.parents[child] = parent
        self.nodes = list(ast.walk(root))


def _line_target(line: int, index: _AstIndex) -> dict[str, Any]:
    node = index.node_at(line)
    concepts = _concepts_for_node(node, index.func_name) if node is not None else []
    reads, writes = _reads_writes(node)
    return {
        "line": line,
        "code": index.line_code(line),
        "ast_node": type(node).__name__ if node is not None else None,
        "concepts": concepts,
        "reads": reads,
        "writes": writes,
        "control_context": index.control_context(line),
        "symbolic": _symbolic_synthesis(node, line, index),
    }


def _branch_target(block: dict[str, Any], index: _AstIndex) -> dict[str, Any]:
    start = int(block["start"])
    node = index.control_node_starting_at(start) or index.node_at(start)
    condition = _block_condition(block, node)
    concepts = _condition_concepts(condition)
    if node is not None:
        _extend_unique(concepts, _concepts_for_node(node, index.func_name))
    return {
        "type": block.get("type"),
        "start": start,
        "end": int(block["end"]),
        "condition": condition,
        "condition_with_lineno": block.get("trigger_condition_with_lineno"),
        "concepts": concepts,
        "code": index.line_code(start),
    }


def _path_target(index: int, sampled_path: list[str], condition_path: list[str]) -> dict[str, Any]:
    conditions = [_parse_condition(raw) for raw in condition_path]
    return {
        "index": index,
        "sampled_path": sampled_path,
        "conditions": conditions,
        "summary": _path_summary(conditions),
    }


def _block_condition(block: dict[str, Any], node: ast.AST | None) -> str:
    raw = block.get("trigger_condition")
    if raw:
        return _strip_outer_parens(str(raw).strip())
    if isinstance(node, ast.If):
        cond = ast.unparse(node.test)
        if block.get("type") == "else":
            return "NOT " + cond
        return cond
    if isinstance(node, ast.While):
        return ast.unparse(node.test)
    if isinstance(node, ast.For):
        return "for " + ast.unparse(node.target) + " in " + ast.unparse(node.iter)
    return ""


def _control_info(node: ast.AST) -> dict[str, Any]:
    if isinstance(node, ast.If):
        typ, condition = "if", ast.unparse(node.test)
    elif isinstance(node, ast.While):
        typ, condition = "while", ast.unparse(node.test)
    elif isinstance(node, ast.For):
        typ = "for"
        condition = "for " + ast.unparse(node.target) + " in " + ast.unparse(node.iter)
    else:
        typ, condition = type(node).__name__, ""
    return {"line": getattr(node, "lineno", 0), "type": typ, "condition": condition}


def _line_in_statements(statements: list[ast.stmt], line: int) -> bool:
    return any(
        getattr(statement, "lineno", 0) <= line <= getattr(statement, "end_lineno", getattr(statement, "lineno", 0))
        for statement in statements
    )


def _stored_names(node: ast.AST) -> list[str]:
    return [item.id for item in ast.walk(node) if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)]


def _statement_dominates(statement: ast.stmt, target: ast.stmt, parents: dict[ast.AST, ast.AST]) -> bool:
    cursor: ast.AST | None = target
    while cursor is not None:
        parent = parents.get(cursor)
        if parent is None:
            return False
        for _, value in ast.iter_fields(parent):
            if not isinstance(value, list) or cursor not in value:
                continue
            if statement in value:
                return value.index(statement) < value.index(cursor)
            break
        cursor = parent
    return False


def _safe_symbolic_value(node: ast.AST) -> bool:
    if isinstance(node, (ast.Name, ast.Constant, ast.Attribute, ast.Subscript)):
        return True
    if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp)):
        return all(_safe_symbolic_value(child) for child in ast.iter_child_nodes(node))
    if isinstance(node, ast.Call):
        return _call_name(node) == "len" and len(node.args) == 1 and _safe_symbolic_value(node.args[0])
    if isinstance(node, (ast.operator, ast.unaryop, ast.boolop, ast.cmpop, ast.Load)):
        return True
    return False


def _expand_expression(node: ast.AST, bindings: dict[str, ast.AST], seen: frozenset[str] = frozenset()) -> ast.AST:
    if isinstance(node, ast.Name) and node.id in bindings and node.id not in seen:
        return _expand_expression(copy.deepcopy(bindings[node.id]), bindings, seen | {node.id})
    expanded = copy.deepcopy(node)
    for field, value in ast.iter_fields(expanded):
        if isinstance(value, ast.AST):
            setattr(expanded, field, _expand_expression(value, bindings, seen))
        elif isinstance(value, list):
            setattr(
                expanded,
                field,
                [_expand_expression(item, bindings, seen) if isinstance(item, ast.AST) else item for item in value],
            )
    return expanded


_INVERSE_COMPARE = {
    ast.Gt: ast.LtE,
    ast.GtE: ast.Lt,
    ast.Lt: ast.GtE,
    ast.LtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
}


def _condition_for_truth(node: ast.AST, truth: bool) -> ast.AST:
    if truth:
        return copy.deepcopy(node)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        inverse = _INVERSE_COMPARE.get(type(node.ops[0]))
        if inverse is not None:
            return ast.Compare(left=copy.deepcopy(node.left), ops=[inverse()], comparators=copy.deepcopy(node.comparators))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return copy.deepcopy(node.operand)
    return ast.UnaryOp(op=ast.Not(), operand=copy.deepcopy(node))


def _boundary_strategy(required: ast.AST) -> str | None:
    if not isinstance(required, ast.Compare) or len(required.ops) != 1 or len(required.comparators) != 1:
        return None
    left = ast.unparse(required.left)
    right = ast.unparse(required.comparators[0])
    op = required.ops[0]
    if isinstance(op, ast.Gt):
        relation = f"{left} = {right} + 1"
    elif isinstance(op, ast.Lt):
        relation = f"{left} = {right} - 1"
    elif isinstance(op, (ast.GtE, ast.LtE, ast.Eq)):
        relation = f"{left} = {right}"
    elif isinstance(op, ast.NotEq):
        relation = f"make {left} and {right} differ by the smallest valid amount"
    elif isinstance(op, ast.In):
        relation = f"place {left} in {right}"
    elif isinstance(op, ast.NotIn):
        relation = f"keep {left} absent from {right}"
    else:
        return None
    return "Use the nearest satisfying boundary: " + relation + "."


def _statement_node(node: ast.AST | None, index: _AstIndex) -> ast.AST | None:
    while node is not None and not isinstance(node, ast.stmt):
        node = index.parents.get(node)
    return node


def _target_intent(node: ast.AST | None, index: _AstIndex) -> str:
    statement = _statement_node(node, index)
    if isinstance(statement, ast.Return):
        recursive = next(
            (
                call
                for call in ast.walk(statement)
                if isinstance(call, ast.Call) and index.func_name and _call_name(call).endswith(index.func_name)
            ),
            None,
        )
        if recursive is not None:
            return f"Reach the recursive return that re-enters `{index.func_name}` with transformed arguments."
        value = ast.unparse(statement.value) if statement.value is not None else "None"
        return f"Reach the return path that produces `{value}`."
    if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return "Reach the state update performed by this assignment."
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return f"Reach the call to `{_call_name(statement.value)}`."
    return "Execute this target statement under its required control-flow conditions."


def _state_transition(node: ast.AST | None, index: _AstIndex) -> str:
    statement = _statement_node(node, index)
    if statement is None:
        return ""
    recursive = next(
        (
            call
            for call in ast.walk(statement)
            if isinstance(call, ast.Call) and index.func_name and _call_name(call).endswith(index.func_name)
        ),
        None,
    )
    if recursive is not None and index.parameters:
        mappings = [
            f"{parameter} <- {ast.unparse(argument)}"
            for parameter, argument in zip(index.parameters, recursive.args)
        ]
        return "Recursive call remaps inputs: " + "; ".join(mappings) + "."
    if isinstance(statement, ast.Return):
        value = ast.unparse(statement.value) if statement.value is not None else "None"
        return f"Control exits the function with `{value}`."
    if isinstance(statement, ast.Assign):
        targets = ", ".join(ast.unparse(target) for target in statement.targets)
        return f"Updates `{targets}` to `{ast.unparse(statement.value)}`."
    if isinstance(statement, ast.AugAssign):
        return f"Mutates `{ast.unparse(statement.target)}` using `{type(statement.op).__name__}`."
    return ""


def _symbolic_synthesis(node: ast.AST | None, line: int, index: _AstIndex) -> dict[str, Any]:
    bindings = index.bindings_before(line)
    constraints: list[dict[str, Any]] = []
    input_relations: list[str] = []
    avoid_relations: list[str] = []
    strategies: list[str] = []

    for control, info in index.control_path(line):
        truth = bool(info["required_truth"])
        if isinstance(control, (ast.If, ast.While)):
            source_node = control.test
            expanded = _expand_expression(source_node, bindings)
            required = _condition_for_truth(expanded, truth)
            avoided = _condition_for_truth(expanded, not truth)
            required_text = ast.unparse(required)
            avoided_text = ast.unparse(avoided)
            constraint = {
                "line": info["line"],
                "control": info["type"],
                "source_expression": ast.unparse(source_node),
                "expanded_expression": ast.unparse(expanded),
                "required_truth": truth,
                "input_expression": required_text,
            }
            strategy = _boundary_strategy(required)
        elif isinstance(control, ast.For):
            expanded = _expand_expression(control.iter, bindings)
            iterable = ast.unparse(expanded)
            required_text = f"{iterable} must produce at least one iteration"
            avoided_text = f"{iterable} is empty"
            constraint = {
                "line": info["line"],
                "control": "for",
                "source_expression": ast.unparse(control.iter),
                "expanded_expression": iterable,
                "required_truth": True,
                "input_expression": required_text,
            }
            strategy = f"Use the smallest valid input that makes `{iterable}` produce one iteration."
        else:
            continue
        constraints.append(constraint)
        _append_unique(input_relations, required_text)
        _append_unique(avoid_relations, avoided_text)
        if strategy:
            _append_unique(strategies, strategy)

    return {
        "intent": _target_intent(node, index),
        "path_constraints": constraints,
        "input_relations": input_relations,
        "avoid_relations": avoid_relations,
        "state_transition": _state_transition(node, index),
        "boundary_strategy": strategies,
    }


def _concepts_for_node(node: ast.AST | None, func_name: str | None = None) -> list[str]:
    if node is None:
        return []
    tags: list[str] = []
    for sub in ast.walk(node):
        if isinstance(sub, (ast.For, ast.While)):
            _append_unique(tags, "loop")
        if isinstance(sub, ast.If):
            _append_unique(tags, "conditional")
        if isinstance(sub, ast.Return):
            _append_unique(tags, "return_value")
        if isinstance(sub, (ast.Dict, ast.DictComp)):
            _append_unique(tags, "hash_map")
        if isinstance(sub, (ast.List, ast.ListComp)):
            _append_unique(tags, "list")
        if isinstance(sub, ast.Subscript):
            _append_unique(tags, "subscript")
        if isinstance(sub, ast.Compare):
            _extend_unique(tags, _compare_concepts(sub))
        if isinstance(sub, ast.BinOp):
            _append_unique(tags, "arithmetic")
        if isinstance(sub, ast.Assign):
            _append_unique(tags, "assignment")
            if any(isinstance(t, ast.Subscript) for t in sub.targets):
                _append_unique(tags, "mutation")
                _append_unique(tags, "hash_map_update")
        if isinstance(sub, ast.Call):
            name = _call_name(sub)
            if name in {"enumerate", "range", "zip"}:
                _append_unique(tags, "iteration")
            if name in {"sorted"} or name.endswith(".sort"):
                _append_unique(tags, "sorting")
            if name.startswith("heapq."):
                _append_unique(tags, "heap")
            if name.startswith("bisect."):
                _append_unique(tags, "binary_search")
            if func_name and name.endswith(func_name):
                _append_unique(tags, "recursion")
        if isinstance(sub, ast.Name) and sub.id.lower() in {"dp", "memo", "cache"}:
            _append_unique(tags, "dynamic_programming")
    return tags


def _compare_concepts(node: ast.Compare) -> list[str]:
    tags: list[str] = []
    if any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
        _append_unique(tags, "membership_test")
        _append_unique(tags, "hash_map_lookup")
    if any(isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for op in node.ops):
        _append_unique(tags, "ordering_constraint")
    if any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
        _append_unique(tags, "equality_constraint")
    return tags


def _condition_concepts(condition: str) -> list[str]:
    tags: list[str] = []
    if " in " in condition or " not in " in condition:
        _append_unique(tags, "membership_test")
        _append_unique(tags, "hash_map_lookup")
    if any(op in condition for op in ("<=", ">=", "<", ">")):
        _append_unique(tags, "ordering_constraint")
    if "==" in condition or "!=" in condition:
        _append_unique(tags, "equality_constraint")
    if condition.startswith("NOT "):
        _append_unique(tags, "negated_branch")
    return tags


def _reads_writes(node: ast.AST | None) -> tuple[list[str], list[str]]:
    if node is None:
        return [], []
    reads: list[str] = []
    writes: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_Name(self, item: ast.Name) -> None:
            if isinstance(item.ctx, ast.Load):
                _append_unique(reads, item.id)
            elif isinstance(item.ctx, (ast.Store, ast.Del)):
                _append_unique(writes, item.id)

    Visitor().visit(node)
    return reads, writes


def _parse_condition(raw: str) -> dict[str, Any]:
    match = re.match(r"\s*Line\s+(\d+):\s*(.*)\s*$", raw)
    if not match:
        return {"line": None, "condition": raw.strip(), "truth": True, "raw": raw}
    line = int(match.group(1))
    condition = match.group(2).strip()
    truth = True
    if condition.startswith("NOT "):
        truth = False
        condition = condition[4:].strip()
    condition = _strip_outer_parens(condition)
    return {"line": line, "condition": condition, "truth": truth, "raw": raw}


def _path_summary(conditions: list[dict[str, Any]]) -> str:
    parts = []
    for item in conditions:
        if item["line"] is None:
            parts.append(item["condition"])
            continue
        prefix = "line %d" % item["line"]
        cond = item["condition"]
        if item["truth"] is False:
            cond = "NOT " + cond
        parts.append(prefix + (" -> " + cond if cond else ""))
    return " ; ".join(parts)


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _attr_base(func.value)
        return (base + "." if base else "") + func.attr
    return ""


def _attr_base(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _attr_base(node.value)
        return (base + "." if base else "") + node.attr
    return ""


def _strip_outer_parens(value: str) -> str:
    value = value.strip()
    while value.startswith("(") and value.endswith(")") and _balanced(value[1:-1]):
        value = value[1:-1].strip()
    return value


def _balanced(value: str) -> bool:
    depth = 0
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _summary(line_targets: list[dict[str, Any]], branch_targets: list[dict[str, Any]], path_targets: list[dict[str, Any]]) -> str:
    return "%d line target(s), %d branch target(s), %d path target(s)" % (
        len(line_targets),
        len(branch_targets),
        len(path_targets),
    )


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _extend_unique(items: list[str], values: Iterable[str]) -> None:
    for value in values:
        _append_unique(items, value)
