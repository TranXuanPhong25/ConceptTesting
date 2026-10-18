"""Online flowtools run: shared concept/behavior/hypothesis stages, common discovery, 9 LLM arms + witness-only.

Order: freeze protocol -> per case shared stages (frozen) -> common witnesses -> arms (3 calls each) -> generation
freeze -> scoring with independent references (fixture oracles / HumanEval+ canonical) only after the freeze.
Usage (repo root, PYTHONPATH=., QWEN_BASE_URL in env):
  $V4_PYTHON -m trickcatcher_linefacts.pipelines.v21_flowtools.flow_run generate --cohort diag16|pilot20
  $V4_PYTHON -m trickcatcher_linefacts.pipelines.v21_flowtools.flow_run score --cohort diag16|pilot20
"""
import argparse
import ast
import collections
import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading

from jsonschema import Draft202012Validator

from . import flow_packages, flow_tools, pilot_fixtures, fixture_oracles, schemas, source_view
from .chain_inputs import literal_for_transport, parse_arguments, parse_literal, typed_value
from .flow_common import digest, immutable, strict_json
from .gen_inputs import sandbox
from .paths import CONFIG, DATA_OUT, REPO, dataset_paths

R = CONFIG['flowrun']
HERE = Path(__file__).resolve().parent
ROOT = DATA_OUT / 'flowrun'
LLM_ARMS = flow_packages.LLM_ARMS
TEXT = {'type': 'string', 'maxLength': 2400}
NONEMPTY = dict(TEXT, minLength=1)
LINES = {'type': 'array', 'items': {'type': 'integer', 'minimum': 1}, 'uniqueItems': True, 'maxItems': 12}


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


SCHEMAS = {
    'concept': obj({'relation': NONEMPTY, 'domain': NONEMPTY, 'uncertainty': TEXT}),
    'behavior': obj({'summary': NONEMPTY, 'source_lines': LINES, 'limitations': TEXT}),
    'hypothesis': obj({'hypotheses': {'type': 'array', 'maxItems': R['max_hypotheses'], 'items': obj({
        'verdict': {'enum': ['mismatch', 'consistent', 'unknown']}, 'required_relation': NONEMPTY, 'actual_relation': NONEMPTY,
        'source_lines': LINES, 'trigger': TEXT, 'alternative': TEXT, 'reason': NONEMPTY})}, 'reason': NONEMPTY}),
    'probe': obj({'inputs': {'type': 'array', 'maxItems': R['round_inputs'], 'items': obj({
        'arguments': NONEMPTY, 'expected': NONEMPTY, 'predicted_actual': NONEMPTY, 'purpose': {'enum': ['trigger', 'contrast']}})},
        'reason': NONEMPTY}),
    'agent': obj({'actions': {'type': 'array', 'maxItems': CONFIG['flowtools']['actions_per_round'], 'items': {'type': 'object'}},
                  'reason': NONEMPTY}),
    'final': obj({'tests': {'type': 'array', 'maxItems': R['final_tests'], 'items': obj({'arguments': NONEMPTY, 'expected': NONEMPTY})},
                  'reason': NONEMPTY}),
}
VALIDATORS = {k: Draft202012Validator(v) for k, v in SCHEMAS.items()}
SYSTEM = ('Return exactly one JSON object matching the supplied schema. No Markdown. Do not invent source lines. '
          'Unknown intent must remain unknown. Do not assume the code is buggy. Tool facts hold only within their stated scope; '
          'observed outputs of the code under test are not expected values.')


def validate(stage, text):
    # Whole-text JSON, or exactly one ```json fenced object with no other JSON outside (ported v21 schemas.extract).
    try:
        value, _ = schemas.extract(text)
    except schemas.ArtifactError as exc:
        raise ValueError('extract:' + str(exc)) from None
    errors = sorted(VALIDATORS[stage].iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        raise ValueError('schema:' + str(list(errors[0].path)) + ':' + errors[0].validator)
    return value


# ---- cohorts ---------------------------------------------------------------------------------------------------
def calls_in(base, names):
    out = []
    try:
        tree = ast.parse(base)
    except SyntaxError:
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in names and not n.keywords:
            try:
                literal = literal_for_transport(tuple(ast.literal_eval(a) for a in n.args))
            except (ValueError, TypeError, SyntaxError):
                continue
            if literal not in out:
                out.append(literal)
    return out


def cohort(name):
    if name == 'diag16':
        rows = []
        for c in pilot_fixtures.cases():
            rows.append(dict(case_id=c['fixture_id'], source=c['source'], entry=c['entry'], base=c['base'], valid_code=c['valid_code'],
                             witnesses=calls_in(c['base'], {'f'})[:R['common_witnesses']], reference=dict(kind='fixture', case=c)))
        return rows
    if name == 'pilot20':
        paths = dataset_paths()
        bundle = json.loads((REPO / 'trickcatcher_linefacts/out/pipelines/v7/humaneval/tasks_hybrid.json').read_text())
        hep = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, paths['oracle_hep'].read_text().splitlines())}
        rows = []
        for t in bundle['tasks']:
            if t['split'] != 'pilot':
                continue
            n = int(t['task'])
            source = (paths['puts'] / f'HumanEval_{n}' / 'put0.py').read_text()
            witnesses = []
            for call in t['tool_inputs'] or []:  # frozen v7 fuzz witnesses, stored order (no outcome selection)
                for literal in calls_in(call, {t['entry']}):
                    if literal not in witnesses:
                        witnesses.append(literal)
            ref = hep[n]
            rows.append(dict(case_id=str(n), source=source, entry=t['entry'], base=t['base'], valid_code=t['mined_valid_src'],
                             witnesses=witnesses[:R['common_witnesses']],
                             reference=dict(kind='canonical', source=ref['prompt'] + ref['canonical_solution'], entry=ref['entry_point'])))
        if len(rows) != 20:
            raise ValueError('pilot20_size')
        return rows
    if name == 'vibepass':
        root = REPO / CONFIG['vibepass']['root']
        plus = {int(r['task_id'].split('/')[1]): r for r in map(json.loads, (root / 'humaneval_mbpp_plus.jsonl').read_text().splitlines())}
        rows = []
        for n in json.loads((root / 'tasks.json').read_text())['heldout']:
            r = plus[n]
            source = (root / 'PUTs' / f'HumanEval_{n}' / 'put0.py').read_text()
            witnesses = []
            for args in r['base_input']:  # public examples only; no evaluator inputs
                try:
                    lit = literal_for_transport(tuple(args))
                except (ValueError, TypeError):
                    continue
                if lit not in witnesses:
                    witnesses.append(lit)
            rows.append(dict(case_id=str(n), source=source, entry=r['entry_point'], base=r['test'], valid_code=None,
                             witnesses=witnesses[:R['common_witnesses']],
                             reference=dict(kind='canonical', source=r['prompt'] + r['canonical_solution'], entry=r['entry_point'],
                                            contract=r['prompt'] + r['contract'] + '\n    pass\n')))
        if len(rows) != 66:
            raise ValueError('vibepass_size')
        return rows
    raise ValueError('cohort')


# ---- prompts -----------------------------------------------------------------------------------------------------
def numbered(task):
    return '\n'.join(f'{i + 1:>3}| {line}' for i, line in enumerate(task['source_masked'].split('\n')) if line.strip())


def structure(session):
    cfg = session.cfg
    if not cfg['supported']:
        return dict(status='unsupported', reasons=cfg['unsupported'])
    cd = cfg['control_dependence']
    rows = [dict(id=session.forward[n], kind=r['kind'], code=session._header(r), reachable=r['reachable'],
                 depends_on=[dict(source=session.forward.get(d['source'], d['source']), branch=d['label']) for d in cd.get(n, [])] if cd is not None else 'unknown',
                 limits=r['limits']) for n, r in sorted(cfg['nodes'].items(), key=lambda kv: kv[1]['span'][:2])]
    return dict(status='ok', scope='static normal-flow structure of the entry function; ids are L<line> statement aliases',
                statements=rows[:CONFIG['flowtools']['max_nodes']])


def message(instruction, context, stage):
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': json.dumps({'instruction': instruction, 'context': context, 'schema': SCHEMAS[stage]},
                                                   ensure_ascii=False, sort_keys=True)}]


INSTR = {
    'concept': ('Extract one central normative behavioral relation from the spec, including eligibility, quantifier, multiplicity or '
                'boundary if relevant. State the original input domain separately. Record undefined intent in uncertainty.'),
    'behavior': ('Describe the actual returned behavior and guards of the executable code. The masked docstring is not missing code. '
                 'Distinguish unused or unreachable operations from returned effects. List relevant statement line numbers.'),
    'hypothesis': ('Compare the normative requirement and the actual behavior. Give at most two hypotheses. For mismatch give a '
                   'feasible trigger sufficient to distinguish outputs, not merely reach a line, and the source lines involved. '
                   'Consider an alternative explanation. Use consistent when supported and unknown for ambiguous intent.'),
    'probe': ('Propose up to six concrete positional argument tuples that could expose a difference between what the spec requires '
              'and what the code does. For each give the expected output required by the spec and the predicted actual output of '
              'the code separately. Write tuples/outputs as Python literal strings; an exception is exception:TypeName; a '
              'one-argument call is (value,). Respect the original input domain.'),
    'agent': ('Choose up to six tool actions to check your hypotheses or the code (see tool_protocol). Each action is one JSON '
              'object. Statement ids are L<line> as in the code listing. Earlier tool results are shown.'),
    'final': ('Write up to six final tests as {arguments, expected}. expected is what the SPEC requires for those arguments, '
              'not what the code returns. Prefer tests where you believe the code violates the spec. Python literal strings; '
              'exception as exception:TypeName; one-argument call is (value,). Earlier tests remain in the record.'),
}


def original_context(task):
    return dict(signature=task['signature'], spec=task['spec'], code=numbered(task), base_tests=task['base'])


# ---- run ---------------------------------------------------------------------------------------------------------
class Run:
    def __init__(self, cohort_name, client=None, model='qwen'):
        self.name = cohort_name
        self.model = model
        self.root = ROOT / cohort_name if model == 'qwen' else ROOT / model / cohort_name
        self.cases = cohort(cohort_name)
        self.client = client
        self.lock = threading.Lock()

    def protocol(self):
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir())
                 if p.is_file() and p.suffix in ('.py', '.json', '.jinja', '.md') and p.name != 'CHANGELOG.md'}
        return immutable(self.root / 'protocol.json', dict(
            cohort=self.name, arms=list(flow_packages.ARMS), sources=files, cases=[c['case_id'] for c in self.cases],
            case_inputs_sha256=digest([{k: c[k] for k in ('case_id', 'source', 'entry', 'base', 'valid_code', 'witnesses')} for c in self.cases]),
            model=CONFIG['codex'] if self.model == 'codex' else R['model'], flowtools=CONFIG['flowtools'], flowrun=R,
            scope='references enter only `score`, after generation_frozen.json'))

    def call(self, slot, stage, messages, seed):
        # Slot includes the prompt digest: identical prompts reuse a cached completion, changed prompts never collide.
        response = self.client.complete(dict(slot=f'{slot}-{digest(messages)[:16]}', stage=stage, seed=seed, messages=messages))
        try:
            value = validate(stage, response['text'])
            error = None
        except ValueError as exc:
            value, error = None, str(exc)
        return value, error, response

    def task(self, case):
        return source_view.prepare(case['source'], case['entry'], case['base'], valid_code=case['valid_code'])

    def shared(self, case, task):
        """Concept (spec only), behavior (code only), hypotheses (both). Frozen once per case for every arm."""
        base = self.root / 'cases' / case['case_id']
        session = flow_tools.FlowSession(task, base / 'common', arm='common')
        seed = R['seed'] + int(hashlib.sha256(case['case_id'].encode()).hexdigest()[:6], 16)
        slot = f"{self.name}/{case['case_id']}/shared"
        concept, cerr, r1 = self.call(slot + '/concept', 'concept', message(INSTR['concept'], dict(signature=task['signature'], spec=task['spec']), 'concept'), seed + 1)
        behavior, berr, r2 = self.call(slot + '/behavior', 'behavior', message(INSTR['behavior'], dict(code=numbered(task), structure=structure(session)), 'behavior'), seed + 2)
        ctx = dict(original_context(task), structure=structure(session), model_concept_claim=concept, model_behavior_claim=behavior)
        hyp, herr, r3 = self.call(slot + '/hypothesis', 'hypothesis', message(INSTR['hypothesis'], ctx, 'hypothesis'), seed + 3)
        line_nodes = collections.defaultdict(list)
        for n, rec in session.cfg['nodes'].items():
            line_nodes[rec['header_lines'][0]].append(n)
        hyps, rejected = [], []
        for i, h in enumerate((hyp or {}).get('hypotheses', [])):
            ids = [n for line in h['source_lines'] for n in line_nodes.get(line, [])]
            row = dict(id=f'H{i + 1}', verdict=h['verdict'], statement=h['reason'], required_relation=h['required_relation'],
                       actual_relation=h['actual_relation'], source_ids=ids, source_lines=h['source_lines'], condition=h['trigger'],
                       alternative=h['alternative'], obligation_ids=['O1'] if concept else [],
                       unmapped_lines=[x for x in h['source_lines'] if x not in line_nodes])
            (hyps if h['verdict'] == 'mismatch' else rejected).append(row)
        concepts = [dict(id='O1', statement=concept['relation'], relation=concept['relation'], domain=concept['domain'],
                         uncertainty=concept['uncertainty'])] if concept else []
        common = session.discover(case['witnesses'])
        placebo = self.placebo(case, task, base)
        record = dict(case_id=case['case_id'], concept=concept, concept_error=cerr, behavior=behavior, behavior_error=berr,
                      hypothesis_raw=hyp, hypothesis_error=herr, hypotheses=hyps, non_mismatch=rejected, concepts=concepts,
                      common=common, placebo=placebo, cfg_supported=session.cfg['supported'],
                      tokens=dict(input=sum(r['input_tokens'] for r in (r1, r2, r3)), output=sum(r['output_tokens'] for r in (r1, r2, r3))),
                      common_report=session.report())
        return record, session

    def placebo(self, case, task, base):
        """Truthful base-covered facts: statements executed by the public base inputs (fixed order, at most 4)."""
        s = flow_tools.FlowSession(task, base / 'placebo', arm='placebo_facts')
        inputs = calls_in(case['base'], {case['entry'], 'candidate', 'f'})[:R['common_witnesses']]
        seen = []
        for view in s.discover(inputs):
            for node in view.get('trace_summary', {}).get('sequence', []):
                if node.startswith('L') and node not in seen:
                    seen.append(node)
        rows = []
        for alias in seen[:4]:
            full = s.back.get(alias)
            rec = s.cfg['nodes'].get(full)
            if rec:
                rows.append(dict(fact=f'Statement {alias} (`{s._header(rec)}`) is executed by the public base tests.'))
        return rows

    def arm(self, case, task, shared, common_session, arm):
        base = self.root / 'cases' / case['case_id'] / 'arms' / arm
        done = base / 'result.json'
        if done.exists():
            return json.loads(done.read_text())
        session = flow_tools.FlowSession(task, base / 'tools', arm=arm)
        session.adopt(common_session.traces)
        seed = R['seed'] + int(hashlib.sha256((case['case_id'] + arm).encode()).hexdigest()[:6], 16)
        slot = f"{self.name}/{case['case_id']}/{arm}"
        record = dict(case_id=case['case_id'], arm=arm, calls=[], rounds=[], final=None, errors=[])
        if arm == 'witness-only':
            record['final_executions'] = [c for c in shared['common'] if c.get('status') == 'ok']
            immutable(done, record)
            return record
        package = flow_packages.build(arm, session, concepts=shared['concepts'], hypotheses=shared['hypotheses'],
                                      witnesses=shared['common'], placebo=shared['placebo'])
        ctx = original_context(task)
        if package['sections']:
            ctx['guidance'] = package['sections']
        history = []
        hyp_ids = list(dict.fromkeys(i for h in shared['hypotheses'] for i in h['source_ids']))[:CONFIG['flowtools']['max_names']]
        observe = hyp_ids if arm in ('concept+hyp', 'input+hyp', 'concept+input+hyp', 'fixed-tools', 'flow+input') else []
        for r in (1, 2):
            session.begin_round()
            stage = 'agent' if arm == 'agent-tools' else 'probe'
            c = dict(ctx, earlier_feedback=history)
            if arm == 'agent-tools':
                c['tool_protocol'] = flow_packages.TOOL_PROTOCOL
            value, error, response = self.call(f'{slot}/round{r}', stage, message(INSTR[stage], c, stage), seed + r)
            record['calls'].append(dict(stage=stage, round=r, error=error, input_tokens=response['input_tokens'], output_tokens=response['output_tokens']))
            feedback = []
            if value is None:
                record['errors'].append(f'round{r}:{error}')
            elif arm == 'agent-tools':
                for action in value['actions']:
                    feedback.append(session.view(session.act(action)))
            else:
                proposals = value['inputs']
                if arm == 'fixed-tools':
                    actions = flow_tools.fixed_schedule(shared['hypotheses'], [p['arguments'] for p in proposals], r)
                else:
                    actions = [dict(tool='replay_input', input=p['arguments'], ids=observe) if observe else
                               dict(tool='replay_input', input=p['arguments']) for p in proposals]
                predictions = {p['arguments']: p for p in proposals}
                for action in actions:
                    result = session.view(session.act(action))
                    if action['tool'] == 'replay_input' and action['input'] in predictions:
                        p = predictions[action['input']]
                        result = dict(result, model_expected=p['expected'], model_predicted_actual=p['predicted_actual'])
                    feedback.append(result)
            history.append(dict(round=r, feedback=feedback))
            record['rounds'].append(dict(round=r, value=value, feedback=feedback))
            text = json.dumps(history, ensure_ascii=False)
            if len(text) > 12000:  # bounded prompt-visible history; full record kept on disk
                history = [dict(round=h['round'], feedback=h['feedback'][:3], omitted=max(0, len(h['feedback']) - 3)) for h in history]
        value, error, response = self.call(f'{slot}/final', 'final', message(INSTR['final'], dict(ctx, earlier_feedback=history), 'final'), seed + 3)
        record['calls'].append(dict(stage='final', error=error, input_tokens=response['input_tokens'], output_tokens=response['output_tokens']))
        record['final'] = value
        if value is None:
            record['errors'].append(f'final:{error}')
            record['final_executions'] = []
        else:
            inputs = [t['arguments'] for t in value['tests']]
            record['final_executions'] = session.final_inputs(inputs[:R['final_tests']])
        record['tool_report'] = session.report()
        record['package_sections'] = sorted(package['sections'])
        immutable(done, record)
        return record

    def generate(self, workers):
        self.protocol()
        if (self.root / 'generation_frozen.json').exists():
            print('generation already frozen')
            return
        prepared = {}

        failures = []

        def prep(case):
            try:
                prep_one(case)
            except Exception as exc:
                failures.append([case['case_id'], 'shared', type(exc).__name__, str(exc)[:200]])
                print('FAILED shared', case['case_id'], type(exc).__name__, str(exc)[:200], flush=True)

        def prep_one(case):
            task = self.task(case)
            path = self.root / 'cases' / case['case_id'] / 'shared.json'
            if path.exists():
                record = json.loads(path.read_text())
                session = flow_tools.FlowSession(task, self.root / 'cases' / case['case_id'] / 'common', arm='common')
                session.discover(case['witnesses'])
            else:
                record, session = self.shared(case, task)
                immutable(path, record)
            prepared[case['case_id']] = (case, task, record, session)
            print('shared', case['case_id'], 'hyps', len(record['hypotheses']), 'errors', record['concept_error'], record['behavior_error'], record['hypothesis_error'], flush=True)

        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(prep, self.cases))
        jobs = [(cid, arm) for cid in prepared for arm in flow_packages.ARMS]
        with ThreadPoolExecutor(workers) as pool:
            futures = {pool.submit(self.arm, prepared[cid][0], prepared[cid][1], prepared[cid][2], prepared[cid][3], arm): (cid, arm) for cid, arm in jobs}
            for f in as_completed(futures):
                cid, arm = futures[f]
                try:
                    rec = f.result()
                    print('arm', cid, arm, 'errors', rec['errors'], 'final', len(rec.get('final_executions') or []), flush=True)
                except Exception as exc:
                    failures.append([cid, arm, type(exc).__name__, str(exc)[:200]])
                    print('FAILED', cid, arm, type(exc).__name__, str(exc)[:200], flush=True)
        if failures:
            immutable(self.root / f'failures_{digest(failures)[:8]}.json', failures)
            raise SystemExit(f'{len(failures)} arm jobs failed; rerun to resume; not frozen')
        files = sorted(p for p in (self.root / 'cases').rglob('*.json') if '/executions/' not in str(p))
        immutable(self.root / 'generation_frozen.json', {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        print('generation frozen')


# ---- scoring (after freeze) -------------------------------------------------------------------------------------
def same(a, b):
    """Typed equality; floats compared with math.isclose(rel_tol=1e-6, abs_tol=1e-9)."""
    if a[0] != b[0]:
        return False
    if a[0] == 'exception':
        return a[1] == b[1]
    return _same_typed(a[1], b[1])


def _same_typed(x, y):
    if type(x) is tuple and type(y) is tuple and len(x) == 2 and type(x[0]) is str and type(y[0]) is str:
        if x[0] != y[0]:
            return False
        if x[0] == 'float':
            return math.isclose(x[1], y[1], rel_tol=1e-6, abs_tol=1e-9)
        if type(x[1]) is tuple and type(y[1]) is tuple:
            return len(x[1]) == len(y[1]) and all(_same_typed(a, b) for a, b in zip(x[1], y[1]))
        return x[1] == y[1]
    if type(x) is tuple and type(y) is tuple:
        return len(x) == len(y) and all(_same_typed(a, b) for a, b in zip(x, y))
    return x == y


def parse_expected(text):
    if text.startswith('exception:'):
        kind = text.split(':', 1)[1].strip()
        return ('exception', kind) if kind.isidentifier() else None
    try:
        return ('ok', typed_value(parse_literal(text, output=True)))
    except (ValueError, TypeError):
        return None


def put_observation(execution):
    if execution.get('status') != 'ok' or not execution.get('native_checked'):
        return None
    if execution['execution_status'] == 'exception':
        return ('exception', execution['exception_type'])
    if execution['execution_status'] == 'ok' and execution.get('output') is not None:
        try:
            return ('ok', typed_value(parse_literal(execution['output'], output=True)))
        except (ValueError, TypeError):
            return None
    return None


class Reference:
    def __init__(self, run):
        self.run = run
        self.root = run.root / 'reference'

    def contract_valid(self, case, literal):
        """Evaluator-only input validity (VibePass checker contract); True when no contract exists."""
        ref = case['reference']
        if not ref.get('contract'):
            return True
        return self._run(ref['contract'], ref['entry'], literal).get('status') == 'ok'

    def _run(self, source, entry, literal):
        key = digest(dict(source=source, entry=entry, input=literal))
        d = self.root / key
        jp, op = d / 'job.json', d / 'result.json'
        if not op.exists():
            immutable(jp, dict(source=source, entry=entry, input_repr=literal, mode='ordinary', valid_code=None,
                               limits=dict(flow_tools.worker_limits(), worker_timeout=8)))
            try:
                sandbox(CONFIG['V4_PYTHON'], HERE / 'flow_worker.py', jp, op, 20)
            except RuntimeError:
                immutable(op, dict(status='unresolved', reason='isolated_worker_failed'))
        return json.loads(op.read_text())

    def __call__(self, case, literal):
        ref = case['reference']
        if ref['kind'] == 'fixture':
            return fixture_oracles.expected(ref['case'], literal)
        if ref.get('contract'):
            r = self._run(ref['source'], ref['entry'], literal)
            if r.get('status') == 'exception':
                return ('exception', r['exception_type'])
            if r.get('status') == 'ok' and r.get('output_repr') is not None:
                return ('ok', typed_value(parse_literal(r['output_repr'], output=True)))
            return None
        key = digest(dict(source=ref['source'], entry=ref['entry'], input=literal))
        d = self.root / key
        jp, op = d / 'job.json', d / 'result.json'
        if not op.exists():
            immutable(jp, dict(source=ref['source'], entry=ref['entry'], input_repr=literal, mode='ordinary', valid_code=None,
                               limits=flow_tools.worker_limits()))
            try:
                sandbox(CONFIG['V4_PYTHON'], HERE / 'flow_worker.py', jp, op, CONFIG['flowtools']['outer_timeout'])
            except RuntimeError:
                immutable(op, dict(status='unresolved', reason='isolated_worker_failed'))
        r = json.loads(op.read_text())
        if r.get('status') == 'exception':
            return ('exception', r['exception_type'])
        if r.get('status') == 'ok' and r.get('output_repr') is not None:
            return ('ok', typed_value(parse_literal(r['output_repr'], output=True)))
        return None


def score(run):
    if not (run.root / 'generation_frozen.json').exists():
        raise SystemExit('generation not frozen')
    frozen = json.loads((run.root / 'generation_frozen.json').read_text())
    for rel, h in frozen.items():
        if hashlib.sha256((run.root / rel).read_bytes()).hexdigest() != h:
            raise SystemExit('frozen artifact changed: ' + rel)
    ref = Reference(run)
    rows, per_case = [], {}
    for case in run.cases:
        shared = json.loads((run.root / 'cases' / case['case_id'] / 'shared.json').read_text())
        witness_disc = False
        arity = source_view.prepare(case['source'], case['entry'])['arity']
        for arm in flow_packages.ARMS:
            rec = json.loads((run.root / 'cases' / case['case_id'] / 'arms' / arm / 'result.json').read_text())
            expected = {}
            if rec.get('final'):
                for t in rec['final']['tests']:
                    try:
                        lit = literal_for_transport(flow_tools.parse_call(t['arguments'], arity))
                    except (ValueError, TypeError):
                        continue
                    expected.setdefault(lit, t['expected'])
            stats = collections.Counter()
            for ex in rec.get('final_executions') or []:
                if ex.get('status') != 'ok':
                    stats['invalid_inputs'] += 1
                    continue
                stats['executed'] += 1
                if ex.get('domain_filter') != 'accepted':
                    stats['inadmissible'] += 1
                    continue
                if not ref.contract_valid(case, ex['input']):
                    # Contract-invalid input never detects; a claimed bug on it is a false alarm (held-out convention).
                    stats['contract_invalid'] += 1
                    exp = parse_expected(expected.get(ex['input'], '')) if arm != 'witness-only' else None
                    put = put_observation(ex)
                    if exp is not None and put is not None and not same(exp, put):
                        stats['false_alarm'] += 1
                    continue
                stats['admissible'] += 1
                put = put_observation(ex)
                truth = ref(case, ex['input'])
                if put is None or truth is None:
                    stats['unscored'] += 1
                    continue
                disc = not same(put, truth)
                stats['input_discrepancy'] += disc
                if arm == 'witness-only':
                    continue
                exp = parse_expected(expected.get(ex['input'], ''))
                if exp is None:
                    stats['unparseable_expected'] += 1
                    continue
                if disc and same(exp, truth):
                    stats['confirmed_detection'] += 1
                elif disc:
                    stats['discrepancy_wrong_expected'] += 1
                elif not same(exp, put):
                    stats['false_alarm'] += 1
                else:
                    stats['passing_test'] += 1
            if arm == 'witness-only':
                witness_disc = stats['input_discrepancy'] > 0
            calls = rec.get('calls', [])
            rows.append(dict(case_id=case['case_id'], arm=arm, **stats, calls=len(calls), schema_errors=sum(1 for c in calls if c['error']),
                             input_tokens=sum(c['input_tokens'] for c in calls), output_tokens=sum(c['output_tokens'] for c in calls),
                             tool_actions=(rec.get('tool_report') or {}).get('actions', 0), tool_errors=(rec.get('tool_report') or {}).get('errors', 0),
                             hypotheses=len(shared['hypotheses'])))
        per_case[case['case_id']] = witness_disc
    summary = {}
    for arm in flow_packages.ARMS:
        rs = [r for r in rows if r['arm'] == arm]
        summary[arm] = dict(
            cases=len(rs), tasks_confirmed=sum(1 for r in rs if r.get('confirmed_detection')),
            tasks_confirmed_beyond_witness=sum(1 for r in rs if r.get('confirmed_detection') and not per_case[r['case_id']]),
            tasks_input_discrepancy=sum(1 for r in rs if r.get('input_discrepancy')),
            confirmed_tests=sum(r.get('confirmed_detection', 0) for r in rs), false_alarms=sum(r.get('false_alarm', 0) for r in rs),
            tasks_with_false_alarm=sum(1 for r in rs if r.get('false_alarm')), admissible=sum(r.get('admissible', 0) for r in rs),
            inadmissible=sum(r.get('inadmissible', 0) for r in rs), invalid_inputs=sum(r.get('invalid_inputs', 0) for r in rs),
            discrepancy_wrong_expected=sum(r.get('discrepancy_wrong_expected', 0) for r in rs),
            schema_errors=sum(r['schema_errors'] for r in rs), calls=sum(r['calls'] for r in rs),
            input_tokens=sum(r['input_tokens'] for r in rs), output_tokens=sum(r['output_tokens'] for r in rs),
            tool_actions=sum(r['tool_actions'] for r in rs), tool_errors=sum(r['tool_errors'] for r in rs))
    detected = {a: {r['case_id'] for r in rows if r['arm'] == a and r.get('confirmed_detection')} for a in flow_packages.ARMS}
    paired = {}
    for a in LLM_ARMS:
        for b in ('toolinput', 'plain', 'placebo+input', 'flow+input', 'input+hyp', 'fixed-tools'):
            if a != b:
                paired[f'{a} vs {b}'] = dict(wins=len(detected[a] - detected[b]), losses=len(detected[b] - detected[a]))
    shared_stats = collections.Counter()
    for case in run.cases:
        s = json.loads((run.root / 'cases' / case['case_id'] / 'shared.json').read_text())
        shared_stats['concept_valid'] += s['concept'] is not None
        shared_stats['behavior_valid'] += s['behavior'] is not None
        shared_stats['hypothesis_valid'] += s['hypothesis_raw'] is not None
        shared_stats['cases_with_mismatch_hypothesis'] += bool(s['hypotheses'])
        shared_stats['mismatch_hypotheses'] += len(s['hypotheses'])
        shared_stats['cfg_supported'] += s['cfg_supported']
    report = dict(cohort=run.name, scope='frozen generation scored with independent references; small n, descriptive only',
                  shared=dict(shared_stats), arms=summary, paired_task_detection=paired, rows=rows)
    immutable(run.root / 'score.json', report)
    print(json.dumps(dict(shared=report['shared'], arms=summary), indent=1))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=('generate', 'score'))
    ap.add_argument('--cohort', choices=('diag16', 'pilot20', 'vibepass'), required=True)
    ap.add_argument('--model', choices=('qwen', 'codex'), default='qwen')
    ap.add_argument('--workers', type=int)
    args = ap.parse_args()
    run = Run(args.cohort, model=args.model)
    if args.command == 'generate':
        if args.model == 'codex':
            from .codex_client import CodexClient
            run.client = CodexClient(run.root / 'transport')
        else:
            from .flow_client import Client
            run.client = Client(run.root / 'transport')
        try:
            run.generate(args.workers or (CONFIG['codex']['workers'] if args.model == 'codex' else R['workers']))
        finally:
            run.client.close()
    else:
        score(run)


if __name__ == '__main__':
    main()
