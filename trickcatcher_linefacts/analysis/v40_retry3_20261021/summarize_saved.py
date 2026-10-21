"""Post-freeze metrics from saved JSON only; no model or PUT execution."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v40_concept_agent import d1

spec = importlib.util.spec_from_file_location(
    'original_saved_scorer', HERE.parent / 'v40_concept_agent_20261021/score.py')
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)


def main():
    root = d1.ROOT.with_name('d1_retry3_20261021')
    d1.verify(root)
    assert (root / 'generation_frozen.json').exists()
    cases = {x['fixture_id']: x for x in d1.pilot_fixtures.cases()}
    prepared = [d1.read(p) for p in sorted((root / 'prepared').glob('*.json'))]
    global_shared = {scorer.literal_id(row['task'], x)
                     for row in prepared for x in row['shared_inputs']}
    rows = []
    for row in prepared:
        shared = {scorer.literal_id(row['task'], x) for x in row['shared_inputs']}
        for arm in d1.ARMS:
            counts, errors = Counter(), Counter()
            records = []
            for turn in (1, 2, 3):
                slot = f"{row['episode']}__{arm}__{turn}"
                artifact = d1.read(root / 'artifacts' / (slot + '.json'))
                event = d1.read(root / 'events' / (slot + '.json'))
                raw = d1.strict_json(artifact['raw']['text'])
                counts['received_completions'] += 1
                counts['valid_turns'] += artifact['state'] == 'valid'
                for field in ('queries', 'later_queries', 'final_inputs'):
                    counts['raw_' + field] += len(raw.get(field, []))
                if artifact['state'] != 'valid':
                    errors[artifact['error']] += 1
                for observation in event['feedback']:
                    phase = 'final' if turn == 3 else 'query'
                    counts[phase + '_feedback'] += 1
                    counts[phase + '_' + observation['status']] += 1
                    if phase == 'query':
                        counts['actual_' + observation.get('tool', 'refused_action')] += 1
                    if observation.get('error'):
                        errors[observation['error']] += 1
                    if 'input' not in observation:
                        continue
                    key = scorer.literal_id(row['task'], observation['input'])
                    assessment = scorer.assess(cases[row['fixture']], observation)
                    counts[phase + '_native_rows'] += observation.get('native_checked') is True
                    counts[phase + '_' + assessment] += 1
                    records.append({'turn': turn, 'phase': phase, 'input': observation['input'],
                                    'input_id': key, 'assessment': assessment,
                                    'outside_task_shared': key not in shared,
                                    'outside_global_shared_literal_pool': key not in global_shared})
            unique = {x['input_id'] for x in records}
            exposing = {x['input_id'] for x in records if x['assessment'] == 'exposes'}
            final = [x for x in records if x['phase'] == 'final']
            rows.append({'episode': row['episode'], 'fixture': row['fixture'], 'arm': arm,
                         'counts': dict(counts), 'errors': dict(errors),
                         'unique_inputs': len(unique), 'unique_exposing_inputs': len(exposing),
                         'novel_task_shared_inputs': len(unique - shared),
                         'novel_task_shared_exposing_inputs': len(exposing - shared),
                         'novel_global_shared_literal_exposing_inputs': len(exposing - global_shared),
                         'any_exposure': bool(exposing),
                         'final_exposure': any(x['assessment'] == 'exposes' for x in final),
                         'final_novel_task_shared_exposure': any(
                             x['assessment'] == 'exposes' and x['outside_task_shared'] for x in final),
                         'records': records})
    arms = {}
    for arm in d1.ARMS:
        selected = [x for x in rows if x['arm'] == arm]
        counts, errors = Counter(), Counter()
        for row in selected:
            counts.update(row['counts']); errors.update(row['errors'])
        arms[arm] = {'counts': dict(counts), 'errors': dict(errors),
                     'exposing_tasks': [x['episode'] for x in selected if x['any_exposure']],
                     'final_exposing_tasks': [x['episode'] for x in selected if x['final_exposure']],
                     'final_novel_task_shared_exposing_tasks': [
                         x['episode'] for x in selected if x['final_novel_task_shared_exposure']],
                     'unique_task_input_pairs': sum(x['unique_inputs'] for x in selected),
                     'unique_exposing_task_input_pairs': sum(x['unique_exposing_inputs'] for x in selected),
                     'novel_task_shared_pairs': sum(x['novel_task_shared_inputs'] for x in selected),
                     'novel_task_shared_exposing_pairs': sum(x['novel_task_shared_exposing_inputs'] for x in selected),
                     'novel_global_shared_literal_exposing_pairs': sum(
                         x['novel_global_shared_literal_exposing_inputs'] for x in selected)}
    result = {'scope': 'saved v40 data only; novelty relative to ENTIRE v40 prepared shared pool, not historical24+base/benchmark novelty',
              'rows': rows, 'arms': arms,
              'assertions': 'not generated or scored; fixture expected values computed only post-freeze',
              'semantic_claim_correctness': 'manual independent review; input exposure is not claim correctness'}
    d1.write_json(HERE / 'input_metrics.json', result)
    print(json.dumps(arms, indent=2))


if __name__ == '__main__':
    main()
