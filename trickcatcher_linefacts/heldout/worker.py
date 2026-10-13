"""Entry adapters for workers with data paths and HumanEval base AST assumptions."""
from pathlib import Path
import ast
import json
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def oracle(job_path, result_path):
    from trickcatcher_linefacts import oracle_b01 as ob
    job = json.loads(Path(job_path).read_text())
    parse = ast.parse
    def parse_base(source, *args, **kwargs):
        tree = parse(source, *args, **kwargs)
        if source == job["base"]:
            # Only the extraction AST changes. passes_base still executes the
            # actual tolerant check. Preserve the trusted pairs for B3 posts.
            for n in ast.walk(tree):
                if isinstance(n, ast.Assert) and isinstance(n.test, ast.Call) and isinstance(n.test.func, ast.Name) and n.test.func.id == "_heldout_same":
                    call, expected = n.test.args[:2]
                    n.test = ast.Compare(left=call, ops=[ast.Eq()], comparators=[expected])
        return tree
    proxy = SimpleNamespace(**{name: getattr(ast, name) for name in dir(ast)})
    proxy.parse = parse_base
    with patch.object(ob, "ast", proxy):
        ob.worker(job_path, result_path)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["worker"]: args = args[1:]
    oracle(*args[:2])
