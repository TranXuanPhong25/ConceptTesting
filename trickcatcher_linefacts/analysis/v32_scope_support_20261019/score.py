"""Read-only post-freeze oracle scoring; no model/PUT/predicate execution."""
from collections import Counter
import json

from run import ROOT, HERE, gate, immutable, read, sha, verify
from trickcatcher_linefacts.pipelines.v32_scope_support import fixtures
from trickcatcher_linefacts.pipelines.v32_scope_support.binding import observation
from client import costs, inspect_events


def compare(case, rows, checks):
    result = Counter()
    ids, bugs, false_ids = set(), set(), set()
    for i, row in enumerate(rows):
        check = checks[i] if i < len(checks) else {'state': 'unknown'}
        result['rows'] += 1
        actual = observation(row['execution'])
        gold = fixtures.expected(case, row['arguments'])
        if actual is not None:
            ids.add(row['input_id'])
        if check.get('state') != 'evaluated' or type(check.get('value')) is not bool:
            result['unknown_contract_rows'] += 1
        if gold is None:
            result['undefined_oracle'] += 1
        elif actual is None:
            result['unknown_native'] += 1
        else:
            bug = not fixtures.same_observation(actual, gold)
            if bug:
                bugs.add(row['input_id']); result['bug_rows'] += 1
            if check.get('state') != 'evaluated' or type(check.get('value')) is not bool:
                result['unknown_contract'] += 1
            else:
                result['known_contract'] += 1
                if check['value'] is False:
                    result['contract_flags'] += 1
                    if not bug:
                        result['false_contract_flags'] += 1; false_ids.add(row['input_id'])
                elif bug:
                    result['missed_contract_bugs'] += 1
    result.update(unique_observed_inputs=len(ids), unique_bug_inputs=len(bugs), unique_false_flag_inputs=len(false_ids))
    return dict(result), bugs


def workers(folder, predicate=False):
    attempts = [read(p) for p in folder.rglob('attempt.json')]
    results = [read(p) for p in folder.rglob('result.json')]
    return {'reserved': len(attempts), 'recorded_launches': sum(x.get('launched') is True for x in attempts),
            'unresolved_reservations': sum(x.get('launched') is None for x in attempts),
            'failed': sum(x.get('state') == 'failed' for x in attempts),
            'reported_evaluations' if predicate else 'reported_PUT_calls':
                sum(x.get('evaluations_attempted' if predicate else 'put_calls', 0) for x in results)}


def main():
    verify(); gate.verify_snapshot(ROOT)
    native = read(ROOT / 'report.json')
    rows = []
    for packet in read(ROOT / 'prepared.json'):
        case = packet['case']; uid = case['fixture_id']
        summary = dict(next(x for x in native['rows'] if x['case'] == uid))
        if uid == 'f13':
            summary.update(witness_only_bug_inputs=None, new_detected_case=None,
                           oracle_performance='not_applicable_undefined_intent')
        summary['authored_calibration_rows'] = len(packet['bank'])
        hp, gp = ROOT / 'hypothesis_cases' / (uid + '.json'), ROOT / 'generation' / (uid + '.json')
        # PhaseA always records full shared evidence even if B is blocked.
        if hp.exists():
            hyp = read(hp); pool, checks = hyp['pool'], hyp['checks']
        else:
            # Calibrated phaseA pool checks are already stored in predicate jobs.
            # Read those exact rows/results, never invoke replay/evaluate here.
            from trickcatcher_linefacts.pipelines.v32_scope_support.common import digest
            pool, checks = [], []
            prepared = read(ROOT / 'prepared_cases' / (uid + '.json'))
            if prepared['qualification']['state'] == 'calibrated':
                source = prepared['contract']['value']['predicate_source']
                cached = {}
                for jp in (ROOT / 'predicate_executions').glob('*/job.json'):
                    job = read(jp)
                    if job['kind'] != 'obligation' or job['source'] != source: continue
                    results = read(jp.parent / 'result.json')['rows']
                    assert len(job['rows']) == len(results)
                    for r, check in zip(job['rows'], results):
                        if 'expected' not in r: cached[digest(r)] = check
                own = read(ROOT / 'contexts' / (uid + '__phaseA.json'))['toolinput']['common_inputs_and_native_traces']
                for r in own:
                    obs = observation(r['execution'])
                    key = digest({'arguments': r['arguments'], 'observation': obs})
                    if key not in cached: continue
                    pool.append(r); checks.append(cached[key])
            summary['pool_oracle_scoring'] = 'A-stop: own saved common rows matched by arguments+observation; remainder unscored'
            summary['pool_rows_not_scored'] = len(packet['pool']['all_inputs']) - len(pool)
        if pool:
            summary['original'], pool_bugs = compare(case, pool, checks)
        else:
            pool_bugs = set()
        if gp.exists():
            gen = read(gp); observed = [r for r in gen['replays'] if r['state'] == 'observed']
            summary['generated'], bug_ids = compare(case, observed, gen['checks'])
            original_ids = {r['input_id'] for r in pool}
            accepted = set(gen['cumulative_update']['accepted_slots'])
            accepted_rows = [r for r in gen['replays'] if r['slot'] in accepted]
            accepted_ids = {r['input_id'] for r in accepted_rows}
            summary.update(novel_bug_inputs=len(bug_ids - original_ids),
                           accepted_unique_inputs=len(accepted_ids),
                           accepted_false_flag_inputs=len(accepted_ids - bug_ids),
                           novel_accepted_bug_inputs=len((accepted_ids & bug_ids) - original_ids),
                           new_task_beyond_witness_only=bool(bug_ids) and not pool_bugs,
                           final_unknown_indices=gen['support'].get('unknown_indices', []),
                           final_complete_coverage=gen['support']['complete_coverage'],
                           proposed_inputs=gen['artifact'].get('parsed'))
        rows.append(summary)
    records, threads = [], []
    for p in sorted((ROOT / 'transport/calls').glob('*/attempts.json')):
        attempt = read(p)[0]; records.append(attempt)
        if attempt['state'] == 'received':
            events = inspect_events((p.parent / 'stdout.jsonl').read_text())
            assert not events['forbidden_items'] and not attempt['denied_router_attempt']
            threads.extend(x['thread_id'] for x in events['events'] if x['type'] == 'thread.started')
            response = read(p.parent / 'response.json')
            artifact = read(ROOT / 'artifacts' / (p.parent.name + '.json'))
            assert response == artifact['response']
            assert read(p.parent / 'request.json') == read(ROOT / 'requests' / (p.parent.name + '.json'))
            assert response['text'] == (p.parent / 'last.txt').read_text()
    assert len(threads) == len(set(threads))
    raw_inventory = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'transport').rglob('*')) if p.is_file()}
    immutable(ROOT / 'raw_transport_frozen.json', raw_inventory)
    result = {'scope': 'fresh seen5 feasibility; no actual arm comparison or causal/task-gain claim',
              'status': read(ROOT / 'status.json'), 'gates': native['gates'], 'rows': rows,
              'CLI_costs': costs(ROOT / 'transport'), 'unique_received_threads': len(threads),
              'raw_origin': 'codex_cli_gpt-5.6-luna_low_host_disabled',
              'raw_inventory_sha256': sha(ROOT / 'raw_transport_frozen.json'),
              'main_workers': native['costs']['workers'],
              'CPU_preflight_workers': {'native': workers(ROOT / 'cpu_native'),
                                        'predicate': workers(ROOT / 'cpu_predicates', True)},
              'cached_input_tokens_subset': sum((x.get('usage') or {}).get('cached_input_tokens', 0) for x in records),
              'reasoning_output_tokens_subset': sum((x.get('usage') or {}).get('reasoning_output_tokens', 0) for x in records),
              'latency_seconds': [x['seconds'] for x in records],
              'old_inventory_verified': True,
              'limits': ['authored finite calibration', 'same seen fixtures, K1', 'source/support fixes bundled',
                         'no task comparison arms run', 'tool schemas exposed, host disabled',
                         'requested CLI model only, server identity unobserved', 'roles flattened',
                         'CLI sampling/token caps unmatched', 'internal HTTP retries and dollars unobserved']}
    immutable(HERE / 'results.json', result)
    print(json.dumps({'gates': result['gates'], 'CLI_costs': result['CLI_costs'],
                      'rows': [{k: v for k, v in r.items() if k in ('case', 'phaseB', 'phaseC', 'initial_support', 'final_support',
                                 'provisional_admission', 'raw_inputs', 'observed_inputs', 'accepted_witness_inputs',
                                 'novel_accepted_bug_inputs', 'new_task_beyond_witness_only')} for r in rows]}, indent=2))


if __name__ == '__main__': main()
