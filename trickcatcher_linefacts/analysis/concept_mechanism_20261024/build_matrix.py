"""Normalize reviewed saved results. No runner imports or new outcome execution."""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def main():
    historical = read(HERE / 'HISTORICAL_MECHANISM_ROWS.json')
    review = read(HERE / 'V50_SEMANTIC_REVIEW.json')
    v53_path = REPO / 'trickcatcher_linefacts/out/analysis/v53_validity_smallscope/score.json'
    if not v53_path.exists():
        raise RuntimeError('finish reviewed v53 scoring before finalizing the matrix')
    v53 = read(v53_path)
    rows = []
    problem = {r['case_id']: r['problem_id'] for r in historical['v49']}
    role = {'v34': 'fault_hypothesis', 'v47': 'input_class_selection', 'v49': 'oracle_decomposition'}
    for version in ('v34', 'v47', 'v49'):
        for record in historical[version]:
            for arm, outcome in record['arms'].items():
                rows.append(dict(
                    version=version, case_id=record['case_id'], problem_id=record['problem_id'], arm=arm,
                    unit=record['unit'], concept_role=role[version],
                    semantic_binding='not independently established by task-level outcome summary',
                    obligation_realization=record['obligation_realization'],
                    evidence_parity=record.get('evidence_parity', 'see EVIDENCE_PARITY.md'),
                    selected_exposing=record.get('selected_exposing'),
                    discordance=record.get('discordance'), outcome=outcome,
                    provenance=record['provenance'],
                ))
    for record in review['records']:
        rows.append(dict(
            version='v50', case_id=record['episode'], problem_id=None,
            arm=record['stage'], unit='seen authored episode x reply stage',
            concept_role='normative_binding_and_judgment',
            semantic_binding=dict(
                required_relation_label_neutral=record['required_relation_coverage_label_neutral'],
                required_relation_strict=record['required_relation_coverage_strict_label_compatible']),
            obligation_realization='not measured: saved-observation revision, no input generation',
            evidence_parity='paired finals differ only in tool_feedback from shared observations',
            outcome={k: record[k] for k in ('review_success_strict', 'review_success_label_neutral',
                                           'judgment_enum_correct', 'manual_finding')},
            provenance=[record['artifact_path'], record['context_path']],
        ))
    for cid, task in v53['tasks'].items():
        for arm, outcome in task['arms'].items():
            rows.append(dict(
                version='v53_validity', case_id=cid, problem_id=problem[cid], arm=arm,
                unit='dev PUT x validity filter arm', concept_role='input_validity',
                semantic_binding='runtime comparison to evaluator contract on fixed universe; not a proof',
                obligation_realization='not measured: input filtering, not new input generation',
                evidence_parity='same spec/public tests; tool arm numeric-only; lines controls taxonomy',
                universe={k: task[k] for k in ('inputs', 'invalid', 'valid', 'exposing')},
                outcome=outcome, provenance=[str(v53_path.relative_to(REPO)),
                    'trickcatcher_linefacts/analysis/v53_validity_smallscope/PREREG.md'],
            ))
    target = HERE / 'MECHANISM_MATRIX.jsonl'
    with target.open('x') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    print(json.dumps(dict(rows=len(rows), by_version={v: sum(r['version'] == v for r in rows)
                     for v in sorted({r['version'] for r in rows})},
                     sha256=hashlib.sha256(target.read_bytes()).hexdigest()), indent=2))


if __name__ == '__main__':
    main()
