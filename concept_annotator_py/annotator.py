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
        "schema": "concept_annotator_py.v4",
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


def render_prompt_block(
    annotation: dict[str, Any],
    max_lines: int = 6,
    max_branches: int = 4,
    max_paths: int = 3,
    fact_kinds: set[str] | None = None,
) -> str:
    """Render a compact prompt block for TestEval target generation."""

    lines = ["Reachability facts for the target:"]

    for target in annotation.get("line_targets", [])[:max_lines]:
        symbolic = target.get("symbolic", {})
        lines.append("- target L%d: %s" % (target["line"], target["code"]))
        for fact in symbolic.get("reachability_facts", []):
            if fact_kinds is not None and fact["kind"] not in fact_kinds:
                continue
            lines.append("  %s: %s" % (fact["kind"], fact["detail"]))

    lines.append("Choose the smallest concrete input satisfying every fact above. Do not add facts that are not required to reach the target.")
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
        self.sequence_names = _sequence_names(self.function)

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

    def prior_exit_guards(self, line: int) -> list[tuple[ast.If, bool]]:
        """Find earlier sibling guards that must be bypassed to reach a line."""
        cursor = _statement_node(self.node_at(line), self)
        guards: list[tuple[ast.If, bool]] = []
        while cursor is not None:
            parent = self.parents.get(cursor)
            if parent is None:
                break
            for _, value in ast.iter_fields(parent):
                if not isinstance(value, list) or cursor not in value:
                    continue
                for sibling in value[: value.index(cursor)]:
                    if not isinstance(sibling, ast.If):
                        continue
                    body_exits = _definitely_exits(sibling.body)
                    else_exits = _definitely_exits(sibling.orelse)
                    if body_exits != else_exits:
                        guards.append((sibling, not body_exits))
                break
            cursor = parent if isinstance(parent, ast.stmt) else None
        return sorted(guards, key=lambda item: item[0].lineno)

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


def _definitely_exits(statements: list[ast.stmt]) -> bool:
    if not statements:
        return False
    last = statements[-1]
    if isinstance(last, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
        return True
    if isinstance(last, ast.If) and last.orelse:
        return _definitely_exits(last.body) and _definitely_exits(last.orelse)
    return False


def _sequence_names(function: ast.AST | None) -> set[str]:
    """Conservatively identify names known to hold indexable sequences."""
    if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return set()
    names: set[str] = set()
    for arg in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs):
        if arg.annotation is not None:
            annotation = ast.unparse(arg.annotation)
            if annotation in {"str", "bytes", "list", "tuple"} or annotation.startswith(
                ("List[", "list[", "Tuple[", "tuple[", "Sequence[")
            ):
                names.add(arg.arg)
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, (ast.List, ast.ListComp, ast.Tuple)):
                names.add(node.targets[0].id)
    return names


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
    facts: list[dict[str, str]] = []

    for control, info in index.control_path(line):
        truth = bool(info["required_truth"])
        required: ast.AST | None = None
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
        if isinstance(control, ast.If):
            _append_fact(facts, "branch_true" if truth else "branch_false", required_text)
        elif isinstance(control, (ast.While, ast.For)):
            _append_fact(facts, "loop_one_plus_iteration", required_text)
        if required is not None:
            for detail in _state_before_use(required):
                _append_fact(facts, "state_before_use", detail)
            if isinstance(control, ast.If) and truth:
                for detail in _prior_iteration_setup(control, index):
                    _append_fact(facts, "loop_two_plus_iteration", detail)
            if isinstance(control, ast.While):
                for detail in _state_after_update(control, index):
                    _append_fact(facts, "state_after_update", detail)
        if strategy:
            _append_unique(strategies, strategy)

    for guard, truth in index.prior_exit_guards(line):
        required = _condition_for_truth(guard.test, truth)
        _append_fact(facts, "avoid_early_exit", f"at L{guard.lineno}: {ast.unparse(required)}")

    for detail in _index_bounds(node, index):
        _append_fact(facts, "index_in_bounds", detail)
    transition = _state_transition(node, index)
    if transition.startswith("Recursive call remaps inputs:"):
        _append_fact(facts, "recursive_argument_swap", transition.removeprefix("Recursive call remaps inputs: ").rstrip("."))

    return {
        "intent": _target_intent(node, index),
        "path_constraints": constraints,
        "input_relations": input_relations,
        "avoid_relations": avoid_relations,
        "state_transition": transition,
        "boundary_strategy": strategies,
        "reachability_facts": facts,
    }


def _state_before_use(required: ast.AST) -> list[str]:
    """Derive population preconditions from membership guards such as ``x in seen``."""
    facts: list[str] = []
    for compare in ast.walk(required):
        if not isinstance(compare, ast.Compare) or len(compare.ops) != 1 or len(compare.comparators) != 1:
            continue
        if isinstance(compare.ops[0], ast.In):
            _append_unique(facts, f"{ast.unparse(compare.comparators[0])} already contains {ast.unparse(compare.left)}")
        elif isinstance(compare.ops[0], ast.NotIn):
            _append_unique(facts, f"{ast.unparse(compare.comparators[0])} does not contain {ast.unparse(compare.left)}")
    return facts


def _prior_iteration_setup(guard: ast.If, index: _AstIndex) -> list[str]:
    """Find an empty map populated after this guard in a surrounding loop."""
    facts: list[str] = []
    collections = {
        compare.comparators[0].id
        for compare in ast.walk(guard.test)
        if isinstance(compare, ast.Compare)
        and len(compare.ops) == 1
        and isinstance(compare.ops[0], ast.In)
        and len(compare.comparators) == 1
        and isinstance(compare.comparators[0], ast.Name)
    }
    loop = index.parents.get(guard)
    while loop is not None and not isinstance(loop, (ast.For, ast.While)):
        loop = index.parents.get(loop)
    if not isinstance(loop, (ast.For, ast.While)):
        return facts
    for name in collections:
        initialized_empty = any(
            isinstance(stmt, ast.Assign)
            and stmt.lineno < loop.lineno
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and stmt.targets[0].id == name
            and isinstance(stmt.value, ast.Dict)
            and not stmt.value.keys
            for stmt in ast.walk(index.function or index.tree)
        )
        if not initialized_empty:
            continue
        for stmt in ast.walk(loop):
            if not isinstance(stmt, ast.Assign) or stmt.lineno <= guard.lineno:
                continue
            if any(
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == name
                for target in stmt.targets
            ):
                _append_unique(facts, f"{name} starts empty; a previous loop iteration must execute `{ast.unparse(stmt)}`")
                break
    return facts


def _state_after_update(loop: ast.While, index: _AstIndex) -> list[str]:
    parent = index.parents.get(loop)
    if parent is None:
        return []
    for _, value in ast.iter_fields(parent):
        if not isinstance(value, list) or loop not in value:
            continue
        facts: list[str] = []
        for stmt in value[: value.index(loop)]:
            if not isinstance(stmt, ast.AugAssign) or not isinstance(stmt.target, ast.Name):
                continue
            if any(isinstance(n, ast.Name) and n.id == stmt.target.id for n in ast.walk(loop.test)):
                _append_unique(facts, f"after `{ast.unparse(stmt)}`, require `{ast.unparse(loop.test)}`")
        return facts
    return []


def _index_bounds(node: ast.AST | None, index: _AstIndex) -> list[str]:
    """Only claim an index bound when the container is known to be a sequence."""
    if node is None:
        return []
    facts: list[str] = []
    for subscript in ast.walk(node):
        if isinstance(subscript, ast.Subscript):
            root = subscript.value
            while isinstance(root, ast.Subscript):
                root = root.value
            if not isinstance(root, ast.Name) or root.id not in index.sequence_names:
                continue
            _append_unique(
                facts,
                f"{ast.unparse(subscript.slice)} selects an existing element of {ast.unparse(subscript.value)}",
            )
    return facts


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


def _append_fact(facts: list[dict[str, str]], kind: str, detail: str) -> None:
    fact = {"kind": kind, "detail": detail}
    if detail and fact not in facts:
        facts.append(fact)


def _extend_unique(items: list[str], values: Iterable[str]) -> None:
    for value in values:
        _append_unique(items, value)
