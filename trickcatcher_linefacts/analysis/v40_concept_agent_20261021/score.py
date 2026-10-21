"""Post-freeze saved-observation scoring only. No model/PUT/reference worker calls."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v40_concept_agent import d1, fixture_oracles
from trickcatcher_linefacts.pipelines.v40_concept_agent.flow_common import digest


def literal_id(task, literal):
    args = d1.flow_tools.parse_call(literal, task['arity'])
    return digest(d1.typed_value(args))


def assess(case, observation):
    if observation.get('native_checked') is not True or observation.get('domain_filter') != 'accepted':
        return 'unknown'
    gold = fixture_oracles.expected(case, observation['input'])
    if gold is None:
        return 'undefined_oracle'
    status = observation.get('execution_status')
    if status == 'ok' and observation.get('output_capture') == 'literal':
        actual = ('ok', d1.typed_value(d1.parse_literal(observation['output'], output=True)))
    elif status == 'exception':
        actual = ('exception', observation.get('exception_type'))
    else:
        return 'unknown'
    return 'exposes' if actual != gold else 'matches'


def workers(root):
    attempts = [d1.read(p) for p in root.rglob('attempt.json')]
    results = [d1.read(p) for p in root.rglob('result.json')]
    return {'reserved': len(attempts), 'recorded_launches': sum(x.get('launched') is True for x in attempts),
            'unknown_reservations': sum(x.get('launched') is None for x in attempts),
            'failed': sum(x.get('state') == 'failed' for x in attempts),
            'reported_PUT_calls': sum(x['put_calls'] for x in results) if results and all('put_calls' in x for x in results) else None,
            'recorded_validity_checks': sum(x.get('validity_checks', 0) for x in results),
            'inferred_single_entry_calls': sum(x.get('status') in ('ok', 'exception') for x in results),
            'entry_call_scope': 'inferred from one-entry-call worker source and completed status; no explicit PUT counter'}


def main():
    root = d1.ROOT
    d1.verify(root)
    complete = (root / 'generation_frozen.json').exists()
    cases = {x['fixture_id']: x for x in d1.pilot_fixtures.cases()}
    prepared = [d1.read(p) for p in sorted((root / 'prepared').glob('*.json'))]
    all_shared_literals = set()
    for row in prepared:
        all_shared_literals.update(literal_id(row['task'], x) for x in row['shared_inputs'])
    rows, slot_counts = [], Counter()
    for row in prepared:
        shared = {literal_id(row['task'], x) for x in row['shared_inputs']}
        case = cases[row['fixture']]
        shared_assessment = [assess(case, x) for x in row['public']['initial_observations'] + [row['injection']]]
        for arm in d1.ARMS:
            summary = {'episode': row['episode'], 'fixture': row['fixture'], 'arm': arm,
                       'shared_assessment': shared_assessment, 'turns': [], 'query_proposals': 0,
                       'native_rows': 0, 'unknown_rows': 0, 'undefined_rows': 0}
            exposures, observed, final_exposures = set(), set(), set()
            for turn in (1, 2, 3):
                slot = row['episode'] + '__' + arm + '__' + str(turn)
                path = root / 'events' / (slot + '.json')
                if not path.exists():
                    ledger = root / 'transport/calls' / slot / 'attempt.json'
                    failure = d1.read(ledger) if ledger.exists() else None
                    if failure is not None:
                        state = 'transport_failed_no_artifact' if failure['state'] != 'received' else 'received_not_processed'
                    else:
                        state = 'not_attempted' if not (root / 'artifacts' / (slot + '.json')).exists() else 'incomplete_execution'
                    summary['turns'].append({'turn': turn, 'state': state,
                                             'transport_failure': failure}); slot_counts[state] += 1
                    continue
                event = d1.read(path); slot_counts[event['reply_state']] += 1
                summary['turns'].append({'turn': turn, 'state': event['reply_state'],
                                         'error': event.get('reply_error'), 'claims': event['reply'].get('claims', [])})
                summary['query_proposals'] += len(event['reply'].get('queries', []))
                for feedback in event['feedback']:
                    if 'input' not in feedback: continue
                    judgement = assess(case, feedback)
                    summary['native_rows'] += feedback.get('native_checked') is True
                    summary['unknown_rows'] += judgement == 'unknown'
                    summary['undefined_rows'] += judgement == 'undefined_oracle'
                    key = literal_id(row['task'], feedback['input'])
                    observed.add(key)
                    if judgement == 'exposes':
                        exposures.add(key)
                        if turn == 3: final_exposures.add(key)
            attempted = any(x['state'] in ('valid', 'failed') for x in summary['turns'])
            summary.update(any_generated_exposure=bool(exposures) if attempted else None,
                           final_exposure=bool(final_exposures) if attempted else None,
                           unique_observed_inputs=len(observed), unique_exposing_inputs=len(exposures),
                           new_input_ids_outside_entire_task_shared_pool=len(observed - shared),
                           exposing_ids_outside_task_shared_pool=len(exposures - shared),
                           exposing_ids_outside_global_shared_literal_pool=len(exposures - all_shared_literals),
                           within_episode_discovery=bool(exposures) and 'exposes' not in shared_assessment if attempted else None)
            rows.append(summary)
    attempts = [d1.read(p) for p in (root / 'transport/calls').glob('*/attempt.json')]
    costs = {'task_attempts': len(attempts), 'received': sum(x['state'] == 'received' for x in attempts),
             'known_usage_attempts': sum(x.get('usage_known') is True for x in attempts),
             'unknown_usage_attempts': sum(x.get('usage_known') is not True for x in attempts),
             'input_tokens_known': sum(x.get('input_tokens') or 0 for x in attempts),
             'output_tokens_known': sum(x.get('output_tokens') or 0 for x in attempts),
             'metadata_requests': len((root / 'transport/metadata.jsonl').read_text().splitlines()) if (root / 'transport/metadata.jsonl').exists() else 0,
             'prelaunch_metadata_requests': 1 if (root / 'metadata_prelaunch.json').exists() else 0}
    result = {'scope': 'seen8 authored supplied-concept diagnostic; all24episode-arm/72slots retained',
              'generation_complete': complete, 'status': d1.read(root / 'status.json') if (root / 'status.json').exists() else None,
              'slots': dict(slot_counts), 'rows': rows, 'costs': costs,
              'shared_CPU_workers': workers(root / 'shared'), 'model_requested_workers': workers(root / 'native'),
              'semantic_review': 'not available: no received model output' if not costs['received'] else 'independent review required',
              'historical_novelty': 'not assessed; no new real-task/benchmark or model-authored assertion claim',
              'mechanism_gate': 'not measured' if not costs['received'] else 'pending independent semantic review',
              'novelty_definition': 'task-scoped input pairs subtract all shared rows; separate stricter global literal metric; never arm-local',
              'source_snapshot_sha256': hashlib.sha256((root / 'preparation.json').read_bytes()).hexdigest()}
    terminal = (root / 'status.json').exists() and d1.read(root / 'status.json').get('state') == 'stopped'
    output = HERE / ('results.json' if complete else 'incomplete_status.json' if terminal else 'prepared_status.json')
    d1.write_json(output, result)
    print(json.dumps({'output': str(output.relative_to(REPO)), 'complete': complete, 'slots': dict(slot_counts), 'costs': costs}, indent=2))


if __name__ == '__main__': main()
