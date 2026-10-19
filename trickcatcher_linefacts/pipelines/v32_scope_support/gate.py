"""Five-case prospective feasibility gate. Stops before dependent phases; no comparison."""
import argparse
from collections import Counter
import fcntl
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import threading

from . import fixtures
from .binding import observation
from .common import D, digest, immutable, task_for, worker_identity, write_json, strict_json
from .diagnostic_client import Client, SlotFailure
from .evidence import (qualify, contract_results, hypothesis_evidence, replay,
                       replay_inputs, shared_selection, cumulative_support)
from .interfaces import SCHEMAS, input_schema, messages, parse, envelope, control_contexts
from .paths import DATA_OUT

HERE = Path(__file__).resolve().parent
ROOT = DATA_OUT / 'feasibility5'
ECHO_SCHEMA = {'type': 'object', 'properties': {'schema_gate': {'const': True}},
               'required': ['schema_gate'], 'additionalProperties': False}


def source_files():
    return {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.rglob('*')) if p.is_file() and
            '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p.suffix != '.pyc'}


def dependencies():
    return {'python': sys.version, 'worker_identity': worker_identity(),
            **{x: importlib.metadata.version(x) for x in ('hypothesis', 'jsonschema', 'httpx', 'jinja2')}}


def packets():
    return [{'case': c, 'pool': fixtures.discovery_pool(c), 'bank': fixtures.semantic_bank(c)} for c in fixtures.cases()]


def freeze(root=ROOT):
    path = root / 'prepared.json'
    data = json.loads(path.read_text()) if path.exists() else packets()
    assert [p['case'] for p in data] == fixtures.cases()
    immutable(path, data)
    immutable(root / 'protocol.json', {'sources': source_files(), 'dependencies': dependencies(),
                                      'prepared_hash': digest(data), 'task_cap': 30, 'echo_cap': 1,
                                      'scope': 'seen5 feasibility only, finite authored calibration; no full comparison or benchmark',
                                      'envelope': 'bare payload or one entire matching fence; no content repair',
                                      'gate_policy': 'A4 calibrated+ambiguous unknown; B admission supported or fully-known nontrigger candidate; C cumulative novel witness/consistent contrast/abstention'})
    return data


def verify_snapshot(root=ROOT):
    freeze(root)
    snapshot = json.loads((root / 'run_frozen.json').read_text())
    for name, sha in snapshot.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != sha:
            raise ValueError('frozen_data_drift:' + name)


def finish(root, phase, passed):
    names = ('requests', 'artifacts', 'prepared_cases', 'hypothesis_cases', 'generation',
             'contexts', 'native_executions', 'predicate_executions')
    data = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for name in names for p in sorted((root / name).rglob('*.json'))}
    for name in ('protocol.json', 'prepared.json', 'capability.json', 'gates.json',
                 'capability_request.json', 'capability_response.json'):
        if (root / name).exists():
            data[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    immutable(root / 'run_frozen.json', data)
    return {'phase': phase, 'passed': passed}


def advertised_guided_json(document):
    try:
        schema = document['paths']['/v1/chat/completions']['post']['requestBody']['content']['application/json']['schema']
    except (KeyError, TypeError):
        return False
    def visit(node, seen):
        if type(node) is not dict:
            return False
        if '$ref' in node:
            ref = node['$ref']
            if ref in seen or not ref.startswith('#/'):
                return False
            value = document
            for key in ref[2:].split('/'):
                value = value[key]
            return visit(value, seen | {ref})
        return 'guided_json' in node.get('properties', {}) or any(
            visit(child, seen) for kind in ('anyOf', 'allOf', 'oneOf') for child in node.get(kind, []))
    try:
        return visit(schema, set())
    except (KeyError, TypeError):
        return False


def choose_backend(client, root=ROOT):
    path = root / 'capability.json'
    if path.exists():
        result = json.loads(path.read_text())
        for name in ('capability_request.json', 'capability_response.json'):
            if name in result and digest(json.loads((root / name).read_text())) != result[name]:
                raise ValueError('capability_evidence_drift')
        return result
    result = {'mode': 'plain', 'advertised': False, 'echo_requested': False}
    try:
        document = client.call('/openapi.json', timeout=15)
        result.update(openapi_hash=digest(document), advertised=advertised_guided_json(document))
    except Exception as exc:
        result.update(metadata_error=type(exc).__name__)
    if result['advertised']:
        result['echo_requested'] = True
        req = {'slot': 'capability__echo', 'stage': 'echo', 'seed': D['seed'],
               'messages': [{'role': 'user', 'content': 'Output exactly the single word NOT_JSON. Do not output JSON.'}],
               'guided_schema': ECHO_SCHEMA}
        immutable(root / 'capability_request.json', req)
        result['capability_request.json'] = digest(req)
        try:
            response = client.complete(req)
            immutable(root / 'capability_response.json', response)
            result['capability_response.json'] = digest(response)
            # Enforcement probe is BARE JSON, never run through the task fence decoder.
            parsed = strict_json(response['text'])
            good = (response['finish_reason'] == 'stop' and type(parsed) is dict
                    and set(parsed) == {'schema_gate'} and type(parsed['schema_gate']) is bool
                    and parsed['schema_gate'] is True)
            result.update(echo_passed=good, mode='guided_json' if good else 'plain')
        except (SlotFailure, ValueError) as exc:
            result.update(echo_passed=False, echo_error=type(exc).__name__)
    return immutable(path, result)


def valid(record):
    return record is not None and record.get('state') == 'valid'


def contract_artifact(meta, predicate):
    if not valid(meta) or (meta['parsed']['decision'] == 'proposed' and not valid(predicate)):
        return {'state': 'failed', 'reason': 'missing_valid_metadata_or_predicate'}
    m = meta['parsed']
    return {'state': 'valid', 'value': {'decision': m['decision'], 'spec_quote': m['spec_quote'],
                                       'domain': m['input_domain'], 'relation': m['required_relation'],
                                       'uncertainty': m['uncertainty'],
                                       'predicate_source': predicate['parsed']['source'] if valid(predicate) else ''}}


def hypothesis_artifact(meta, trigger):
    if not valid(meta) or (meta['parsed']['verdict'] == 'mismatch' and not valid(trigger)):
        return {'state': 'failed', 'reason': 'missing_valid_hypothesis_or_trigger'}
    m = meta['parsed']
    return {'state': 'valid', 'value': {'verdict': m['verdict'], 'target_line': m['target_line'],
                                       'claim': m['explanation'], 'trigger_condition': m['trigger_condition'],
                                       'trigger_source': trigger['parsed']['source'] if valid(trigger) else ''}}


def b_ok(row):
    if not valid(row['records']['behavior']) or not valid(row['records']['hypothesis']):
        return False
    verdict = row['records']['hypothesis']['parsed']['verdict']
    if row['case'] in ('f02', 'f04', 'f06'):
        return (valid(row['hypothesis']) and verdict == 'mismatch'
                and (row['support']['state'] == 'observed_supported' or provisional(row['support'])))
    if row['case'] == 'f14':
        return (verdict == 'consistent' and bool(row['checks'])
                and len(row['pool']) == len(row['checks'])
                and all(x.get('state') == 'evaluated' and x.get('value') is True for x in row['checks'])
                and all(x['execution']['native_checked'] and observation(x['execution']) is not None
                        for x in row['pool']))
    return verdict == 'unknown'


def provisional(support):
    return (support['state'] == 'unverified' and support.get('complete_coverage') is True
            and support.get('reason') == 'no_triggered_violation_in_finite_pool'
            and not support['witness_indices'] and not support['counterexample_indices']
            and bool(support['trigger_results'])
            and all(x.get('state') == 'evaluated' and x.get('value') is False
                    for x in support['trigger_results']))


def candidate_context(context, hyp):
    context = dict(context)
    if provisional(hyp['support']):
        # Separate from the verified field: a candidate is a prospective test request.
        context.update(unverified_candidate=hyp['hypothesis']['value'],
                       candidate_status='unverified_candidate',
                       candidate_admission_reason=hyp['support']['reason'])
    return context


def run(client, root=ROOT, backend=None):
    data = freeze(root)
    if (root / 'run_frozen.json').exists():
        verify_snapshot(root); return
    mode = backend or choose_backend(client, root)
    immutable(root / 'capability.json', mode)

    def ask(case, stage, **context):
        task = task_for(case); uid = case['fixture_id']; slot = uid + '__' + stage
        request = {'slot': slot, 'stage': stage, 'task_hash': task['task_hash'],
                   'seed': D['seed'] + int(uid[1:]), 'messages': messages(stage, task, **context)}
        if mode['mode'] == 'guided_json' and stage not in ('predicate', 'trigger'):
            request['guided_schema'] = input_schema(task) if stage == 'inputs' else SCHEMAS[stage]
        immutable(root / 'requests' / (slot + '.json'), request)
        if len(list((root / 'requests').glob('*.json'))) > D['task_call_cap']:
            raise ValueError('task_call_budget')
        path = root / 'artifacts' / (slot + '.json')
        if path.exists():
            return json.loads(path.read_text())
        record = {'request_hash': digest(request)}
        try:
            response = client.complete(request); record['response'] = response
        except SlotFailure as exc:
            return immutable(path, dict(record, state='failed', reason=str(exc)))
        try:
            if response['finish_reason'] != 'stop':
                raise ValueError('incomplete_finish_reason')
            payload, framing = envelope(response['text'], 'code' if stage in ('predicate', 'trigger') else 'json')
            record.update(decoded_payload=payload, envelope=framing)
            parsed, payload, framing = parse(stage, response['text'], task)
            record.update(state='valid', parsed=parsed, decoded_payload=payload, envelope=framing)
        except ValueError as exc:
            record.update(state='failed', reason=str(exc))
        return immutable(path, record)

    # A: complete only the five contract/ambiguity cases before deciding whether to proceed.
    phase_a = []
    for packet in data:
        case = packet['case']; uid = case['fixture_id']; task = task_for(case)
        path = root / 'prepared_cases' / (uid + '.json')
        if path.exists():
            row = json.loads(path.read_text())
        else:
            meta = ask(case, 'meta'); predicate = None
            if valid(meta) and meta['parsed']['decision'] == 'proposed':
                predicate = ask(case, 'predicate', metadata=meta['parsed'])
            contract = contract_artifact(meta, predicate)
            qualification = qualify(case, contract, packet['bank'], root / 'predicate_executions')
            row = {'case': uid, 'records': {'meta': meta, 'predicate': predicate},
                   'contract': contract, 'qualification': qualification}
            immutable(path, row)
        phase_a.append(row)
        pool = [replay(task, args, root / 'native_executions') for args in packet['pool']['all_inputs']]
        checks = contract_results(row['contract'], row['qualification'], pool, root / 'predicate_executions')
        selected = shared_selection(pool, checks, {'state': 'unverified', 'witness_indices': []})
        ctx = control_contexts(task, selected['rows'], row['records'], row['qualification'], row['contract'],
                               {'state': 'missing'}, {'state': 'unverified'})
        immutable(root / 'contexts' / (uid + '__phaseA.json'), ctx)
        print(uid, 'A', row['qualification']['state'], flush=True)
    passed_a = all((r['qualification']['state'] == 'calibrated' if r['case'] != 'f13' else
                    valid(r['records']['meta']) and r['records']['meta']['parsed']['decision'] == 'unknown'
                    and r['qualification']['state'] == 'unknown_spec') for r in phase_a)
    gates = {'A': passed_a, 'B': None, 'C': None}
    if not passed_a:
        immutable(root / 'gates.json', gates); return finish(root, 'A', False)

    # B: admission only. Fully-known no-trigger candidates may request one witness probe.
    phase_b = []
    for packet in data:
        case = packet['case']; uid = case['fixture_id']; task = task_for(case)
        path = root / 'hypothesis_cases' / (uid + '.json')
        prepared = next(x for x in phase_a if x['case'] == uid)
        if path.exists():
            row = json.loads(path.read_text())
            contexts = control_contexts(task, row['selection']['rows'], row['records'], prepared['qualification'],
                                        prepared['contract'], row['hypothesis'], row['support'])
            contexts['verified_hyp']['concept_metadata'] = prepared['records']['meta']['parsed']
            immutable(root / 'contexts' / (uid + '__phaseB.json'), contexts)
            phase_b.append(row); continue
        pool = [replay(task, args, root / 'native_executions') for args in packet['pool']['all_inputs']]
        checks = contract_results(prepared['contract'], prepared['qualification'], pool, root / 'predicate_executions')
        selected = shared_selection(pool, checks, {'state': 'unverified', 'witness_indices': []})
        behavior = ask(case, 'behavior')
        h = ask(case, 'hypothesis', concept_metadata=prepared['records']['meta']['parsed'],
                contract=prepared['contract'].get('value'), behavior=behavior.get('parsed'),
                common_rows=selected['rows'], obligation_checks=[checks[i] for i in selected['indices']])
        trigger = ask(case, 'trigger', hypothesis=h['parsed']) if valid(h) and h['parsed']['verdict'] == 'mismatch' else None
        combined = hypothesis_artifact(h, trigger)
        support = hypothesis_evidence(task, combined, pool, checks, root / 'predicate_executions')
        records = dict(prepared['records'], behavior=behavior, hypothesis=h, trigger=trigger)
        row = {'case': uid, 'records': records, 'hypothesis': combined, 'support': support,
               'pool': pool, 'checks': checks, 'selection': selected}
        immutable(path, row); phase_b.append(row)
        contexts = control_contexts(task, selected['rows'], records, prepared['qualification'],
                                    prepared['contract'], combined, support)
        contexts['verified_hyp']['concept_metadata'] = prepared['records']['meta']['parsed']
        immutable(root / 'contexts' / (uid + '__phaseB.json'), contexts)
        print(uid, 'B', support['state'], flush=True)
    gates['B'] = all(b_ok(r) for r in phase_b)
    if not gates['B']:
        immutable(root / 'gates.json', gates); return finish(root, 'B', False)

    # C: one named-JSON input call per case. This is feasibility, not an arm comparison.
    for packet in data:
        case = packet['case']; uid = case['fixture_id']; task = task_for(case)
        path = root / 'generation' / (uid + '.json')
        if path.exists():
            continue
        prepared = next(x for x in phase_a if x['case'] == uid)
        hyp = next(x for x in phase_b if x['case'] == uid)
        context = candidate_context(json.loads((root / 'contexts' / (uid + '__phaseB.json')).read_text())['verified_hyp'], hyp)
        artifact = ask(case, 'inputs', context=context)
        replays = replay_inputs(task, artifact['parsed'], root / 'native_executions') if valid(artifact) else []
        observed = [r for r in replays if r['state'] == 'observed']
        checks = contract_results(prepared['contract'], prepared['qualification'], observed, root / 'predicate_executions')
        update = cumulative_support(task, hyp['hypothesis'], hyp['pool'], hyp['checks'],
                                    replays, checks, root / 'predicate_executions', valid(artifact))
        support = update['support']
        if uid in ('f02', 'f04', 'f06'):
            passed = valid(artifact) and bool(update['novel_accepted_slots'])
        elif uid == 'f14':
            passed = (valid(artifact) and not update['failed_proposal_slots']
                and len(observed) == len(checks) and all(x.get('state') == 'evaluated' and x.get('value') is True
                                                       for x in hyp['checks'] + checks)
                and any(r['proposal']['purpose'] == 'contrast'
                and observation(r['execution']) is not None and observation(r['execution'])['status'] == 'ok'
                and check.get('state') == 'evaluated' and check.get('value') is True
                for r, check in zip(observed, checks)))
        else:
            passed = valid(artifact) and not artifact['parsed']['inputs']
        immutable(path, {'case': uid, 'artifact': artifact, 'replays': replays, 'checks': checks,
                         'support': support, 'cumulative_update': update,
                         'initial_support': hyp['support'], 'passed': passed})
        print(uid, 'C', passed, flush=True)
    gates['C'] = all(json.loads(p.read_text())['passed'] for p in (root / 'generation').glob('*.json'))
    immutable(root / 'gates.json', gates); return finish(root, 'C', gates['C'])


def costs(root=ROOT):
    groups = {'task': Counter(), 'capability': Counter()}
    for p in (root / 'transport/calls').glob('*/attempts.json'):
        group = 'capability' if p.parent.name == 'capability__echo' else 'task'
        for x in json.loads(p.read_text()):
            groups[group]['physical_attempts'] += 1
            groups[group]['input_tokens'] += x.get('input_tokens', 0)
            groups[group]['output_tokens'] += x.get('output_tokens', 0)
            groups[group]['unknown_usage_attempts'] += x['state'] != 'received'
    workers = {}
    for group in ('native_executions', 'predicate_executions'):
        records = [json.loads(p.read_text()) for p in (root / group).rglob('attempt.json')]
        results = [json.loads(p.read_text()) for p in (root / group).rglob('result.json')]
        workers[group] = {'reserved_attempts': len(records),
                          'recorded_process_launches': sum(x.get('launched') is True for x in records),
                          'unresolved_launch_reservations': sum(x.get('launched') is None for x in records),
                          'failed_workers': sum(x.get('state') == 'failed' for x in records),
                          'cached_unknown_after_interruption': sum(x.get('resume_cached_unknown', False) for x in records)}
        if group == 'native_executions':
            workers[group]['reported_PUT_calls'] = sum(x.get('put_calls', 0) for x in results)
            workers[group]['unknown_PUT_calls_upper_bound'] = sum(
                x.get('status') == 'unresolved' and 'put_calls' not in x for x in results)
        else:
            workers[group]['reported_predicate_evaluations'] = sum(x.get('evaluations_attempted', 0) for x in results)
            workers[group]['unknown_predicate_evaluations_upper_bound'] = sum(
                len(json.loads((p.parent / 'job.json').read_text()).get('rows', []))
                for p in (root / group).rglob('result.json')
                if 'evaluations_attempted' not in json.loads(p.read_text())
                and json.loads((p.parent / 'attempt.json').read_text()).get('launched') is not False)
    return {'groups': groups, 'task_slots': len(list((root / 'requests').glob('*.json'))),
            'workers': workers,
            'execution_cost_scope': 'recorded launches/reported calls with explicit interrupted upper bounds; CPU preflight separate',
            'metadata_calls': sum(1 for _ in (root / 'transport/metadata_calls.jsonl').open())
            if (root / 'transport/metadata_calls.jsonl').exists() else 0}


def report(root=ROOT):
    verify_snapshot(root); data = freeze(root)
    gates = json.loads((root / 'gates.json').read_text()); stage_counts = {}; rows = []
    for p in (root / 'requests').glob('*.json'):
        req = json.loads(p.read_text()); art = json.loads((root / 'artifacts' / p.name).read_text())
        stage_counts.setdefault(req['stage'], Counter())[art.get('reason', art['state'])] += 1
    for packet in data:
        case = packet['case']; uid = case['fixture_id']
        prepared = json.loads((root / 'prepared_cases' / (uid + '.json')).read_text())
        row = {'case': uid, 'qualification': prepared['qualification'],
               'metadata_state': prepared['records']['meta']['state'],
               'code_state': (prepared['records']['predicate']['state'] if prepared['records']['predicate']
                              else 'not_applicable_unknown' if valid(prepared['records']['meta'])
                              and prepared['records']['meta']['parsed']['decision'] == 'unknown'
                              else 'blocked_metadata_failure'),
               'phaseB': 'blocked', 'phaseC': 'blocked',
               'novel_generated_inputs': 0, 'novel_bug_inputs': 0, 'new_detected_case': False}
        bp = root / 'hypothesis_cases' / (uid + '.json')
        if bp.exists():
            hyp = json.loads(bp.read_text()); row['phaseB'] = hyp['support']['state']
            row.update(B_admitted=b_ok(hyp), provisional_admission=provisional(hyp['support']),
                       initial_support=hyp['support']['state'],
                       initial_unknown_indices=hyp['support'].get('unknown_indices', []))
            shared = {r['input_id'] for r in hyp['pool']}
            baseline = {r['input_id'] for r in hyp['pool'] if observation(r['execution']) is not None
                        and fixtures.expected(case, r['arguments']) is not None and not fixtures.same_observation(
                            observation(r['execution']), fixtures.expected(case, r['arguments']))}
            row['witness_only_bug_inputs'] = len(baseline)
            cp = root / 'generation' / (uid + '.json')
            if cp.exists():
                gen = json.loads(cp.read_text()); row['phaseC'] = 'passed' if gen['passed'] else 'failed'
                row.update(initial_support=hyp['support']['state'], final_support=gen['support']['state'],
                           provisional_admission=provisional(hyp['support']),
                           raw_inputs=len(gen['replays']), observed_inputs=sum(x['state'] == 'observed' for x in gen['replays']),
                           accepted_witness_inputs=len(gen['cumulative_update']['accepted_slots']),
                           novel_accepted_witness_inputs=len(gen['cumulative_update']['novel_accepted_slots']),
                           failed_proposal_slots=gen['cumulative_update']['failed_proposal_slots'])
                observed = {r['input_id'] for r in gen['replays'] if r['state'] == 'observed'}
                bugs = {r['input_id'] for r in gen['replays'] if r['state'] == 'observed'
                        and fixtures.expected(case, r['arguments']) is not None and not fixtures.same_observation(
                            observation(r['execution']), fixtures.expected(case, r['arguments']))}
                row.update(novel_generated_inputs=len(observed - shared), novel_bug_inputs=len(bugs - shared),
                           new_detected_case=bool(bugs) and not baseline)
        rows.append(row)
    result = {'scope': 'seen5 prospective feasibility only; no full comparison/benchmark', 'gates': gates,
              'backend': json.loads((root / 'capability.json').read_text()), 'stage_counts': stage_counts,
              'rows': rows, 'costs': costs(root), 'semantic_review': 'pending', 'advance_to_comparison': False}
    return immutable(root / 'report.json', result)


def preflight(root=ROOT):
    from .cpu_contracts import authored_contract
    checks = []
    for packet in packets():
        case = packet['case']; task = task_for(case)
        cpu = authored_contract(case)
        q = qualify(case, cpu, packet['bank'], root / 'cpu_predicates')
        native = replay(task, packet['pool']['public_base_inputs'][0], root / 'cpu_native')
        checks.append({'case': case['fixture_id'], 'calibration': q['state'], 'native': native['execution']['native_checked']})
    result = {'sources': source_files(), 'dependencies': dependencies(), 'prepared_hash': digest(packets()),
              'checks': checks, 'passed': all(r['native'] and r['calibration'] in ('calibrated', 'unknown_spec') for r in checks),
              'scope': 'authored CPU controls only, not model efficacy'}
    if (root / 'preflight.json').exists():
        previous = json.loads((root / 'preflight.json').read_text())
        immutable(root / 'cpu_attempts' / (digest(previous['sources']) + '.json'), previous)
    immutable(root / 'cpu_attempts' / (digest(result['sources']) + '.json'), result)
    write_json(root / 'preflight.json', result)
    return result


def verify_preflight(root=ROOT):
    data = json.loads((root / 'preflight.json').read_text())
    if not data['passed'] or data['sources'] != source_files() or data['dependencies'] != dependencies():
        raise ValueError('CPU_source_or_dependency_drift')
    if data['prepared_hash'] != digest(freeze(root)):
        raise ValueError('CPU_prepared_data_drift')
    return data


def main():
    p = argparse.ArgumentParser(); p.add_argument('command', choices=['preflight', 'freeze', 'online', 'report'])
    p.add_argument('--online', action='store_true'); args = p.parse_args(); ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'controller.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('controller_already_running')
        if args.command == 'preflight': result = preflight()
        elif args.command == 'freeze': result = {'cases': len(freeze())}
        elif args.command == 'report': result = report()
        else:
            if not args.online: raise SystemExit('explicit_--online_required')
            verify_preflight(); freeze()
            if (ROOT / 'run_frozen.json').exists():
                result = report(); print(json.dumps(result, indent=2)); return
            client = Client(ROOT / 'transport'); stop = threading.Event()
            def ping():
                while not stop.wait(1200):
                    try: client.call('/models', timeout=8)
                    except Exception: pass
            thread = threading.Thread(target=ping, daemon=True); thread.start()
            try:
                run(client); stop.set(); thread.join(timeout=12); result = report()
            finally:
                stop.set(); thread.join(timeout=12); client.close()
        print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
