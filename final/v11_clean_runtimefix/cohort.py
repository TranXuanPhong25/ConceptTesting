"""Restore specification metadata for V11 without altering saved program bodies."""

import ast
import copy


class V11ProgramView:
    def build(self, human_eval, program):
        scaffold = ast.parse(human_eval["prompt"])
        generated = ast.parse(program["code"])
        original_entry = next(
            node
            for node in scaffold.body
            if isinstance(node, ast.FunctionDef)
            and node.name == human_eval["entry_point"]
        )
        entry = next(
            node
            for node in generated.body
            if isinstance(node, ast.FunctionDef)
            and node.name == human_eval["entry_point"]
        )
        docstring = ast.get_docstring(original_entry, clean=False) or ""
        if (
            entry.body
            and isinstance(entry.body[0], ast.Expr)
            and isinstance(entry.body[0].value, ast.Constant)
            and isinstance(entry.body[0].value.value, str)
        ):
            entry.body.pop(0)
        entry.body.insert(0, ast.Expr(ast.Constant(docstring)))
        for actual, public in zip(
            entry.args.posonlyargs + entry.args.args,
            original_entry.args.posonlyargs + original_entry.args.args,
        ):
            if actual.annotation is None:
                actual.annotation = copy.deepcopy(public.annotation)
        if entry.returns is None:
            entry.returns = copy.deepcopy(original_entry.returns)
        generated_definitions = {
            node.name
            for node in generated.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        }
        prefix = []
        for node in scaffold.body:
            if isinstance(node, ast.FunctionDef) and node.name in generated_definitions:
                continue
            prefix.append(node)
        future_imports = []
        remaining = []
        for node in generated.body:
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                future_imports.append(node)
            else:
                remaining.append(node)
        module = ast.Module(body=future_imports + prefix + remaining, type_ignores=[])
        return ast.unparse(ast.fix_missing_locations(module)) + "\n"
