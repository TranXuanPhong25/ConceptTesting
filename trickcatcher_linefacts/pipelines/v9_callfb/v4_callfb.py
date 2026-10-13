"""Literal-call discovery for hybrid round two; no generated code runs here."""
import ast
import json
import random
import re
from pathlib import Path
from . import gen_prompts, preconditions, v4_prompts

SEED_BASE = 1_600_000_000
SYSTEM = 'Write concrete Python function calls with literal arguments.'


def seed(task, arm, sample, stage=1, request=0, retry=0):
    if not (0 <= task < 1000 and 0 <= sample < 1000 and stage in (1, 2, 3)
            and 0 <= request < 16 and 0 <= retry < 3):
        raise ValueError('v9 seed indices out of range')
    return SEED_BASE + ((task * len(v4_prompts.ARMS) + v4_prompts.ARMS.index(arm))
                        * 1000 + sample) * 256 + stage * 64 + request * 4 + retry


def messages(task, fact, round1):
    instruction = ('reach the hint below' if fact else 'explore inputs beyond the existing tests')
    body = (f'Write exactly 5 concrete calls to {task["entry"]} that {instruction}. '
            'Use literal arguments only, one call per line in a Python code block. '
            'Do not write assertions, strategies, helpers, imports or expressions in arguments. '
            'Every input must satisfy the specification.\n\nSPECIFICATION:\n'
            + preconditions.specification(task)[0] + '\n\nPUT:\n' + task['put']
            + '\n\nBASE TESTS:\n' + task['base']
            + '\n\nROUND-1 ASSERTIONS:\n' + '\n'.join(round1))
    if fact:
        body += '\n\nHINT:\n' + fact['text']
    return gen_prompts.messages(SYSTEM, body)


def literal_call(source, task):
    """Bind literal kwargs/defaults using the source signature, without loading PUT."""
    node = ast.parse(source, mode='eval').body
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != task['entry']:
        raise ValueError('expected a direct entry call')
    fn = next(n for n in ast.parse(task['put']).body
              if isinstance(n, ast.FunctionDef) and n.name == task['entry'])
    params = fn.args.posonlyargs + fn.args.args
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs:
        raise ValueError('unsupported signature')
    if len(node.args) > len(params):
        raise ValueError('too many arguments')
    bound = {p.arg: ast.literal_eval(v) for p, v in zip(params, node.args)}
    for kw in node.keywords:
        if kw.arg is None or kw.arg not in {p.arg for p in fn.args.args} or kw.arg in bound:
            raise ValueError('invalid keyword argument')
        bound[kw.arg] = ast.literal_eval(kw.value)
    for p, default in zip(params[len(params)-len(fn.args.defaults):], fn.args.defaults):
        if p.arg not in bound:
            bound[p.arg] = ast.literal_eval(default)
    if set(bound) != {p.arg for p in params}:
        raise ValueError('missing argument')
    args = tuple(bound[p.arg] for p in params)
    literal = repr(args)
    if len(literal) > 1000:
        raise ValueError('input exceeds 1000 characters')
    ast.literal_eval(literal)
    return dict(input_repr=literal, call=task['entry']+'('+', '.join(map(repr, args))+')')


def extract_calls(text, task):
    blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', text, re.S)
    lines = [s.strip() for s in ('\n'.join(blocks) if blocks else text).splitlines()
             if s.strip() and not s.lstrip().startswith('#')]
    entries, candidates = [], []
    for i, source in enumerate(lines[:5]):
        entry = dict(index=i, proposed_call=source)
        try:
            candidate = literal_call(source, task)
            candidates.append(candidate)
            entry.update(candidate)
        except (SyntaxError, ValueError, TypeError) as exc:
            entry['parse_error'] = f'{type(exc).__name__}: {exc}'
        entries.append(entry)
    return dict(candidates=candidates, entries=entries,
                errors=[] if len(lines) == 5 else [f'Expected 5 calls; received {len(lines)}.'])


def trigger_condition(task, fact, path=None):
    # v7 changed the validator/fact pool. Do not transfer historical conditions
    # without their v3m2 provenance; v7 conditions may be omitted by design.
    if not fact or task.get('facts_version') != 'v3m2':
        return None
    path = Path(path) if path else Path(__file__).resolve().parents[2] / 'out/trigger_conditions/conditions.json'
    if not path.exists():
        return None
    for row in json.loads(path.read_text()):
        if row['task'] == task['task'] and row['text'] == fact['text']:
            condition = row.get('lib')
            if condition and condition['status'] == 'derived':
                return 'inputs satisfying ' + ' AND '.join(condition['descs']) + ' reach it'
    return None


def feedback(generated, flagged, fact, condition=None):
    by_input = {r['input_repr']: r for r in flagged['records']}
    rows = []
    for entry in generated['entries']:
        row = dict(call=entry.get('call', entry['proposed_call']))
        if fact:
            row.update(reached_site=None, local_behavior_differs=None, output_differs=None)
        record = by_input.get(entry.get('input_repr'))
        if record is None:
            row.update(valid=False, violated_condition=entry.get('parse_error') or
                       flagged['summary'].get('first_contract_message') or 'classification failed')
        else:
            row.update(valid=record['valid'], violated_condition=record.get('contract_error'),
                       trace_error=record.get('trace_error'), feedback_error=record.get('feedback_error'))
            if fact:
                row.update(record.get('feedback', {}).get('hint', {
                    'reached_site': None, 'local_behavior_differs': None, 'output_differs': None}))
                row['hint_hit'] = record['shown_hits'][0]
            else:
                row['output_new_vs_round1'] = record.get('feedback', {}).get('output_new_vs_round1')
        if fact and condition:
            row['input_trigger_condition'] = condition
        rows.append(row)
    payload = dict(calls=rows, protocol_errors=generated['errors'])
    return payload, ('Sandbox feedback:\n' + json.dumps(payload, ensure_ascii=False)
                     + '\nWrite exactly 5 revised concrete literal calls in a Python code block.')


def discover(task, arm, sample, round1, missed, shown, query, classify, directory,
             python, round1_outputs=(), matched_schedule=None):
    """Target arms try at most three times; plain replays the proposal schedule."""
    attempts, summaries, selected, schedule = [], [], [], []
    groups = matched_schedule if matched_schedule is not None else [3] * len(missed)
    for request, limit in enumerate(groups):
        fact = None if matched_schedule is not None else shown[missed[request]]
        conversation = messages(task, fact, round1)
        pool = {}
        used = 0
        for retry in range(limit):
            try:
                raw = query(conversation, 1, request, retry, f'calls_{request}_{retry}', True)
            except RuntimeError as exc:
                # The endpoint rejects over-long conversations (HTTP 400, context length). Record the
                # request as made and stop this hint's loop; nothing is kept from it. (Amendment 1.)
                if 'HTTP 400' not in str(exc):
                    raise
                used += 1
                attempts.append(dict(request=request, retry=retry, fact_index=missed[request] if fact else None,
                                     generated=None, summary=None, feedback=None, error='request rejected: HTTP 400'))
                break
            used += 1
            generated = extract_calls(raw, task)
            flagged = classify(task, directory/f'request_{request}_{retry}', python,
                               candidates=generated['candidates'], shown=[fact] if fact else [],
                               requested_draws=5, feedback=True, reference_outputs=round1_outputs)
            summaries.append(flagged['summary'])
            for record in flagged['records']:
                if record['valid'] and (fact is None or record['shown_hits'][0]):
                    pool[record['input_repr']] = record
            payload, correction = feedback(generated, flagged, fact, trigger_condition(task, fact))
            attempts.append(dict(request=request, retry=retry,
                                 fact_index=missed[request] if fact else None,
                                 generated=generated, summary=flagged['summary'], feedback=payload))
            if matched_schedule is None and len(pool) >= 2:
                break
            conversation += [dict(role='assistant', content=raw), dict(role='user', content=correction)]
        schedule.append(used)
        good = list(pool.values())
        picked = random.Random(seed(task['task'], arm, sample, 3, request)).sample(good, min(2, len(good)))
        attempts[-1]['selected'] = picked
        selected += picked
    return dict(selected=list({r['input_repr']: r for r in selected}.values()), attempts=attempts,
                summaries=summaries, schedule=schedule, count=sum(schedule))


def oracle_messages(task, selected):
    body = (prompts_head(task) + '\nFor each call below write `assert <call> == <expected>`; '
            'do not add other assertions. Expected values must follow the specification. '
            'Use a single Python code block with one assertion per call.\n'
            + '\n'.join(r['call'] for r in selected))
    return gen_prompts.messages('You are an expert software tester.', body)


def prompts_head(task):
    return 'SPECIFICATION:\n' + preconditions.specification(task)[0] + '\n\nPUT:\n' + task['put'] + '\n\nBASE TESTS:\n' + task['base']


def strict_assertions(text, task, selected, *, missing=None):
    """Only direct equality assertions over kept literal calls and literal values."""
    kept = {r['input_repr'] for r in selected}
    blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', text, re.S)
    accepted = {}
    for line in ('\n'.join(blocks) if blocks else text).splitlines():
        try:
            tree = ast.parse(line.strip())
            if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assert) or tree.body[0].msg:
                continue
            expr = tree.body[0].test
            if not isinstance(expr, ast.Compare) or len(expr.ops) != 1 or not isinstance(expr.ops[0], ast.Eq):
                continue
            candidate = literal_call(ast.unparse(expr.left), task)
            expected = ast.literal_eval(expr.comparators[0])
            if candidate['input_repr'] in kept:
                accepted.setdefault(candidate['input_repr'], f'assert {candidate["call"]} == {expected!r}')
        except (SyntaxError, ValueError, TypeError):
            pass
    # As in v8-strict, preserve discovery even if the expected-value completion
    # omits a kept call. Explicit None placeholders are recorded, never claimed
    # as model-written or correct expected values; ref scoring replaces them.
    result = []
    for record in selected:
        key = record['input_repr']
        if key not in accepted:
            if missing is not None:
                missing.append(record['call'])
            accepted[key] = f'assert {record["call"]} == None'
        result.append(accepted[key])
    return list(dict.fromkeys(result))
