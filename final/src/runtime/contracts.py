"""Pure parsing and structural diversity checks; no generated code executes here."""
from __future__ import annotations

import ast
import hashlib
import json


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("Response must be a JSON object")
    return obj


def fingerprint(source: str, entry: str) -> str:
    """Ignore formatting, comments, docstrings, annotations, and identifier renames.

    This is a conservative structural filter, not a proof of algorithmic diversity.
    A shared binding map also handles helper names and comprehension variables.
    """
    tree = ast.parse(source)
    if not any(isinstance(n, ast.FunctionDef) and n.name == entry for n in tree.body):
        raise ValueError("Full source must define the required entry point")

    class Strip(ast.NodeTransformer):
        def visit_arg(self, node):
            node.annotation = None
            return node

        def visit_AnnAssign(self, node):
            return (self.visit(ast.Assign(targets=[node.target], value=node.value))
                    if node.value is not None else None)

        def visit_Pass(self, node):
            return None

        def generic_visit(self, node):
            if hasattr(node, "returns"):
                node.returns = None
            return super().generic_visit(node)

    tree = Strip().visit(tree)
    loaded = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    imports = {}

    class Imports(ast.NodeTransformer):
        def visit_Import(self, node):
            kept = []
            for alias in node.names:
                local = alias.asname or alias.name.split('.')[0]
                if local in loaded:
                    imports[local] = 'import:' + alias.name
                    alias.asname = None
                    kept.append(alias)
            node.names = kept
            return node if kept else None

        def visit_ImportFrom(self, node):
            kept = []
            for alias in node.names:
                local = alias.asname or alias.name
                if local in loaded:
                    imports[local] = f'import:{node.level}:{node.module}:{alias.name}'
                    alias.asname = None
                    kept.append(alias)
            node.names = kept
            return node if kept else None

        def visit_Assign(self, node):
            # Remove obvious unused literal padding, without erasing side effects.
            if isinstance(node.value, ast.Constant) and all(
                isinstance(target, ast.Name) and target.id not in loaded for target in node.targets
            ):
                return None
            return self.generic_visit(node)

    tree = Imports().visit(tree)
    names = {}

    def bind(name):
        if name not in names:
            names[name] = f"v{len(names)}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bind(node.name)
        elif isinstance(node, ast.arg):
            bind(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bind(node.id)

    class Normalize(ast.NodeTransformer):
        def visit_Name(self, node):
            node.id = imports.get(node.id, names.get(node.id, node.id))
            return node

        def visit_arg(self, node):
            node.arg = names[node.arg]
            node.annotation = None
            node.type_comment = None
            return node

        def visit_keyword(self, node):
            node.arg = names.get(node.arg, node.arg)
            return self.generic_visit(node)

        def visit_AnnAssign(self, node):
            if node.value is None:
                return None
            return self.visit(ast.Assign(targets=[node.target], value=node.value))

        def generic_visit(self, node):
            if hasattr(node, "body") and isinstance(node.body, list):
                node.body = [n for n in node.body if not (
                    isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str))]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                node.name = names[node.name]
            if hasattr(node, "returns"):
                node.returns = None
            if hasattr(node, "type_comment"):
                node.type_comment = None
            return super().generic_visit(node)

    normalized = ast.dump(Normalize().visit(tree), include_attributes=False)
    return hashlib.sha256(normalized.encode()).hexdigest()


SAFE_BUILTINS = ("abs", "all", "any", "bool", "dict", "enumerate", "float", "int",
                 "len", "list", "max", "min", "range", "reversed", "round", "set",
                 "sorted", "str", "sum", "tuple", "zip")


def validate_test(record: dict) -> dict:
    """Literal arguments + a restricted predicate over result/args/kwargs/math."""
    if not isinstance(record, dict):
        raise ValueError("Test must be an object")
    for name in ("args", "kwargs", "assertion"):
        if not isinstance(record.get(name), str) or len(record[name]) > 20000:
            raise ValueError(f"Test {name} must be a string of at most 20000 characters")
    args, kwargs = ast.literal_eval(record["args"]), ast.literal_eval(record["kwargs"])
    if not isinstance(args, (list, tuple)) or not isinstance(kwargs, dict):
        raise ValueError("args must be list/tuple; kwargs must be a dict")
    if not all(isinstance(k, str) for k in kwargs):
        raise ValueError("kwargs keys must be strings")
    tree = ast.parse(record["assertion"], mode="eval")
    allowed = set(SAFE_BUILTINS) | {"result", "args", "kwargs", "math"}
    for node in ast.walk(tree):
        if isinstance(node, ast.comprehension):
            for target in ast.walk(node.target):
                if isinstance(target, ast.Name):
                    if target.id in allowed or target.id.startswith("_"):
                        raise ValueError("Comprehension cannot shadow reserved names")
                    allowed.add(target.id)
        if isinstance(node, (ast.Lambda, ast.NamedExpr, ast.Await, ast.Yield, ast.YieldFrom)):
            raise ValueError("Unsupported predicate expression")
        if isinstance(node, ast.Attribute):
            if not (isinstance(node.value, ast.Name) and node.value.id == "math"
                    and not node.attr.startswith("_")):
                raise ValueError("Only public math attributes are allowed")
        if isinstance(node, ast.Call):
            if not ((isinstance(node.func, ast.Name) and node.func.id in SAFE_BUILTINS)
                    or isinstance(node.func, ast.Attribute)):
                raise ValueError("Unsupported predicate function call")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in allowed:
            raise ValueError("Unknown name in predicate")
    return {name: record[name] for name in ("args", "kwargs", "assertion")}
