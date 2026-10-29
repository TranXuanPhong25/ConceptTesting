"""Join exact-source prior judgments and one prospectively blinded judgment."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'run01'
PRIOR = HERE.parent.parent / 'retrieval_v11/evaluation_development/run01'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(row):
    return [row['code'], row['concept']['id'], row['source_sites']]


def main():
    queue = {r['review_id']: r for r in read(OUT / 'NEW_SEMANTIC_REVIEW.json')}
    old_queue = {r['review_id']: r for r in read(PRIOR / 'NEW_SEMANTIC_REVIEW.json')}
    old_grades = {r['review_id']: r for r in read(PRIOR / 'GRADES_NEW.json')}
    prior_receipt = read(PRIOR / 'GRADES_NEW_FREEZE.json') if (PRIOR / 'GRADES_NEW_FREEZE.json').exists() else None
    # The prior file was frozen before its original unblinding; pin its published bytes.
    assert sha(PRIOR / 'GRADES_NEW.json') == 'aad48d76bcd394e2a5b489e01baab02e6d43a199a3d0b345136883e98499911a'
    reused = read(OUT / 'REUSED_VR11_GRADES.json')
    for row in reused:
        previous = row['prior_review_id']
        assert binding(queue[row['review_id']]) == binding(old_queue[previous])
        assert {k: v for k, v in row.items() if k != 'prior_review_id'} == {
            **old_grades[previous], 'review_id': row['review_id']}
    receipt = read(OUT / 'GRADES_FRESH_FREEZE.json')
    assert receipt['grades_sha256'] == sha(OUT / 'GRADES_FRESH.json')
    assert receipt['queue_sha256'] == sha(OUT / 'REVIEW_FRESH.json')
    fresh_queue = read(OUT / 'REVIEW_FRESH.json')
    assert len(fresh_queue) == 1
    assert receipt['source_sha256'] == hashlib.sha256(fresh_queue[0]['code'].encode()).hexdigest()
    assert fresh_queue[0] == queue[fresh_queue[0]['review_id']]
    fresh = read(OUT / 'GRADES_FRESH.json')
    assert len(reused) == 24 and len(fresh) == 1
    combined = sorted(reused + fresh, key=lambda x: x['review_id'])
    assert len({r['review_id'] for r in combined}) == len(queue) == 25
    assert {r['review_id'] for r in combined} == set(queue)
    for row in combined:
        assert row['status'] in {'supported_fault', 'contradicted', 'unknown_or_conditional'}
        assert all(q in queue[row['review_id']]['code'] for q in row['source_quotes'])
    with (OUT / 'GRADES_NEW.json').open('x') as handle:
        json.dump(combined, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    paths = [OUT / n for n in ('NEW_SEMANTIC_REVIEW.json', 'REUSED_VR11_GRADES.json',
             'REVIEW_FRESH.json', 'GRADES_FRESH.json', 'GRADES_FRESH_FREEZE.json', 'GRADES_NEW.json')]
    paths += [PRIOR / 'NEW_SEMANTIC_REVIEW.json', PRIOR / 'GRADES_NEW.json', Path(__file__)]
    with (OUT / 'GRADE_JOIN_FREEZE.json').open('x') as handle:
        json.dump({'status': 'exact_source_binding_join_PASS', 'reused': 24, 'fresh': 1,
                   'files': {str(p.relative_to(HERE.parent.parent.parent)): sha(p) for p in paths},
                   'limitation': 'Exposed development sources; method-blinded agent judgments, not independent efficacy.'},
                  handle, indent=2)
        handle.write('\n')
    print('PASS: 24 exact-source reused judgments + 1 fresh blinded judgment; 25/25 covered')


if __name__ == '__main__':
    main()
