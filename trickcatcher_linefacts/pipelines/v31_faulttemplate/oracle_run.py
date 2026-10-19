"""Oracle comparison on fixed input pools: exact expected (spec / spec+code) vs executable property vs metamorphic.

Order: freeze protocol -> fixed pool + PUT executions -> one Qwen call per (case, arm) -> evaluate model oracles on
PUT outputs -> generation freeze -> `score` with independent references only after the freeze.
Usage (repo root, PYTHONPATH=., QWEN_BASE_URL in env):
  $V4_PYTHON -m trickcatcher_linefacts.pipelines.v26_proporacle.oracle_run generate --cohort pilot20|diag16
  $V4_PYTHON -m trickcatcher_linefacts.pipelines.v26_proporacle.oracle_run score --cohort pilot20|diag16
"""
import argparse
import collections
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from jsonschema import Draft202012Validator

from . import flow_run, flow_tools, schemas, source_view
from .chain_inputs import literal_for_transport, parse_literal, typed_value
from .flow_common import digest, immutable
from .gen_inputs import sandbox
from .paths import CONFIG, DATA_OUT, REPO

O = CONFIG['oracle']
ARMS = tuple(O['arms'])
HERE = Path(__file__).resolve().parent
ROOT = DATA_OUT / 'oracle'
V21 = REPO / 'trickcatcher_linefacts/out/pipelines/v21_flowtools/humaneval/flowrun'
TEXT = {'type': 'string', 'maxLength': 4000}
NONEMPTY = dict(TEXT, minLength=1)


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


EXACT = obj({'expected': {'type': 'array', 'maxItems': O['pool_cap'], 'items': obj({'input_id': NONEMPTY, 'expected': NONEMPTY})},
             'reason': NONEMPTY})
SCHEMAS = {
    'exact_spec': EXACT, 'exact_code': EXACT,
    'property': obj({'properties': {'type': 'array', 'maxItems': O['max_properties'], 'items': obj({'id': NONEMPTY, 'description': NONEMPTY, 'code': NONEMPTY})},
                     'reason': NONEMPTY}),
    'metamorphic': obj({'relations': {'type': 'array', 'maxItems': O['max_relations'], 'items': obj({'id': NONEMPTY, 'description': NONEMPTY, 'code': NONEMPTY})},
                        'reason': NONEMPTY}),
}
VALIDATORS = {k: Draft202012Validator(v) for k, v in SCHEMAS.items()}
SYSTEM = ('Return exactly one JSON object matching the supplied schema. No Markdown outside the JSON. '
          'Base every answer on the specification. Unknown intent must remain unknown.')
INSTR = {
    'exact_spec': ('For each listed input give the output the SPECIFICATION requires, as a Python literal string; '
                   'exception:TypeName if the spec requires an error; unknown if the spec does not determine it.'),
    'exact_code': ('For each listed input give the output the SPECIFICATION requires (not necessarily what the code returns), '
                   'as a Python literal string; exception:TypeName if the spec requires an error; unknown if undetermined.'),
    'property': ('Write up to three executable properties that EVERY correct implementation of the specification satisfies, '
                 'each as Python code defining `def check(args, output, error):` where args is the positional argument tuple, '
                 'output the returned value (None if an exception was raised) and error the exception class name or None. '
                 'Return True when the observed result satisfies the property and False when it violates it. Capture the '
                 'central concept (for example counts, ordering, membership, bounds, eligibility, type), not a full '
                 're-implementation. Use only the standard library; no I/O.'),
    'metamorphic': ('Write up to two metamorphic relations implied by the specification, each as Python code defining '
                    '`def follow(args):` returning a NEW positional argument tuple in the same input domain, and '
                    '`def relation(args, output, args2, output2):` returning True when the two results are consistent '
                    'with the specification and False otherwise. Use only the standard library; no I/O.'),
}


ARRAY_FIELD = {'exact_spec': 'expected', 'exact_code': 'expected', 'property': 'properties', 'metamorphic': 'relations'}


STRICT = {
    'exact': (' Rules: (1) derive each value only from the specification and its examples, never from what the code does; '
              '(2) the literal must have the exact Python type the specification and signature require (for example a '
              'string result is written with quotes, \'22\' not 22; a float as 2.0); (3) work through each input carefully '
              'before answering; (4) answer unknown only when the specification truly leaves the result open.'),
    'property': (' Rules: (1) each property must hold for EVERY valid input: if it is about a special case (empty input, '
                 'single element, ties, ...), first test that condition on args and return True when it does not apply; '
                 '(2) constrain the relation between args and output, never the inputs alone (invalid inputs are already '
                 'filtered); (3) add nothing that the specification does not state, including examples you only infer; '
                 '(4) use only names defined inside the function (args, output, error) and the standard library; '
                 '(5) if the specification requires an exception, check error; otherwise return False when error is not None.'),
    'metamorphic': (' Rules: (1) follow must return a tuple of the same arity that stays inside the documented input domain; '
                    '(2) the relation must be implied by the specification for EVERY valid input, including edge cases; '
                    '(3) add nothing the specification does not state; (4) use only the given parameters and the standard library.'),
}


def instruction(arm, variant):
    text = INSTR[arm]
    if variant == 'strict':
        text += STRICT['exact' if arm.startswith('exact') else arm]
    return text


def validate(stage, text):
    # Arm-neutral format rule: a bare JSON array (raw or in one fence) is wrapped as {<array field>: [...], reason}.
    try:
        value, _ = schemas.extract(text)
    except schemas.ArtifactError as exc:
        if str(exc) != 'object_required':
            raise ValueError('extract:' + str(exc)) from None
        body = text.strip()
        if body.startswith('```'):
            body = body.split('\n', 1)[1].rsplit('```', 1)[0]
        array = flow_run.strict_json(body)
        if type(array) is not list:
            raise ValueError('extract:object_required') from None
        value = {ARRAY_FIELD[stage]: array, 'reason': 'wrapped_bare_array'}
    errors = sorted(VALIDATORS[stage].iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        raise ValueError('schema:' + str(list(errors[0].path)) + ':' + errors[0].validator)
    return value


def v21_inputs(cohort_name, case_id):
    out = []
    for p in sorted((V21 / cohort_name / 'cases' / case_id / 'arms').glob('*/result.json')):
        for ex in json.loads(p.read_text()).get('final_executions') or []:
            if ex.get('status') == 'ok' and ex.get('input'):
                out.append(ex['input'])
    return out


def observation(view):
    """PUT result of an admissible, natively checked execution -> ('ok', typed) / ('exception', name) / None."""
    if view['execution_status'] == 'exception':
        return ('exception', view['exception_type'])
    if view['execution_status'] == 'ok' and view.get('output') is not None:
        return ('ok', typed_value(parse_literal(view['output'], output=True)))
    return None


class Run:
    def __init__(self, name, client=None, model='qwen', variant='original'):
        self.name, self.client, self.model, self.variant = name, client, model, variant
        self.root = ROOT / f'{model}_{variant}' / name
        self.cases = flow_run.cohort(name)

    def protocol(self):
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir())
                 if p.is_file() and p.suffix in ('.py', '.json', '.jinja', '.md') and p.name != 'CHANGELOG.md'}
        return immutable(self.root / 'protocol.json', dict(cohort=self.name, arms=list(ARMS), sources=files, oracle=O, variant=self.variant,
                                                         model=CONFIG['codex'] if self.model == 'codex' else CONFIG['flowrun']['model'], cases=[c['case_id'] for c in self.cases],
                                                         scope='references only in `score`, after generation_frozen.json'))

    def pool(self, case, task):
        arity = task['arity']
        first, rest = [], []
        for text in case['witnesses'] + flow_run.calls_in(case['base'], {case['entry'], 'candidate', 'f'}):
            try:
                lit = literal_for_transport(flow_tools.parse_call(text, arity))
            except (ValueError, TypeError):
                continue
            if lit not in first:
                first.append(lit)
        for text in v21_inputs(self.name, case['case_id']):
            try:
                lit = literal_for_transport(flow_tools.parse_call(text, arity))
            except (ValueError, TypeError):
                continue
            if lit not in first and lit not in rest:
                rest.append(lit)
        rest.sort(key=lambda s: hashlib.sha256(s.encode()).hexdigest())  # fixed selector, independent of outcomes
        return (first + rest)[:O['pool_cap']]

    def execute(self, task, executor, literal):
        ordinary, traced = executor.run(literal)
        if ordinary.get('status') == 'filtered':
            return dict(input=literal, admissible=False)
        if not flow_tools.native_checked(ordinary, traced):
            return dict(input=literal, admissible=True, checked=False)
        return dict(input=literal, admissible=True, checked=True, execution_status=ordinary['status'],
                    exception_type=ordinary.get('exception_type'), output=ordinary.get('output_repr'))

    def model_code(self, directory, code, mode, **kw):
        key = digest(dict(code=code, mode=mode, **kw))
        d = Path(directory) / key
        jp, op = d / 'job.json', d / 'result.json'
        if not op.exists():
            immutable(jp, dict(code=code, mode=mode, timeout=O['property_timeout'], **kw))
            try:
                sandbox(CONFIG['V4_PYTHON'], HERE / 'prop_worker.py', jp, op, O['property_timeout'] + 6)
            except RuntimeError:
                immutable(op, dict(status='error', error='isolated_worker_failed'))
        return json.loads(op.read_text())

    def case(self, case):
        base = self.root / 'cases' / case['case_id']
        done = base / 'oracles.json'
        if done.exists():
            return json.loads(done.read_text())
        task = source_view.prepare(case['source'], case['entry'], case['base'], valid_code=case['valid_code'])
        executor = flow_tools.Executor(task, base / 'executions')
        rows = [self.execute(task, executor, lit) for lit in self.pool(case, task)]
        usable = [r for r in rows if r['admissible'] and r.get('checked')]
        for i, r in enumerate(usable):
            r['id'] = f'I{i + 1}'
        inputs = [dict(id=r['id'], arguments=r['input']) for r in usable]
        seed = O['seed'] + int(hashlib.sha256(case['case_id'].encode()).hexdigest()[:6], 16)
        record = dict(case_id=case['case_id'], pool=rows, arms={})
        for k, arm in enumerate(ARMS):
            ctx = dict(signature=task['signature'], spec=task['spec'], base_tests=task['base'])
            if arm.startswith('exact'):
                ctx['inputs'] = inputs
            if arm == 'exact_code':
                ctx['code'] = flow_run.numbered(task)
            messages = [{'role': 'system', 'content': SYSTEM},
                        {'role': 'user', 'content': json.dumps(dict(instruction=instruction(arm, self.variant), context=ctx, schema=SCHEMAS[arm]), ensure_ascii=False, sort_keys=True)}]
            arec = dict(verdicts={}, error=None)
            if arm.startswith('exact') and not inputs:
                arec['error'] = 'no_admissible_inputs'
                record['arms'][arm] = arec
                continue
            response = self.client.complete(dict(slot=f"{self.name}/{case['case_id']}/{arm}-{digest(messages)[:16]}", stage=arm, seed=seed + k, messages=messages))
            arec.update(input_tokens=response['input_tokens'], output_tokens=response['output_tokens'])
            try:
                value = validate(arm, response['text'])
            except ValueError as exc:
                arec['error'] = str(exc)
                record['arms'][arm] = arec
                continue
            arec['value'] = value
            arec['verdicts'] = self.verdicts(arm, value, usable, task, executor, base / 'model_code')
            record['arms'][arm] = arec
        immutable(done, record)
        return record

    def verdicts(self, arm, value, usable, task, executor, code_dir):
        out = {}
        if arm.startswith('exact'):
            given = {e['input_id']: e['expected'] for e in value['expected']}
            for r in usable:
                text = given.get(r['id'], 'unknown').strip()
                exp = None if text == 'unknown' else flow_run.parse_expected(text)
                put = observation(r)
                if exp is None or put is None:
                    out[r['input']] = dict(verdict='unknown')
                else:
                    out[r['input']] = dict(verdict='ok' if flow_run.same(exp, put) else 'bug', expected=text)
            return out
        if arm == 'property':
            for r in usable:
                results = []
                for p in value['properties']:
                    res = self.model_code(code_dir, p['code'], 'property', args_repr=r['input'],
                                          output_repr=r['output'] if r['execution_status'] == 'ok' else None,
                                          error=r['exception_type'] if r['execution_status'] == 'exception' else None)
                    results.append(dict(id=p['id'], status=res['status'], result=res.get('result')))
                ok = [x['result'] for x in results if x['status'] == 'ok']
                out[r['input']] = dict(verdict='bug' if False in ok else 'ok' if ok else 'unknown', checks=results)
            return out
        for r in usable:  # metamorphic
            results = []
            for m in value['relations']:
                f = self.model_code(code_dir, m['code'], 'follow', args_repr=r['input'])
                if f['status'] != 'ok' or not f.get('args2_repr'):
                    results.append(dict(id=m['id'], status='follow_error'))
                    continue
                try:
                    lit2 = literal_for_transport(flow_tools.parse_call(f['args2_repr'], task['arity']))
                except (ValueError, TypeError):
                    results.append(dict(id=m['id'], status='follow_not_valid_tuple'))
                    continue
                r2 = self.execute(task, executor, lit2)
                if not r2['admissible'] or not r2.get('checked') or r2['execution_status'] != 'ok' or r['execution_status'] != 'ok':
                    results.append(dict(id=m['id'], status='followup_inadmissible_or_exception', args2=lit2))
                    continue
                res = self.model_code(code_dir, m['code'], 'relation', args_repr=r['input'], output_repr=r['output'],
                                      args2_repr=lit2, output2_repr=r2['output'])
                results.append(dict(id=m['id'], status=res['status'], result=res.get('result'), args2=lit2))
            ok = [x['result'] for x in results if x['status'] == 'ok']
            out[r['input']] = dict(verdict='bug' if False in ok else 'ok' if ok else 'unknown', checks=results)
        return out

    def generate(self, workers):
        self.protocol()
        if (self.root / 'generation_frozen.json').exists():
            print('generation already frozen')
            return
        failures = []

        def one(case):
            try:
                rec = self.case(case)
                print('case', case['case_id'], {a: (r.get('error') or sum(v['verdict'] == 'bug' for v in r['verdicts'].values())) for a, r in rec['arms'].items()}, flush=True)
            except Exception as exc:
                failures.append([case['case_id'], type(exc).__name__, str(exc)[:200]])
                print('FAILED', case['case_id'], type(exc).__name__, str(exc)[:200], flush=True)
        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(one, self.cases))
        if failures:
            raise SystemExit(f'{len(failures)} cases failed; rerun to resume; not frozen')
        files = sorted(p for p in (self.root / 'cases').rglob('oracles.json'))
        immutable(self.root / 'generation_frozen.json', {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        print('generation frozen')


def score(run):
    frozen_path = run.root / 'generation_frozen.json'
    if not frozen_path.exists():
        raise SystemExit('generation not frozen')
    for rel, h in json.loads(frozen_path.read_text()).items():
        if hashlib.sha256((run.root / rel).read_bytes()).hexdigest() != h:
            raise SystemExit('frozen artifact changed: ' + rel)
    reference = flow_run.Reference(run)
    rows = []
    soundness = collections.Counter()
    for case in run.cases:
        rec = json.loads((run.root / 'cases' / case['case_id'] / 'oracles.json').read_text())
        truth = {}
        for r in rec['pool']:
            if r['admissible'] and r.get('checked'):
                put, ref = observation(r), reference(case, r['input'])
                truth[r['input']] = None if put is None or ref is None else not flow_run.same(put, ref)
        any_disc = any(truth.values())
        verdict_sets = {}
        for arm in ARMS:
            a = rec['arms'][arm]
            c = collections.Counter()
            flagged = set()
            for lit, v in a['verdicts'].items():
                t = truth.get(lit)
                if arm == 'metamorphic' and v['verdict'] == 'bug':
                    # A relation violation is real if the PUT differs from the reference on the input or any follow-up.
                    seconds = [x['args2'] for x in v.get('checks', []) if x.get('result') is False and x.get('args2')]
                    t2 = [reference(case, s2) for s2 in seconds]
                    t = bool(t) or any(_disc2(run, case, s2, ref2) for s2, ref2 in zip(seconds, t2))
                if t is None:
                    c['unscored'] += 1
                    continue
                if v['verdict'] == 'bug':
                    flagged.add(lit)
                    c['tp' if t else 'false_alarm'] += 1
                elif v['verdict'] == 'ok':
                    c['missed' if t else 'tn'] += 1
                else:
                    c['unknown_disc' if t else 'unknown_nodisc'] += 1
            verdict_sets[arm] = flagged
            rows.append(dict(case_id=case['case_id'], arm=arm, error=a.get('error'), any_disc=any_disc,
                             disc_inputs=sum(1 for x in truth.values() if x), inputs=len(truth),
                             input_tokens=a.get('input_tokens', 0), output_tokens=a.get('output_tokens', 0), **c))
            if arm == 'property' and a.get('value'):
                for p in a['value']['properties']:
                    for r in rec['pool']:
                        if not (r['admissible'] and r.get('checked')):
                            continue
                        ref = reference(case, r['input'])
                        if ref is None:
                            continue
                        res = run_model_code(run, case, p['code'], r['input'], ref)
                        soundness['property_checks_on_reference'] += 1
                        soundness['fails_on_reference'] += res.get('status') == 'ok' and res.get('result') is False
                        soundness['errors_on_reference'] += res.get('status') != 'ok'
        for name, combine in (('consensus_exact_code_property', lambda a, b: a & b), ('union_exact_code_property', lambda a, b: a | b)):
            flagged = combine(verdict_sets['exact_code'], verdict_sets['property'])
            c = collections.Counter()
            for lit in flagged:
                if truth.get(lit) is not None:
                    c['tp' if truth[lit] else 'false_alarm'] += 1
            rows.append(dict(case_id=case['case_id'], arm=name, any_disc=any_disc, secondary=True, **c))
    summary = {}
    for arm in list(ARMS) + ['consensus_exact_code_property', 'union_exact_code_property']:
        rs = [r for r in rows if r['arm'] == arm]
        tp, fa = sum(r.get('tp', 0) for r in rs), sum(r.get('false_alarm', 0) for r in rs)
        summary[arm] = dict(tasks_confirmed=sum(1 for r in rs if r.get('tp')), tasks_false_alarm=sum(1 for r in rs if r.get('false_alarm')),
                            tp=tp, false_alarms=fa, precision=round(tp / (tp + fa), 3) if tp + fa else None,
                            missed=sum(r.get('missed', 0) for r in rs), unknown_on_disc=sum(r.get('unknown_disc', 0) for r in rs),
                            schema_errors=sum(1 for r in rs if r.get('error') and r['error'] != 'no_admissible_inputs'),
                            input_tokens=sum(r.get('input_tokens', 0) for r in rs), output_tokens=sum(r.get('output_tokens', 0) for r in rs))
    pool = dict(tasks=len(run.cases), tasks_with_disc=len({r['case_id'] for r in rows if r['any_disc']}),
                inputs=sum(r['inputs'] for r in rows if r['arm'] == ARMS[0]), disc_inputs=sum(r['disc_inputs'] for r in rows if r['arm'] == ARMS[0]))
    report = dict(cohort=run.name, scope='fixed pools; post-freeze independent references; descriptive (small n, K=1)',
                  pool=pool, arms=summary, property_soundness=dict(soundness), rows=rows)
    immutable(run.root / 'score.json', report)
    print(json.dumps(dict(pool=pool, arms=summary, property_soundness=dict(soundness)), indent=1))
    return report


def _disc2(run, case, literal, ref):
    task = source_view.prepare(case['source'], case['entry'], case['base'], valid_code=case['valid_code'])
    r = run_put(run, case, task, literal)
    put = observation(r) if r.get('admissible') and r.get('checked') else None
    return put is not None and ref is not None and not flow_run.same(put, ref)


def run_put(run, case, task, literal):
    executor = flow_tools.Executor(task, run.root / 'cases' / case['case_id'] / 'executions')
    return Run.execute(run, task, executor, literal)


def run_model_code(run, case, code, literal, ref):
    out = ref[1] if ref[0] == 'ok' else None
    output_repr = None if ref[0] != 'ok' else repr(_untyped(out))
    return Run.model_code(run, run.root / 'reference_soundness', code, 'property', args_repr=literal, output_repr=output_repr,
                          error=ref[1] if ref[0] == 'exception' else None)


def _untyped(t):
    kind, v = t
    if kind in ('list', 'tuple'):
        items = [_untyped(x) for x in v]
        return items if kind == 'list' else tuple(items)
    if kind in ('set', 'frozenset'):
        items = {_untyped(x) for x in v}
        return items if kind == 'set' else frozenset(items)
    if kind == 'dict':
        return {_untyped(k): _untyped(x) for k, x in v}
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=('generate', 'score'))
    ap.add_argument('--cohort', choices=('diag16', 'pilot20'), required=True)
    ap.add_argument('--model', choices=('qwen', 'codex'), required=True)
    ap.add_argument('--variant', choices=('original', 'strict'), required=True)
    ap.add_argument('--workers', type=int)
    args = ap.parse_args()
    run = Run(args.cohort, model=args.model, variant=args.variant)
    if args.command == 'generate':
        if args.model == 'codex':
            from .codex_client import CodexClient
            run.client = CodexClient(run.root / 'transport')
        else:
            from .flow_client import Client
            run.client = Client(run.root / 'transport')
        try:
            run.generate(args.workers or (CONFIG['codex']['workers'] if args.model == 'codex' else CONFIG['flowrun']['workers']))
        finally:
            run.client.close()
    else:
        score(run)


if __name__ == '__main__':
    main()
