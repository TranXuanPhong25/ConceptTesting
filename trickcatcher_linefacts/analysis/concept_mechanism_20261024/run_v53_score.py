"""Run the original reviewed v53 scorer with a reference guard and audit journal.

No model calls. Scorer semantics, answers, caps, exclusions and registered gates are
unchanged. Unknown reference results stop scoring instead of becoming invalid data.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = REPO / 'trickcatcher_linefacts/out/analysis/concept_mechanism_20261024'


def now():
    return datetime.now(timezone.utc).isoformat()


def write_status(value):
    path = WORK / 'v53_score_status.json'
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def main():
    from trickcatcher_linefacts.analysis.v53_validity_smallscope import validity as v

    snapshot = json.loads((HERE / 'ARTIFACT_INVENTORY.json').read_text())['v53']
    protocol_inventory = json.loads((HERE / 'V53_PROTOCOL_INVENTORY.json').read_text())
    check = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

    def verify_inputs():
        for name, expected in protocol_inventory['source_sha256'].items():
            if check(REPO / name) != expected:
                raise RuntimeError(f'reviewed source changed: {name}')
        if check(v.OUT / 'problems.json') != snapshot['problems_sha256']:
            raise RuntimeError('problem mapping changed since inventory')
        if check(Path(v.__file__).with_name('PREREG.md')) != snapshot['prereg_sha256']:
            raise RuntimeError('PREREG changed since inventory')
        # Both exclusion files were absent in the reviewed snapshot. Never silently
        # accept a new exclusion or change the paired evaluation denominator.
        if (v.OUT / 'excluded_problems.json').exists() or (v.P.OUT / 'excluded.json').exists():
            raise RuntimeError('exclusion policy input appeared after review')
        for folder, key in [('prompts', 'prompt_sha256'), ('answers', 'answer_sha256')]:
            paths = {str(p.relative_to(v.OUT / folder)): check(p)
                     for p in (v.OUT / folder).rglob('*') if p.is_file()}
            if paths != snapshot[key]:
                raise RuntimeError(f'{folder} changed since inventory')

    verify_inputs()
    if (v.OUT / 'score.json').exists():
        raise RuntimeError('score already exists; inspect it rather than duplicate scoring')
    if not (HERE / 'V53_SCORING_REVIEW.md').is_file():
        raise RuntimeError('independent review missing')

    WORK.mkdir(parents=True, exist_ok=True)
    if (WORK / 'v53_score_status.json').exists():
        raise RuntimeError('audit run already has a status; inspect before any restart')
    state = dict(state='running', pid=os.getpid(), started_utc=now(),
                 original_scorer_sha256=check(Path(v.__file__)),
                 reference_checks=[], completed_case_arms=[])
    write_status(state)
    original_truth = v.E.reference_truth
    original_checks = v.run_checks

    def guarded_truth(inv, case, record, official, diag):
        truth = original_truth(inv, case, record, official, diag)
        unresolved = [lit for lit, row in truth.items()
                      if row.get('reference_skipped') or (row['valid'] and row['ref'] is None)]
        state['reference_checks'].append(dict(case_id=case['case_id'], inputs=len(truth),
                                               unresolved=len(unresolved)))
        write_status(state)
        if unresolved:
            raise RuntimeError(f'unresolved reference results for case {case["case_id"]}; withhold verdict')
        return truth

    def logged_checks(case, rec, arm, code, found, inputs):
        result = original_checks(case, rec, arm, code, found, inputs)
        state['completed_case_arms'].append(dict(case_id=case['case_id'], arm=arm,
                                                 checks=len(found), kept=result[1], inputs=len(inputs)))
        write_status(state)
        print(json.dumps(state['completed_case_arms'][-1]), flush=True)
        return result

    v.E.reference_truth = guarded_truth
    v.run_checks = logged_checks
    try:
        code = v.score()
        verify_inputs()
        state.update(state='complete' if code == 0 else 'incomplete', returncode=code, ended_utc=now())
        if (v.OUT / 'score.json').exists():
            state['score_sha256'] = check(v.OUT / 'score.json')
        write_status(state)
        return code
    except BaseException as exc:
        state.update(state='failed', scientific_verdict='withheld', error_type=type(exc).__name__,
                     error=str(exc), ended_utc=now())
        write_status(state)
        raise
    finally:
        v.E.reference_truth = original_truth
        v.run_checks = original_checks


if __name__ == '__main__':
    raise SystemExit(main())
