"""Small semantic diagnostic. JSON Schema checks shape, never semantic truth."""
import ast
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .chain_inputs import parse_arguments, parse_literal, literal_for_transport, typed_value
from .paths import CONFIG
from .source_view import prepare

D = CONFIG['diagnostic']
ARMS = tuple(D['arms'])


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


TEXT = {'type': 'string', 'maxLength': 2400}
NONEMPTY = dict(TEXT, minLength=1)
LINES = {'type': 'array', 'items': {'type': 'integer', 'minimum': 1},
         'uniqueItems': True, 'maxItems': 12}


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


SCHEMAS = {
    'concept': obj({'relation': NONEMPTY, 'domain': NONEMPTY, 'uncertainty': TEXT}),
    'behavior': obj({'summary': NONEMPTY, 'source_lines': LINES, 'limitations': TEXT}),
    'hypothesis': obj({'verdict': {'enum': ['mismatch', 'consistent', 'unknown']},
                       'required_relation': NONEMPTY, 'actual_relation': NONEMPTY,
                       'source_lines': LINES, 'trigger': TEXT,
                       'alternative': TEXT, 'reason': NONEMPTY}),
    'inputs': obj({'inputs': {'type': 'array', 'maxItems': D['round_inputs'],
                              'items': obj({'arguments': NONEMPTY, 'expected': NONEMPTY,
                                            'predicted_actual': NONEMPTY,
                                            'purpose': {'enum': ['trigger', 'contrast']}})},
                   'reason': NONEMPTY}),
}
VALIDATORS = {name: Draft202012Validator(schema) for name, schema in SCHEMAS.items()}


def validate(stage, text, task):
    value = strict_json(text)
    errors = sorted(VALIDATORS[stage].iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        e = errors[0]
        raise ValueError('schema:' + str(list(e.path)) + ':' + e.validator)
    if stage in ('hypothesis', 'behavior'):
        statements = {n['span'][0] for n in task['nodes']
                      if n['is_statement'] and n['execution_scope'] == 'function_body'}
        if any(line not in statements for line in value['source_lines']):
            raise ValueError('non_statement_source_line')
        if stage == 'hypothesis' and value['verdict'] == 'mismatch':
            if not value['source_lines'] or not value['trigger'].strip():
                raise ValueError('mismatch_requires_trigger_and_source')
    # Candidate literals/domain/predictions are checked individually by replay, so one bad
    # candidate cannot silently discard its valid siblings or escape the per-round budget.
    return value


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


def messages(stage, task, *, concept=None, behavior=None, hypothesis=None,
             evidence=None, previous=None, feedback=None):
    """Separate views; a spec-only concept extractor and a code-only behavior extractor."""
    system = ('Return exactly one JSON object matching the supplied schema. No Markdown. '
              'Do not invent source lines. Empty strings are permitted only where the schema '
              'allows them. Unknown intent must remain unknown. This is a diagnostic, not a '
              'request to force a bug claim. Tool facts have their stated scope.')
    if stage == 'concept':
        context = {'signature': task['signature'], 'spec': task['spec']}
        instruction = ('Extract one central normative behavioral relation from the spec, '
                       'including eligibility, quantifier, multiplicity or boundary if relevant. '
                       'State the original input domain separately. Record undefined intent '
                       'in uncertainty; do not invent requirements.')
        schema = SCHEMAS['concept']
    elif stage == 'behavior':
        context = {'code': task['source_masked'], 'syntax': syntax_evidence(task)}
        instruction = ('Describe actual returned behavior and guards from executable code. '
                       'The masked docstring is not a missing implementation. Distinguish '
                       'unused/unreachable local operations from returned effects. List the '
                       'relevant statement line numbers; imported semantics may be unknown.')
        schema = SCHEMAS['behavior']
    else:
        context = {'signature': task['signature'], 'spec': task['spec'],
                   'code': task['source_masked'], 'base_tests': task['base'],
                   'fixed_tool_evidence': evidence,
                   'model_behavior_claim': behavior}
        if concept is not None:
            context['model_concept_claim'] = concept
        if hypothesis is not None:
            context['model_hypothesis_claim'] = hypothesis
        if previous is not None:
            context['previous_proposal'] = previous
            context['execution_feedback'] = feedback
        if stage == 'hypothesis':
            instruction = ('Compare the normative requirement and actual behavior. Propose '
                           'at most one fault hypothesis. For mismatch give a feasible trigger '
                           'sufficient to distinguish outputs, not merely reach a line. Consider '
                           'an alternative and evidence against the hypothesis. Use consistent '
                           'when supported, unknown for ambiguous intent; do not infer a global '
                           'proof from finite examples. Source lines are statement numbers.')
            schema = SCHEMAS['hypothesis']
        else:
            instruction = ('Propose up to three concrete positional argument tuples to test '
                           'or challenge the supplied hypothesis. Give expected output from '
                           'the original spec and predicted actual output from code separately. '
                           'Write each tuple/output as a Python literal string; an exception '
                           'is exception:TypeName. A one-argument call requires (value,). '
                           'Include a contrast if useful; abstain with inputs=[] when expected '
                           'semantics are undefined. Respect the original domain. Do not use '
                           'PUT observations as the expected oracle. No code or strategies.')
            if stage == 'revision':
                instruction += (' Review all previous predictions and contrary evidence. '
                                'Propose additional inputs; earlier tests remain in the record. '
                                'No tools beyond the supplied fixed replay feedback are available.')
            schema = SCHEMAS['inputs']
    return [{'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps({'instruction': instruction,
                                                   'context': context, 'schema': schema},
                                                  ensure_ascii=False, sort_keys=True)}]
