"""Seen8 supplied-concept diagnostic. Semantics scored only after generation freeze."""
import argparse
import ast
import copy
import fcntl
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import subprocess
import sys

from jsonschema import Draft202012Validator

from . import pilot_fixtures, source_view, flow_tools, tool_contract
from .chain_inputs import literal_for_transport, typed_value, parse_literal
from .d1_client import Client, TransportStop
from .flow_common import immutable, strict_json, write_json, digest
from .paths import DATA_OUT, CONFIG

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = DATA_OUT / 'd1'
ARMS = ('concept_adaptive', 'generic_adaptive', 'concept_committed')
QUOTA = REPO / 'trickcatcher_linefacts/analysis/astra_concept_design_20261020/quota_guard.py'


class Session(flow_tools.FlowSession):
    query_replay_ordinal = 0

    def _dispatch(self, action, number):
        if type(action) is not dict:
            return {'status': 'refused', 'error': 'D1_action_shape', 'charges': {}}
        if action.get('tool') not in ('inspect_flow', 'inspect_data', 'replay_input') or self.query_replay_ordinal > 2:
            return {'status': 'refused', 'error': 'D1_tool_or_round_replay_cap', 'charges': {}}
        return super()._dispatch(action, number)


def read(path):
    return strict_json(Path(path).read_text(), max_bytes=16 * 1024 * 1024)


def sources():
    return {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.rglob('*')) if p.is_file() and p.suffix != '.pyc'
            and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}


def dependencies():
    binary = Path(CONFIG['V4_PYTHON']).resolve()
    return {'python': sys.version, 'worker_binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'libraries': {k: importlib.metadata.version(k) for k in ('networkx', 'jsonschema', 'httpx', 'jinja2')}}


def base_input(case):
    tree = ast.parse(case['base'])
    call = next(x for x in ast.walk(tree) if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == case['entry'])
    return literal_for_transport(tuple(ast.literal_eval(x) for x in call.args))


def task(case):
    return source_view.prepare(case['source'], case['entry'], case['base'], valid_code=case['valid_code'])


def measured_gap(ep, literal):
    """Finite base-input measurements; no oracle/PUT output drives this summary."""
    args = ast.literal_eval(literal)
    xs = args[0]
    from collections import Counter
    m = {'observed_rows': 1, 'input_length': len(xs)}
    uid = ep['source_fixture']
    if uid in ('f02', 'f14'):
        m['maximum_multiplicity'] = max(Counter(xs).values(), default=0)
        assert m['maximum_multiplicity'] < 2
    elif uid == 'f04':
        m['equality_occurrences'] = sum(x == args[1] for x in xs)
        assert m['equality_occurrences'] == 0
    elif uid == 'f06':
        m['container_only_distinct_values'] = len(set(xs) - set(args[1]))
        assert m['container_only_distinct_values'] == 0
    elif uid == 'f08':
        m['positive_occurrences'] = sum(x > 0 for x in xs)
        assert m['positive_occurrences'] > 0
    elif uid == 'f12':
        m.update(aggregate=sum(xs), limit=args[1])
        assert len(xs) < 3
    elif uid == 'f16':
        m.update(one_occurrences=xs.count(1), maximum_multiplicity=max(Counter(xs).values(), default=0))
        assert m['one_occurrences'] == 0 and m['maximum_multiplicity'] < 2
    elif uid == 'f13':
        m = {'binding': 'unknown', 'eligibility_measurement': None}
    return dict(copy.deepcopy(ep['abstract_gap']), measurements=m)


def compact(result):
    # Same projection in every arm. No gold, model expected value or relation verdict.
    allowed = ('status', 'tool', 'hypothesis', 'error', 'error_details', 'input', 'domain_filter',
               'execution_status', 'exception_type', 'output', 'output_capture', 'native_checked',
               'output_provenance', 'reach', 'trace_complete', 'all_invocations_proven',
               'snapshots', 'omitted_snapshots', 'nodes', 'edges', 'definitions', 'uses',
               'statements', 'names', 'reaching_definitions', 'observed_def_use',
               'omitted_nodes', 'control_dependence_scope', 'validity_provenance', 'trace',
               'supported', 'unsupported', 'scope', 'trace_summary', 'observation_id')
    return {k: copy.deepcopy(v) for k, v in result.items() if k in allowed}


def prepare(root=ROOT):
    manifest = read(HERE / 'd1_packets.json')
    catalog = {x['id']: x for x in read(HERE / 'catalog.json')['concepts']}
    fixtures = {x['fixture_id']: x for x in pilot_fixtures.cases()}
    prepared = []
    for ep in manifest['episodes']:
        case = fixtures[ep['source_fixture']]
        t = task(case)
        session = flow_tools.FlowSession(t, root / 'shared' / ep['id'], arm='shared')
        literals = [base_input(case), ep['round1_native_input']]
        observations = session.discover(literals)
        assert len(observations) == 2
        assert all(x.get('native_checked') is True for x in observations), 'unusable_shared_native'
        public_rows = []
        for i, row in enumerate(observations):
            visible = compact(row); visible['observation_id'] = 'B0' if i == 0 else 'J0'
            public_rows.append(visible)
        entry = catalog[ep['concept_binding']['catalog_id']]
        concept = {k: entry[k] for k in manifest['shared_policy']['public_catalog_projection']}
        public = {'signature': t['signature'], 'spec': t['spec'], 'code': t['source_masked'],
                  'base_tests': t['base'], 'initial_hypothesis': ep['initial_hypothesis'],
                  'initial_observations': public_rows[:1],
                  'source_ids': [{'id': session.forward[n['id']], 'line': n['header_lines'][0]}
                                 for n in session.cfg['nodes'].values() if n['id'] in session.forward],
                  'notice': manifest['shared_policy']['untrusted_notice_all_arms']}
        row = {'episode': ep['id'], 'fixture': ep['source_fixture'], 'task': t, 'public': public,
               'concept': concept, 'binding': ep['concept_binding'], 'gap': measured_gap(ep, literals[0]),
               'injection': public_rows[1], 'shared_inputs': literals}
        immutable(root / 'prepared' / (ep['id'] + '.json'), row)
        prepared.append(row)
    order = [x['episode'] for x in prepared]
    random.Random(20261021).shuffle(order)
    return immutable(root / 'preparation.json', {'sources': sources(), 'dependencies': dependencies(),
                     'quota_guard_sha256': hashlib.sha256(QUOTA.read_bytes()).hexdigest(),
                     'episode_order': order, 'episodes': [x['episode'] for x in prepared],
                     'prepared_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / 'prepared').glob('*.json'))},
                     'scope': 'seen authored fixtures, supplied concepts; no extraction/generalization claim'})


def verify(root=ROOT):
    frozen = read(root / 'preparation.json')
    assert frozen['sources'] == sources(), 'source_drift'
    assert frozen['dependencies'] == dependencies(), 'dependency_drift'
    assert frozen['quota_guard_sha256'] == hashlib.sha256(QUOTA.read_bytes()).hexdigest(), 'quota_guard_drift'
    assert frozen['prepared_hashes'] == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / 'prepared').glob('*.json'))}, 'prepared_drift'
    if (root / 'generation_frozen.json').exists():
        for name, sha in read(root / 'generation_frozen.json').items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, 'generation_drift'


def decode(text, finish):
    if finish != 'stop':
        raise ValueError('incomplete_response')
    value = text.strip()
    if value.startswith('```json\n') and value.endswith('\n```') and value.count('```') == 2:
        value = value[8:-4]
    result = strict_json(value)
    errors = list(Draft202012Validator(read(HERE / 'reply.schema.json')).iter_errors(result))
    if errors:
        raise ValueError('reply_schema')
    ids = [x['id'] for x in result['claims']]
    if len(ids) != len(set(ids)) or any(not x for x in ids):
        raise ValueError('claim_ids')
    return result


def messages(row, arm, turn, history):
    context = copy.deepcopy(row['public'])
    if arm != 'generic_adaptive':
        context.update(concept=row['concept'], concept_binding=row['binding'], abstract_gap=row['gap'])
    protocol = strict_json(tool_contract.protocol().split('Contract: ', 1)[1])
    protocol['schemas'] = {k: v for k, v in protocol.pop('tools').items()
                           if k in ('inspect_flow', 'inspect_data', 'replay_input')}
    protocol.update(round_replays=2, total_replays=4,
                    scope='Structural inspection and native observations only; errors consume action slots.')
    context.update(tool_protocol=protocol, earlier_turns=history, turn=turn,
                   injected_observation=row['injection'] if turn > 1 else None)
    instruction = ('The initial hypothesis is fallible. Keep/revise/withdraw/unknown claims from spec and observations. '
                   'Before each query commit its predicted observation and what would change your claim. '
                   'Use only inspect_flow, inspect_data, replay_input, at most3 actions/round and at most2 replay actions. '
                   'Actions use the published literal full positional tuple format. Observed output is not a trusted expected oracle. '
                   'Evidence IDs: original_spec, source_return, B0, J0 and the observation_id in feedback. '
                   'Final inputs may be proposed even when claims remain unknown. No arbitrary code or external tools. ')
    if turn == 3:
        instruction += 'Final turn: claims and up to2 final_inputs, no queries or later_queries. No expected-output field. '
    elif arm == 'concept_committed' and turn == 1:
        instruction += 'Commit queries for round1 AND later_queries for round2 now, each max3/max2replays. Later queries cannot be changed after feedback. '
    elif arm == 'concept_committed':
        instruction += 'Your committed later_queries will execute now; update claims only. Do not submit replacement queries. '
    else:
        instruction += 'Submit current queries only, no later_queries or final_inputs before final turn. '
    return [{'role': 'system', 'content': 'Return exactly one JSON object. No prose outside JSON. No tools outside the declared bridge.'},
            {'role': 'user', 'content': json.dumps({'instruction': instruction, 'context': context,
                                                  'reply_schema': read(HERE / 'reply.schema.json')}, ensure_ascii=False)}]


def quota_check(root):
    result = subprocess.run([sys.executable, str(QUOTA), 'check'], capture_output=True, text=True, timeout=30, check=True)
    snapshot = strict_json(result.stdout)
    write_json(root / 'quota_latest.json', snapshot)
    if snapshot['should_stop']:
        raise TransportStop('quota_at_or_below15')


def run(client, root=ROOT, check_quota=True):
    verify(root)
    if (root / 'generation_frozen.json').exists():
        return
    order = read(root / 'preparation.json')['episode_order']
    for i, episode in enumerate(order):
        row = read(root / 'prepared' / (episode + '.json'))
        arms = ARMS[i % 3:] + ARMS[:i % 3]
        for arm in arms:
            executor = flow_tools.Executor(row['task'], root / 'native')
            session = Session(row['task'], root / 'arms' / episode / arm / 'tools', arm=arm, executor=executor)
            history, committed = [], []
            for turn in (1, 2, 3):
                slot = episode + '__' + arm + '__' + str(turn)
                request = messages(row, arm, turn, history)
                immutable(root / 'requests' / (slot + '.json'), request)
                verify(root)
                if check_quota:
                    quota_check(root)
                response = client.complete(slot, request)
                artifact = {'raw': response}
                try:
                    value = decode(response['text'], response['finish_reason'])
                    if turn == 3 and (value.get('queries') or value.get('later_queries')):
                        raise ValueError('queries_in_final')
                    if turn < 3 and value.get('final_inputs'):
                        raise ValueError('premature_final_inputs')
                    if arm != 'concept_committed' and value.get('later_queries'):
                        raise ValueError('unexpected_commitment')
                    if arm == 'concept_committed' and turn == 2 and (value.get('queries') or value.get('later_queries')):
                        raise ValueError('replacement_commitment')
                    artifact.update(state='valid', parsed=value)
                except ValueError as exc:
                    value = {}; artifact.update(state='failed', error=str(exc))
                immutable(root / 'artifacts' / (slot + '.json'), artifact)  # Durable prediction BEFORE execution.
                feedback = []
                if turn < 3:
                    session.begin_round()
                    if turn == 1:
                        committed = copy.deepcopy(value.get('later_queries', []))
                    queries = committed if turn == 2 and arm == 'concept_committed' else value.get('queries', [])
                    replays = 0
                    for number, query in enumerate(queries[:3]):
                        action = query['action']
                        if action.get('tool') == 'replay_input':
                            replays += 1
                        session.query_replay_ordinal = replays
                        result = compact(session.view(session.act(action)))
                        result['observation_id'] = 'T' + str(turn) + '_' + str(number + 1)
                        feedback.append(result)
                else:
                    feedback = [compact(x) for x in session.final_inputs(value.get('final_inputs', []))]
                event = {'turn': turn, 'reply': value, 'reply_state': artifact['state'],
                         'reply_error': artifact.get('error'), 'feedback': feedback}
                immutable(root / 'events' / (slot + '.json'), event)
                history.append(event)
                print(episode, arm, turn, artifact['state'], flush=True)
    frozen = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for name in ('prepared', 'requests', 'artifacts', 'events', 'arms', 'native', 'transport')
              for p in sorted((root / name).rglob('*')) if p.is_file()}
    immutable(root / 'generation_frozen.json', frozen)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=('prepare', 'run', 'verify'))
    parser.add_argument('--online', action='store_true'); args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == 'prepare':
            prepare(); print('prepared seen8, no model calls')
        elif args.command == 'verify':
            verify(); print('verified')
        else:
            if not args.online:
                raise SystemExit('explicit_online_required')
            verify(); quota_check(ROOT)
            if (ROOT / 'generation_frozen.json').exists():
                return
            approval = read(ROOT / 'approval.json')
            if not (approval.get('passed') and approval.get('sources') == sources()
                    and approval.get('preparation_hash') == digest(read(ROOT / 'preparation.json'))):
                raise RuntimeError('audit_approval_required')
            state = {'state': 'running', 'model': CONFIG['model']}
            write_json(ROOT / 'status.json', state)
            client = None
            try:
                client = Client(ROOT / 'transport'); run(client)
                state['state'] = 'complete'
            except Exception as exc:
                state.update(state='stopped', error_type=type(exc).__name__, reason=str(exc) if isinstance(exc, TransportStop) else 'controller_failure')
            finally:
                if client: client.close()
                write_json(ROOT / 'status.json', state)
                print(json.dumps(state), flush=True)


if __name__ == '__main__':
    main()
