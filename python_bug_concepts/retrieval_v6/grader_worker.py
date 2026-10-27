"""Grading-only bounded worker. Never imported by the retrieval engine."""
import contextlib
import copy
import inspect
import io
import json
import resource
import sys
import textwrap

resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
job = json.load(sys.stdin)
out = io.StringIO()
try:
    namespace = {}
    with contextlib.redirect_stdout(out):
        exec(compile(job["source"], "<grading-source>", "exec"), namespace)
        function = namespace[job["entry"]]
        if job["mode"] == "validity":
            params = ", ".join(inspect.signature(function).parameters)
            body = textwrap.dedent(job["contract"]).strip()
            code = f"def __contract__({params}):\n" + (textwrap.indent(body, "    ") + "\n" if body else "") + "    return True\n"
            exec(compile(code, "<official-contract>", "exec"), namespace)
            value = namespace["__contract__"](*copy.deepcopy(job["args"]))
        else:
            value = function(*copy.deepcopy(job["args"]))
    result = {"status": "ok", "value": value, "type": type(value).__name__, "repr": repr(value)[:2000]}
    json.dumps(result)
except BaseException as exc:
    result = {"status": "error", "error_type": type(exc).__name__, "message": str(exc)[:500]}
print(json.dumps(result, ensure_ascii=True))
