"""Verify existing saved data; never import pipeline code or execute a PUT/model.

Manual semantic judgments remain in the follow-through report. This script checks
integrity, denominators and pre-existing exposure labels, not semantic correctness.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN = REPO / 'trickcatcher_linefacts/out/pipelines/v40_concept_agent/humaneval/d1_retry3_20261021'
ANALYSIS = REPO / 'trickcatcher_linefacts/analysis/v40_retry3_20261021'
ARMS = ('concept_adaptive', 'generic_adaptive', 'concept_committed')
DISCOVERY = {'E1', 'E2', 'E4', 'E5'}


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    status = read(RUN / 'status.json')
    assert status['state'] == 'complete', status['state']
    frozen = read(RUN / 'generation_frozen.json')
    bad = [name for name, expected in frozen.items()
           if digest(RUN / name) != expected]
    assert not bad, bad
    results = read(ANALYSIS / 'results.json')
    rows = results['rows']
    assert len(rows) == 24
    assert {(r['episode'], r['arm']) for r in rows} == {
        (f'E{n}', arm) for n in range(1, 9) for arm in ARMS}
    saved_metrics = read(ANALYSIS / 'input_metrics.json')
    assert len(saved_metrics['rows']) == 24
    metric_rows = {(r['episode'], r['arm']): r for r in saved_metrics['rows']}
    validity = Counter()
    evidence_files = {}
    for row in rows:
        assert [t['turn'] for t in row['turns']] == [1, 2, 3]
        for turn in (1, 2, 3):
            slot = f"{row['episode']}__{row['arm']}__{turn}"
            path = RUN / 'artifacts' / f'{slot}.json'
            artifact = read(path)
            validity[(row['arm'], artifact['state'])] += 1
            evidence_files[str(path.relative_to(REPO))] = digest(path)
        assert row['any_generated_exposure'] == metric_rows[
            (row['episode'], row['arm'])]['any_exposure']
    summary = {}
    for arm in ARMS:
        selected = [r for r in rows if r['arm'] == arm]
        discovered = sorted(r['episode'] for r in selected
                            if r['episode'] in DISCOVERY
                            and r['within_episode_discovery'])
        summary[arm] = {
            'valid_turns': validity[(arm, 'valid')],
            'failed_turns': validity[(arm, 'failed')],
            'valid_final_turns': sum(r['turns'][-1]['state'] == 'valid' for r in selected),
            'no_supplied_witness_discovery_episodes': discovered,
            'any_exposure_episodes': sorted(r['episode'] for r in selected
                                           if r['any_generated_exposure']),
        }
    ca = set(summary['concept_adaptive']['no_supplied_witness_discovery_episodes'])
    ga = set(summary['generic_adaptive']['no_supplied_witness_discovery_episodes'])
    claims = {}
    for episode, observation_turn in [('E2', 2), ('E4', 1), ('E6', 2)]:
        final_path = RUN / 'artifacts' / f'{episode}__concept_adaptive__3.json'
        event_path = RUN / 'events' / f'{episode}__concept_adaptive__{observation_turn}.json'
        final = json.loads(read(final_path)['raw']['text'])
        event = read(event_path)
        claims[episode] = {
            'final_claims': final['claims'],
            'prior_native_observations': [
                {k: o.get(k) for k in ('observation_id', 'input', 'execution_status',
                                     'exception_type', 'output', 'native_checked')}
                for o in event['feedback'] if o.get('native_checked')],
            'final_artifact_sha256': digest(final_path),
            'observation_event_sha256': digest(event_path),
            'interpretation': 'manual semantic assessment in follow-through report',
        }
    dependencies = [ANALYSIS / n for n in
                    ('results.json', 'input_metrics.json', 'SEMANTIC_A.md',
                     'SEMANTIC_B.md', 'INTEGRITY_COST_AUDIT.md')]
    dependencies += [RUN / 'generation_frozen.json', RUN / 'status.json',
                     REPO / 'trickcatcher_linefacts/pipelines/v40_concept_agent/d1_protocol.json',
                     REPO / 'trickcatcher_linefacts/analysis/v41_iorel/RESULTS.md']
    report = {
        'scope': 'post-hoc saved-data verification; no new scoring, PUT, model or network calls',
        'generation_manifest_files_verified': len(frozen),
        'all_24_rows_present': True,
        'all_72_artifacts_present': sum(validity.values()) == 72,
        'arms': summary,
        'concept_only_discovery_episodes': sorted(ca - ga),
        'generic_only_discovery_episodes': sorted(ga - ca),
        'claim_observation_examples': claims,
        'dependency_sha256': {str(p.relative_to(REPO)): digest(p) for p in dependencies},
        'artifact_sha256': evidence_files,
        'semantic_gate': 'manual; JSON/schema and exposure labels do not establish correctness',
        'new_model_calls': 0,
        'new_native_calls': 0,
    }
    destination = OUT / 'CONCEPT_FOLLOWTHROUGH_20261021.evidence.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in
                      ('generation_manifest_files_verified', 'all_24_rows_present',
                       'all_72_artifacts_present', 'arms', 'concept_only_discovery_episodes',
                       'generic_only_discovery_episodes')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
