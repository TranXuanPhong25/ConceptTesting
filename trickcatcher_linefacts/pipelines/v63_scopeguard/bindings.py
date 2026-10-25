"""Resolve an ordinary entry or the repository's simple Solution-method wrapper.

The original module and AST coordinates remain unchanged for concrete replay.
"""
import ast


def resolve(tree, entry):
    wrapper = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == entry), None)
    if wrapper is None: raise ValueError('entry_not_top_level_function')
    body = [n for n in wrapper.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))]
    if len(body) != 1 or not isinstance(body[0], ast.Return) or not isinstance(body[0].value, ast.Call):
        return wrapper, False
    call = body[0].value
    if not (isinstance(call.func, ast.Attribute) and call.func.attr == entry and isinstance(call.func.value, ast.Call)
            and isinstance(call.func.value.func, ast.Name) and not call.func.value.args and not call.func.value.keywords and not call.keywords):
        return wrapper, False
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == call.func.value.func.id), None)
    if cls is None or cls.bases or cls.decorator_list or cls.keywords or wrapper.decorator_list: return wrapper, False
    if any(isinstance(n, ast.FunctionDef) and n.name.startswith('__') for n in cls.body): return wrapper, False
    if any(not isinstance(n, (ast.FunctionDef, ast.Pass)) and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)) for n in cls.body):
        return wrapper, False
    method = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == entry), None)
    if method is None or method.decorator_list or not method.args.args or method.args.args[0].arg != 'self':
        return wrapper, False
    names = [a.arg for a in wrapper.args.posonlyargs + wrapper.args.args]
    args = call.args
    if len(args) == 1 and isinstance(args[0], ast.Starred):
        unpack = args[0].value
        if (isinstance(unpack, ast.Call) and isinstance(unpack.func, ast.Attribute)
                and isinstance(unpack.func.value, ast.Name) and unpack.func.value.id == 'copy'
                and unpack.func.attr == 'deepcopy' and len(unpack.args) == 1 and not unpack.keywords):
            unpack = unpack.args[0]
        args = unpack.elts if isinstance(unpack, ast.Tuple) else []
    if [a.id if isinstance(a, ast.Name) else None for a in args] != names:
        return wrapper, False
    method_names = [a.arg for a in method.args.posonlyargs + method.args.args][1:]
    if len(method_names) != len(names): return wrapper, False
    return method, True
