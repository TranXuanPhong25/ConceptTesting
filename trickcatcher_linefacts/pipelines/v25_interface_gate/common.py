import ast
import hashlib
import json
import functools
import subprocess
from pathlib import Path
from .paths import CONFIG
from .source_view import prepare
from .chain_inputs import parse_arguments, parse_literal, literal_for_transport, typed_value
D=CONFIG["diagnostic"]


@functools.lru_cache(maxsize=1)
def worker_identity():
    from .paths import worker_env
    result = subprocess.run([CONFIG['V4_PYTHON'], '-I', '-B', '-c',
                             'import json,sys; print(json.dumps({"version":sys.version,"cache_tag":sys.implementation.cache_tag}))'],
                            env=worker_env(), capture_output=True, text=True, timeout=8, check=True)
    metadata = json.loads(result.stdout)
    binary = Path(CONFIG['V4_PYTHON']).resolve()
    metadata.update(binary_path=str(binary), binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    return metadata


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
    temp.replace(path)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()

def immutable(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError('immutable_record_changed:' + path.name)
    else:
        # A controller lock serializes writers. Replace prevents partial JSON on interruption.
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        tmp.replace(path)
    return value

def strict_json(text, max_bytes=65536):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_JSON_key')
            result[key] = value
        return result
    if type(text) is not str or len(text.encode()) > max_bytes:
        raise ValueError('response_size')
    try:
        return json.loads(text, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_JSON')))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('invalid_JSON') from exc

def task_for(case):
    return prepare(case['source'], case['entry'], case['base'], valid_code=case['valid_code'])

def base_inputs(case):
    """Only public base calls, never evaluator witnesses or reference outputs."""
    calls = [n for n in ast.walk(ast.parse(case['base']))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == case['entry']]
    result = []
    for call in calls:
        if call.keywords:
            raise ValueError('keyword_base_call_unsupported')
        args = tuple(ast.literal_eval(n) for n in call.args)
        literal = literal_for_transport(args)
        if literal not in result:
            result.append(literal)
    if not result or len(result) > 3:
        raise ValueError('base_input_count')
    return result

def syntax_evidence(task):
    """AST statements/lexical parents only; no CFG, path feasibility or propagation claim."""
    tree = ast.parse(task['source_masked'])
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == task['entry'])
    rows = []

    def walk(node, guards):
        if isinstance(node, ast.stmt) and node is not fn:
            rows.append({'line': node.lineno, 'kind': type(node).__name__,
                         'text': ast.get_source_segment(task['source_masked'], node),
                         'lexical_enclosing_guards': guards})
        for child in ast.iter_child_nodes(node):
            extra = []
            if isinstance(node, (ast.If, ast.While)) and child in node.body + node.orelse:
                extra = [{'line': node.lineno, 'test': ast.unparse(node.test),
                          'body_or_else': 'body' if child in node.body else 'else'}]
            walk(child, guards + extra)
    walk(fn, [])
    if len(rows) > D['max_source_lines']:
        raise ValueError('statement_cap')
    return {'scope': 'syntactic AST statements and lexical guards; reach/flow not inferred',
            'statements': rows}

def observation(result):
    """Parse model prediction. Native PUT observations never become the spec oracle."""
    if result.startswith('exception:'):
        kind = result.split(':', 1)[1]
        if not kind.isidentifier() or len(kind) > 128:
            raise ValueError('exception_type')
        return ('exception', kind)
    return ('ok', typed_value(parse_literal(result, output=True)))

def native_observation(result):
    if not result.get('native_checked'):
        return None
    if result['status'] == 'exception':
        return ('exception', result['exception_type'])
    if result['status'] == 'ok' and result.get('output_repr') is not None:
        return observation(result['output_repr'])
    return None
