"""Executable-obligation diagnostic9. No automatic benchmark or expected-output synthesis."""
import argparse
from collections import Counter
import fcntl
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import sys
import threading

from . import fixtures
from .binding import observation
from .common import D, digest, immutable, task_for, worker_identity
from .contracts import messages, parse
from .diagnostic_client import SlotFailure, write_json
from .evidence import (contract_results, feedback_for, hypothesis_evidence, qualify,
                       replay, replay_inputs, shared_selection)
from .paths import DATA_OUT

HERE = Path(__file__).resolve().parent
ROOT = DATA_OUT / 'obligation_diagnostic'
ARMS = tuple(D['arms'])


def files():
    return {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.rglob('*')) if p.is_file() and
            '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and p.suffix != '.pyc'}


def dependencies():
    return {'python': sys.version, 'worker_identity': worker_identity(), **{n: importlib.metadata.version(n)
                                      for n in ('hypothesis', 'jsonschema', 'httpx', 'jinja2')}}


def freeze(root=ROOT):
    source = files()
    packet_path = root / 'prepared_packets.json'
    if packet_path.exists():
        packets = json.loads(packet_path.read_text())
    else:
        packets = [{'case': c, 'pool': fixtures.discovery_pool(c), 'semantic_bank': fixtures.semantic_bank(c)}
                   for c in fixtures.cases()]
        immutable(packet_path, packets)
    if [p['case'] for p in packets] != fixtures.cases():
        raise ValueError('prepared_fixture_drift')
    immutable(root / 'protocol.json', {'source': source, 'dependencies': dependencies(),
                                      'packets_hash': digest(packets), 'max_logical_calls': D['max_model_calls'],
                                      'semantic_scope': 'diagnostic-only authored finite calibration; not human gold or deployable semantic proof',
                                      'scoring': 'same independent fixture oracle for all arms after generation freeze',
                                      'advance_to_benchmark': False})
    return packets


def value(artifact):
    return artifact.get('value') if artifact.get('state') == 'valid' else None


def base_evidence(packet, task, root):
    return [replay(task, x, root / 'native_executions') for x in packet['pool']['public_base_inputs']]


def preflight(root=ROOT):
    """Authored positive/negative controls, not model success; no online transport."""
    from .cpu_contracts import authored_contract
    source = files()
    packets = [{'case': c, 'pool': fixtures.discovery_pool(c), 'semantic_bank': fixtures.semantic_bank(c)}
               for c in fixtures.cases()]
    checks = []
    for packet in packets:
        case = packet['case']; task = task_for(case)
        native = base_evidence(packet, task, root)
        contract = authored_contract(case)
        qualification = qualify(case, contract, packet['semantic_bank'], root / 'cpu_predicates')
        known = case['evaluator']['witness']
        witness_checked = None
        if known:
            from .binding import from_literal
            sample = replay(task, from_literal(task, known), root / 'cpu_evaluator_only')
            predicate = contract_results(contract, qualification, [sample], root / 'cpu_predicates')[0]
            witness_checked = predicate.get('state') == 'evaluated' and predicate.get('value') is False
        checks.append({'case': case['fixture_id'], 'native_checked': all(x['execution']['native_checked'] for x in native),
                       'calibration': qualification['state'], 'authored_bug_witness': witness_checked})
    passed = all(x['native_checked'] and x['calibration'] in ('calibrated', 'unknown_spec')
                 and x['authored_bug_witness'] is not False for x in checks)
    result = {'source': source, 'dependencies': dependencies(), 'packets_hash': digest(packets),
              'scope': 'CPU controls only; no Qwen/semantic efficacy claim', 'checks': checks, 'passed': passed}
    old = root / 'preflight.json'
    if old.exists():
        previous = json.loads(old.read_text())
        immutable(root / 'preflight_attempts' / (digest(previous['source']) + '.json'), previous)
    immutable(root / 'preflight_attempts' / (digest(source) + '.json'), result)
    write_json(old, result)
    return result


def verify_preflight(root=ROOT):
    check = json.loads((root / 'preflight.json').read_text())
    if not check['passed'] or check['source'] != files() or check['dependencies'] != dependencies():
        raise ValueError('CPU_gate_failed_or_source_drift')
    return check


def snapshot(root, names):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for name in names for p in sorted((root / name).rglob('*.json'))}


def verify_snapshot(root, name):
    for path, sha in json.loads((root / name).read_text()).items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != sha:
            raise ValueError('frozen_data_drift:' + path)


def run(client, root=ROOT):
    packets = freeze(root)
    if (root / 'generation_frozen.json').exists():
        verify_snapshot(root, 'generation_frozen.json')
        return
    ordered = list(packets); random.Random(D['seed']).shuffle(ordered)

    def ask(case, task, stage, arm='shared', **context):
        slot = case['fixture_id'] + '__' + arm + '__' + stage
        request = {'slot': slot, 'stage': stage, 'task_hash': task['task_hash'],
                   'seed': D['seed'] + int(case['fixture_id'][1:]), 'messages': messages(stage, task, **context)}
        immutable(root / 'requests' / (slot + '.json'), request)
        if len(list((root / 'requests').glob('*.json'))) > D['max_model_calls']:
            raise ValueError('logical_call_budget')
        path = root / 'artifacts' / (slot + '.json')
        if path.exists():
            return json.loads(path.read_text())
        try:
            response = client.complete(request)
        except SlotFailure as exc:
            return immutable(path, {'state': 'failed', 'reason': str(exc), 'request_hash': digest(request)})
        record = {'request_hash': digest(request), 'response': response}
        try:
            if response['finish_reason'] != 'stop':
                raise ValueError('incomplete_finish_reason')
            record.update(state='valid', value=parse(stage, response['text'], task))
        except ValueError as exc:
            record.update(state='failed', reason=str(exc))
        return immutable(path, record)

    for packet in ordered:
        case = packet['case']; uid = case['fixture_id']; task = task_for(case)
        destination = root / 'preparation' / (uid + '.json')
        if destination.exists():
            continue
        base = base_evidence(packet, task, root)
        if not all(x['execution']['native_checked'] for x in base):
            raise RuntimeError('native_preflight_required')
        contract = ask(case, task, 'contract')
        behavior = ask(case, task, 'behavior')
        qualification = qualify(case, contract, packet['semantic_bank'], root / 'predicate_executions')
        pool = [replay(task, args, root / 'native_executions') for args in packet['pool']['all_inputs']]
        predicate_checks = contract_results(contract, qualification, pool, root / 'predicate_executions')
        context = {'contract_claim': value(contract), 'obligation_id': 'O1',
                   'qualification_state': qualification['state'], 'behavior_claim': value(behavior),
                   'public_base_evidence': base}
        initial = ask(case, task, 'hypothesis', **context)
        before = hypothesis_evidence(task, initial, pool, predicate_checks, root / 'predicate_executions')
        final = ask(case, task, 'hyp_revision', initial_hypothesis=value(initial),
                    initial_support_state=before['state'],
                    fixed_pool_feedback=feedback_for(pool, predicate_checks, before), **context)
        after = hypothesis_evidence(task, final, pool, predicate_checks, root / 'predicate_executions')
        selection = shared_selection(pool, predicate_checks, after)
        immutable(destination, {'case': uid, 'contract': contract, 'behavior': behavior,
                                'qualification': qualification, 'initial_hypothesis': initial,
                                'initial_support': before, 'final_hypothesis': final, 'final_support': after,
                                'pool': pool, 'contract_checks': predicate_checks, 'selection': selection})
        print(uid, 'prepared', qualification['state'], before['state'], after['state'], flush=True)
    immutable(root / 'preparation_frozen.json', snapshot(root, ('preparation',)))
    verify_snapshot(root, 'preparation_frozen.json')
    for packet in ordered:
        case = packet['case']; uid = case['fixture_id']; task = task_for(case)
        prepared = json.loads((root / 'preparation' / (uid + '.json')).read_text())
        destination = root / 'generation' / (uid + '.json')
        if destination.exists():
            continue
        contract = value(prepared['contract'])
        hypothesis = value(prepared['final_hypothesis'])
        selected = prepared['selection']
        arm_results = {}
        order = list(ARMS); random.Random(D['seed'] + int(uid[1:])).shuffle(order)
        for arm in order:
            context = {'common_inputs_and_native_traces': selected['rows']}
            if arm == 'text_hyp':
                context['unverified_model_concept'] = contract
                context['unverified_model_hypothesis'] = hypothesis
            if arm == 'verified_hyp':
                qualified = prepared['qualification']['state'] == 'calibrated'
                context['contract'] = contract if qualified else None
                context['qualification_state'] = prepared['qualification']['state']
                context['hypothesis'] = hypothesis if prepared['final_support']['state'] == 'observed_supported' else None
                context['hypothesis_support_state'] = prepared['final_support']['state']
                context['shared_input_obligation_checks'] = [prepared['contract_checks'][i] for i in selected['indices']]
            rounds = []
            previous = None
            for stage in ('inputs', 'revision'):
                extra = {} if previous is None else {'previous_proposal': previous['artifact'].get('value'),
                                                      'execution_feedback': previous['feedback']}
                artifact = ask(case, task, stage, arm, **context, **extra)
                replays = replay_inputs(task, value(artifact), root / 'native_executions') if value(artifact) else []
                feedback = list(replays)
                verified = []
                if arm == 'verified_hyp':
                    observed = [r for r in replays if r['state'] == 'observed']
                    checks = contract_results(prepared['contract'], prepared['qualification'], observed,
                                              root / 'predicate_executions')
                    evidence = hypothesis_evidence(task, prepared['final_hypothesis'], observed, checks,
                                                   root / 'predicate_executions')
                    for i, r in enumerate(observed):
                        verified.append({'slot': r['slot'], 'obligation': checks[i],
                                         'trigger': evidence['trigger_results'][i] if evidence['trigger_results'] else None,
                                         'reach_and_violation': i in evidence['witness_indices'],
                                         'accepted': (prepared['qualification']['state'] == 'calibrated'
                                                      and prepared['final_support']['state'] == 'observed_supported'
                                                      and i in evidence['witness_indices']),
                                         'scope': 'individual observed violation, not universal trigger proof'})
                    feedback = {'native_replays': replays, 'contract_checks': verified}
                previous = {'stage': stage, 'artifact': artifact, 'replays': replays,
                            'feedback': feedback, 'mechanical_acceptance': verified}
                rounds.append(previous)
            arm_results[arm] = {'rounds': rounds}
        immutable(destination, {'case': uid, 'arms': arm_results})
        print(uid, 'generation_complete', flush=True)
    immutable(root / 'generation_frozen.json', snapshot(root, ('requests', 'artifacts', 'preparation',
                                                              'generation', 'native_executions', 'predicate_executions')))


def cost_report(root=ROOT):
    attempts = []
    for p in (root / 'transport/calls').glob('*/attempts.json'):
        attempts += json.loads(p.read_text())
    meta = [row for p in (root / 'transport/tokens').glob('*.attempts.json') for row in json.loads(p.read_text())]
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
    return {'logical_slots': len(list((root / 'requests').glob('*.json'))),
            'completion_attempts': len(attempts), 'input_tokens': sum(x.get('input_tokens', 0) for x in attempts),
            'output_tokens': sum(x.get('output_tokens', 0) for x in attempts),
            'unknown_usage_attempts': sum(x['state'] != 'received' for x in attempts),
            'tokenizer_metadata_calls': len(meta),
            'workers': workers,
            'execution_cost_scope': 'durable reservations/recorded launches and reported calls; interrupted uncertainty explicit; no automatic worker retry'}


def report(root=ROOT):
    freeze(root)
    if not (root / 'generation_frozen.json').exists():
        return {'state': 'incomplete', 'cases': len(fixtures.cases()), 'costs': cost_report(root), 'advance_to_benchmark': False}
    verify_snapshot(root, 'preparation_frozen.json'); verify_snapshot(root, 'generation_frozen.json')
    packets = json.loads((root / 'prepared_packets.json').read_text())
    rows = []; totals = {a: Counter() for a in (*ARMS, 'witness_only')}
    preparation_counts = Counter(); initial_states = Counter(); final_states = Counter()
    for packet in packets:
        case = packet['case']; uid = case['fixture_id']
        prep = json.loads((root / 'preparation' / (uid + '.json')).read_text())
        generated = json.loads((root / 'generation' / (uid + '.json')).read_text())
        preparation_counts['qualification_' + prep['qualification']['state']] += 1
        initial_states[prep['initial_support']['state']] += 1
        final_states[prep['final_support']['state']] += 1
        preparation_counts['no_supported_fault_package_cases'] += prep['final_support']['state'] != 'observed_supported'
        preparation_counts['unknown_native_pool_rows'] += sum(not x['execution']['native_checked'] for x in prep['pool'])
        preparation_counts['unknown_contract_pool_rows'] += sum(x['state'] != 'evaluated' for x in prep['contract_checks'])
        preparation_counts['unknown_initial_trigger_rows'] += sum(x['state'] != 'evaluated' for x in prep['initial_support']['trigger_results'])
        preparation_counts['unknown_final_trigger_rows'] += sum(x['state'] != 'evaluated' for x in prep['final_support']['trigger_results'])
        shared_ids = {r['input_id'] for r in prep['pool']}
        baseline = {r['input_id'] for r in prep['pool'] if observation(r['execution']) is not None
                    and fixtures.expected(case, r['arguments']) is not None
                    and not fixtures.same_observation(observation(r['execution']), fixtures.expected(case, r['arguments']))}
        totals['witness_only']['detected_cases'] += bool(baseline)
        totals['witness_only']['unique_bug_inputs'] += len(baseline)
        arms = {}
        for arm, state in generated['arms'].items():
            observed, bugs, novel_bugs = set(), set(), set()
            accepted, accepted_bugs, false_flags = set(), set(), set()
            invalid = unknown = failed = abstentions = slots = duplicates = 0
            for rnd in state['rounds']:
                if rnd['artifact']['state'] != 'valid':
                    failed += 1
                elif not rnd['artifact']['value']['inputs']:
                    abstentions += 1
                for r in rnd['replays']:
                    slots += 1
                    if r['state'] == 'invalid':
                        invalid += 1; continue
                    if r['state'] != 'observed':
                        unknown += 1; continue
                    duplicates += r['input_id'] in observed
                    observed.add(r['input_id'])
                    gold = fixtures.expected(case, r['arguments'])
                    selected_by_method = (arm != 'verified_hyp' or any(
                        x['slot'] == r['slot'] and x['accepted'] for x in rnd['mechanical_acceptance']))
                    if selected_by_method:
                        accepted.add(r['input_id'])
                    if gold is not None and not fixtures.same_observation(gold, observation(r['execution'])):
                        bugs.add(r['input_id'])
                        if selected_by_method:
                            accepted_bugs.add(r['input_id'])
                        if r['input_id'] not in shared_ids:
                            novel_bugs.add(r['input_id'])
                    elif gold is not None and arm == 'verified_hyp' and selected_by_method:
                        false_flags.add(r['input_id'])
            arms[arm] = {'unique_observed_inputs': len(observed), 'unique_bug_inputs': len(bugs),
                         'detected_case': bool(bugs), 'novel_bug_inputs_outside_full_pool': len(novel_bugs),
                         'new_detected_case_beyond_witness_only': bool(bugs) and not baseline,
                         'invalid_slots': invalid, 'unknown_slots': unknown, 'failed_stages': failed,
                         'abstention_stages': abstentions, 'oracle_unknown': uid == 'f13',
                         'candidate_slots': slots, 'duplicate_observed_slots': duplicates,
                         'novel_generated_inputs_outside_full_pool': len(observed - shared_ids)}
            arms[arm].update(selected_unique_inputs=len(accepted), selected_bug_inputs=len(accepted_bugs),
                             selected_detected_case=bool(accepted_bugs), false_verified_flags=len(false_flags),
                             selected_novel_bug_inputs_outside_full_pool=len(accepted_bugs - shared_ids),
                             selected_new_detected_case_beyond_witness_only=bool(accepted_bugs) and not baseline)
            for key, count in arms[arm].items():
                totals[arm][key] += count
        support = prep['final_support']
        false_contract_flags = [i for i, c in enumerate(prep['contract_checks'])
                                if c.get('state') == 'evaluated' and c.get('value') is False
                                and fixtures.expected(case, prep['pool'][i]['arguments']) is not None
                                and fixtures.same_observation(observation(prep['pool'][i]['execution']),
                                                             fixtures.expected(case, prep['pool'][i]['arguments']))]
        rows.append({'case': uid, 'qualification': prep['qualification'],
                     'initial_support': prep['initial_support']['state'], 'final_support': support['state'],
                     'false_contract_flag_indices': false_contract_flags,
                     'witness_only_bug_inputs': len(baseline), 'arms': arms})
    stages = {}
    for path in (root / 'requests').glob('*.json'):
        stage = json.loads(path.read_text())['stage']
        artifact = json.loads((root / 'artifacts' / path.name).read_text())
        stages.setdefault(stage, Counter())[artifact['state']] += 1
    result = {'scope': 'seen authored diagnostic9, calibrated with diagnostic gold; input-generation only',
              'cases': len(packets), 'rows': rows, 'totals': totals, 'costs': cost_report(root),
              'stage_counts': stages, 'preparation_counts': preparation_counts,
              'initial_support_states': initial_states, 'final_support_states': final_states,
              'model_expected_outputs_generated': False, 'semantic_review': 'pending_independent_review',
              'advance_to_benchmark': False}
    return immutable(root / 'report.json', result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['preflight', 'freeze', 'online', 'report'])
    p.add_argument('--online', action='store_true')
    args = p.parse_args(); ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'controller.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('controller_already_running')
        if args.command == 'preflight':
            result = preflight()
        elif args.command == 'freeze':
            result = {'cases': len(freeze())}
        elif args.command == 'report':
            result = report()
        else:
            if not args.online:
                raise SystemExit('explicit_--online_required')
            checked = verify_preflight(); packets = freeze()
            if digest(packets) != checked['packets_hash']:
                raise ValueError('CPU_prepared_packet_drift')
            from .diagnostic_client import Client
            client = Client(ROOT / 'transport'); stop = threading.Event()
            def ping():
                while not stop.wait(1200):
                    try:
                        client.call('/models', timeout=8)
                    except Exception:
                        pass
            threading.Thread(target=ping, daemon=True).start()
            try:
                run(client); result = report()
            except Exception as exc:
                write_json(ROOT / 'incomplete_status.json', {'state': 'incomplete', 'cases': 9,
                                                           'error_type': type(exc).__name__, 'costs': cost_report()})
                raise SystemExit('diagnostic_incomplete:' + type(exc).__name__) from None
            finally:
                stop.set(); client.close()
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
