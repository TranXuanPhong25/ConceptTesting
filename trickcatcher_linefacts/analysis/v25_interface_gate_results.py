"""Read-only terminal audit: no client construction, worker execution, repair or retries."""
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v25_interface_gate import gate, fixtures
from trickcatcher_linefacts.pipelines.v25_interface_gate.common import digest, task_for
from trickcatcher_linefacts.pipelines.v25_interface_gate.binding import bind, observation
from trickcatcher_linefacts.pipelines.v25_interface_gate.execution import KEYS
from trickcatcher_linefacts.pipelines.v25_interface_gate.interfaces import raw_record


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cached_pool(root, packet, native_index):
    """Read existing ordinary/traced results only; never invoke replay/execute/run_once."""
    task = task_for(packet['case']); pool = []
    for arguments in packet['pool']['all_inputs']:
        normalized, literal = bind(task, arguments)
        folder = native_index[(task['source_original'], task['entry'], literal, digest(task['valid_code']))]
        ordinary, traced = read(folder / 'ordinary/result.json'), read(folder / 'traced/result.json')
        oj, tj = read(folder / 'ordinary/job.json'), read(folder / 'traced/job.json')
        assert oj == dict(tj, mode='ordinary')
        checked = (ordinary.get('status') in ('ok', 'exception') and traced.get('trace_complete') is True
                   and all(ordinary.get(k) == traced.get(k) for k in KEYS)
                   and ordinary.get('input_before') is not None and ordinary.get('input_after') is not None)
        if ordinary.get('status') == 'ok':
            checked = checked and ordinary.get('output_capture') == 'literal' and ordinary.get('output_signature') is not None
        assert checked
        events = traced.get('events', []); cap = gate.D['trace_prompt_events']
        execution = {'input': literal, 'status': ordinary.get('status'), 'output_repr': ordinary.get('output_repr'),
                     'exception_type': ordinary.get('exception_type'), 'native_checked': checked,
                     'verification_reason': 'native_and_traced_signatures_agree',
                     'events': events[:cap], 'omitted_events': max(0, len(events) - cap),
                     'trace_scope': 'line events; no local-effect or data-propagation proof',
                     'validity_scope': 'authored fixture type/domain filter',
                     'worker_status': {'ordinary': ordinary.get('status'), 'traced': traced.get('status')}}
        pool.append({'arguments': normalized, 'execution': execution, 'input_id': digest(normalized)})
    return pool


def worker_costs(root, group):
    attempts = [read(p) for p in (root / group).rglob('attempt.json')]
    results = [read(p) for p in (root / group).rglob('result.json')]
    return {'attempts': len(attempts), 'recorded_launches': sum(x.get('launched') is True for x in attempts),
            'unresolved_launches': sum(x.get('launched') is None for x in attempts),
            'PUT_calls': sum(x.get('put_calls', 0) for x in results),
            'predicate_evaluations': sum(x.get('evaluations_attempted', 0) for x in results)}


def main():
    root = gate.ROOT
    # Hash verification only. Unlike run/report/freeze, no writer or online entrypoint is invoked.
    protocol, prepared, snapshot = read(root / 'protocol.json'), read(root / 'prepared.json'), read(root / 'run_frozen.json')
    assert gate.source_files() == protocol['sources']
    assert gate.dependencies() == protocol['dependencies']
    assert digest(prepared) == protocol['prepared_hash']
    assert prepared == gate.packets()
    preflight = read(root / 'preflight.json')
    assert preflight['passed'] and preflight['sources'] == protocol['sources']
    assert preflight['dependencies'] == protocol['dependencies'] and preflight['prepared_hash'] == digest(prepared)
    assert all(sha(root / name) == expected for name, expected in snapshot.items())
    parent = read(gate.HERE / 'PARENT.json'); ports = read(gate.HERE / 'PORTS.json')
    assert all(sha(gate.HERE.parent / 'v7' / name) == expected for name, expected in parent['files'].items())
    assert all(sha(gate.HERE.parent / 'v24_obligations' / name) == expected for name, expected in ports['files'].items())
    status, report, capability = read(root / 'status.json'), read(root / 'report.json'), read(root / 'capability.json')
    assert status['state'] == 'gate_failed_A' and status['exit_code'] == 0
    assert status['gates'] == report['gates'] == {'A': False, 'B': None, 'C': None}
    assert gate.costs(root) == report['costs'] == status['costs']
    for name in ('capability_request.json', 'capability_response.json'):
        assert digest(read(root / name)) == capability[name]
    echo = read(root / 'capability_response.json')
    echo_transport = root / 'transport/calls/capability__echo'
    assert echo == read(echo_transport / 'response.json')
    assert echo['origin'] == 'qwen_endpoint' and echo['finish_reason'] == 'stop'
    assert echo['text'] == '{"schema_gate":true}' and echo['input_tokens'] == 42 and echo['output_tokens'] == 10
    assert capability['mode'] == 'guided_json' and capability['echo_passed']
    echo_wire = read(echo_transport / 'wire_request.json')
    assert echo_wire['payload']['guided_json'] == gate.ECHO_SCHEMA
    assert echo_wire['input_tokens'] == echo['input_tokens']
    assert read(echo_transport / 'attempts.json') == [{'state': 'received', 'input_tokens': 42, 'output_tokens': 10}]
    assert not list((root / 'transport').rglob('*quarantine.json'))

    native_index = {}
    for p in (root / 'native_executions').glob('*/ordinary/job.json'):
        job = read(p); key = (job['source'], job['entry'], job['input_repr'], digest(job['valid_code']))
        assert key not in native_index
        native_index[key] = p.parent.parent
    rows, artifacts, token_states = [], [], Counter()
    for packet in prepared:
        case = packet['case']; uid = case['fixture_id']; task = task_for(case)
        req = read(root / 'requests' / (uid + '__meta.json'))
        artifact = read(root / 'artifacts' / (uid + '__meta.json'))
        transport = root / 'transport/calls' / req['slot']
        assert req == read(transport / 'request.json') and artifact['request_hash'] == digest(req)
        assert req['stage'] == 'meta' and 'guided_schema' in req
        assert set(json.loads(req['messages'][1]['content'])['context']) == {'signature', 'spec'}
        assert artifact['state'] == 'failed' and 'response' not in artifact and 'parsed' not in artifact
        assert not (transport / 'response.json').exists()
        attempts = read(transport / 'attempts.json') if (transport / 'attempts.json').exists() else []
        assert len(attempts) <= 3 and all(x['state'] == 'transport_error_usage_unknown' for x in attempts)
        if uid in ('f02', 'f04'):
            assert len(attempts) == 3 and all(x['error'] == 'ReadTimeout' for x in attempts)
        elif uid == 'f06':
            assert [x['http_status'] for x in attempts] == [503, 404]
        else:
            assert not attempts and artifact['reason'] == 'tokenizer_attempt_budget_exhausted'
        # Bind tokenizer records to the same deterministic Jinja template, without Client construction.
        from jinja2.sandbox import SandboxedEnvironment
        rendered = SandboxedEnvironment().from_string((gate.HERE / 'chat_template.jinja').read_text()).render(
            messages=req['messages'], add_generation_prompt=True, tools=None)
        token_ledger = root / 'transport/tokens' / (digest(rendered) + '.attempts.json')
        tokenizer = read(token_ledger); token_states.update(x['state'] for x in tokenizer)
        wire = read(transport / 'wire_request.json') if (transport / 'wire_request.json').exists() else None
        if wire:
            assert wire['payload']['messages'] == req['messages'] and wire['payload']['guided_json'] == req['guided_schema']
            assert read(token_ledger.with_name(digest(rendered) + '.json'))['count'] == wire['input_tokens']
        prep = read(root / 'prepared_cases' / (uid + '.json'))
        assert prep['records'] == {'meta': artifact, 'predicate': None}
        assert prep['qualification'] == {'state': 'unqualified', 'reason': 'invalid_contract_artifact'}
        contexts = read(root / 'contexts' / (uid + '__phaseA.json'))
        pool = cached_pool(root, packet, native_index)
        assert all(contexts[arm]['common_inputs_and_native_traces'] == pool[:6] for arm in ('verified_hyp', 'text_hyp', 'toolinput'))
        assert contexts['text_hyp']['raw_guidance']['meta'] == raw_record(artifact)
        for stage in ('predicate', 'hypothesis', 'trigger'):
            assert contexts['text_hyp']['raw_guidance'][stage] == raw_record(None)
        assert contexts['verified_hyp']['contract'] is None and contexts['verified_hyp']['hypothesis'] is None
        for arm in contexts:
            assert contexts[arm]['spec'] == task['spec'] and contexts[arm]['code'] == task['source_masked']
        bugs = []
        for row in pool:
            obs = observation(row['execution']); gold = fixtures.expected(case, row['arguments'])
            assert obs is not None
            if gold is not None and not fixtures.same_observation(obs, gold):
                bugs.append({'arguments': row['arguments'], 'actual': obs, 'required_fixture_oracle': gold})
        row = {'case': uid, 'kind': 'ambiguous' if uid == 'f13' else 'correct_masked' if uid == 'f14' else 'buggy',
               'metadata_failure': artifact['reason'], 'completion_attempts': attempts, 'tokenizer_attempts': tokenizer,
               'serialized_prompt_tokens': wire['input_tokens'] if wire else None,
               'predicate': 'blocked_metadata_failure', 'calibration': 'not_reached',
               'behavior_hypothesis_trigger': 'blocked_gate_A', 'generation': 'blocked_gate_A',
               'model_ambiguity_abstention': 'unobserved' if uid == 'f13' else 'not_applicable',
               'code_envelope': 'not_observed', 'raw_task_text': None,
               'pool_inputs': len(pool), 'native_rows_shared_per_context': 6,
               'witness_only_bug_inputs': len(bugs) if uid != 'f13' else None,
               'witness_only_examples': bugs[:2], 'generated_input_yield': None, 'novel_input_yield': None,
               'false_contract_flags': None}
        rows.append(row)
        artifacts.append({'slot': req['slot'], 'request_hash': digest(req), 'artifact': artifact,
                          'origin': None, 'response_hash': None, 'raw_text': None})
    assert len(list((root / 'requests').glob('*.json'))) == len(rows) == 5
    assert len(native_index) == sum(x['pool_inputs'] for x in rows) == 124
    assert not list((root / 'hypothesis_cases').glob('*.json')) and not list((root / 'generation').glob('*.json'))
    assert sum(x['witness_only_bug_inputs'] or 0 for x in rows) == 36
    assert token_states == {'received': 3, 'transport_error': 6}
    metadata = [json.loads(line) for line in (root / 'transport/metadata_calls.jsonl').read_text().splitlines()]
    prelaunch = [json.loads(line) for line in (root / 'prelaunch_metadata.jsonl').read_text().splitlines()]
    assert len(metadata) == 13 and len(prelaunch) == 11
    metadata_states = Counter((x['path'], x['state']) for x in metadata)
    # Bind mutable transport/status/report ledgers at ANALYSIS time, not falsely at original run freeze.
    evidence_names = ['status.json', 'report.json', 'capability.json'] + [str(p.relative_to(root)) for p in sorted((root / 'transport').rglob('*.json'))]
    evidence_names += ['transport/metadata_calls.jsonl', 'prelaunch_metadata.jsonl']
    result = {'scope': 'terminal transport failure; semantic feasibility and concept efficacy unmeasured',
              'verification': {'source_files': len(protocol['sources']), 'frozen_artifacts': len(snapshot),
                               'prepared_regeneration_and_hash': True, 'dependencies_preflight': True,
                               'v7_parent_v24_origin_unchanged': True, 'all5_raw_failure_provenance_and_control_parity': True,
                               'original_freeze_excludes_transport_status_report': True},
              'state': status['state'], 'exit_code': status['exit_code'], 'gates': report['gates'],
              'wall_seconds': (dt.datetime.fromisoformat(status['finished_at']) - dt.datetime.fromisoformat(status['started_at'])).total_seconds(),
              'capability': dict(capability, response=echo, openapi_body_preserved=False),
              'costs': report['costs'], 'preflight_CPU_workers': {name: worker_costs(root, name) for name in ('cpu_native', 'cpu_predicates')},
              'metadata_states': {path + ':' + state: count for (path, state), count in metadata_states.items()},
              'prelaunch_metadata_calls': len(prelaunch), 'total_recorded_HTTP_attempts_including_prelaunch': 33,
              'known_completion_usage_only': {'input_tokens': 42, 'output_tokens': 10, 'scope': 'capability echo only'},
              'unknown_task_usage_attempts': 8, 'task_usage_fully_known': False, 'task_actual_usage': None,
              'task_semantic_review': 'unavailable: no task completion body received',
              'code_envelopes_observed': 0, 'Qwen_predicates_calibrated': 0, 'defined_predicate_calibration_denominator': 4,
              'ambiguous_metadata_observed': 0, 'input_generation_calls_sent': 0, 'model_authored_assertions': 'not in track',
              'arm_comparison': 'not executed; exported contexts only', 'witness_only_detected_bugs': 3,
              'rows': rows, 'raw_Qwen_task_artifacts': artifacts,
              'root_cause_limit': 'timeouts then completion503/404 and tokenizer HTTP errors; no server logs/body, cannot distinguish server/tunnel/backend cause',
              'report_limitations': ['Task token counters0 mean no recorded usage, not zero actual usage.',
                  'Generation zeros are blocked-stage defaults, not measured efficacy.',
                  'report semantic_review pending is hardcoded; task review is unavailable.',
                  'No code/predicate envelopes exist to judge the prospective decoder.',
                  'OpenAPI advertisement is recorded as digest+decision only, not an independently replayable body.'],
              'semantic_review_authority': 'root plus independent clean-context v25_terminal_review; no human semantic-gold claim',
              'Luna_probe': 'previous separate null; unpooled', 'callback_handled': True,
              'advance_to_comparison': False, 'advance_to_benchmark': False,
              'analysis_time_evidence_hashes': {name: sha(root / name) for name in evidence_names}}
    output = Path(__file__).with_suffix('.json')
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if output.exists():
        assert read(output) == result
    else:
        output.write_text(encoded)
    print(json.dumps({k: v for k, v in result.items() if k not in ('analysis_time_evidence_hashes', 'raw_Qwen_task_artifacts', 'rows')}, indent=2))
    print(json.dumps([{k: v for k, v in row.items() if k not in ('completion_attempts', 'tokenizer_attempts', 'witness_only_examples')} for row in rows], indent=2))


if __name__ == '__main__':
    main()
