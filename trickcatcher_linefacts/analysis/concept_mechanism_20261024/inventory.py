"""Bounded, read-only run inventory. Does not import runners or execute answers."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
V50 = REPO / 'trickcatcher_linefacts/out/pipelines/v50_binding_revision/humaneval/revision8'
V53 = REPO / 'trickcatcher_linefacts/out/analysis/v53_validity_smallscope'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def tree(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and p.suffix != '.pyc'
            and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}


def compare(expected, actual):
    return dict(expected_count=len(expected), actual_count=len(actual),
                missing=sorted(set(expected) - set(actual)),
                extra=sorted(set(actual) - set(expected)),
                changed=sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k]),
                matches=expected == actual)


def v50():
    frozen = read(V50 / 'freeze.json')
    generation = read(V50 / 'generation_frozen.json')
    sources = tree(REPO / 'trickcatcher_linefacts/pipelines/v50_binding_revision')
    status = read(V50 / 'status.json')
    slots = read(V50 / 'slots.json')
    expected_slots = set(frozen['slots'])
    actual_slots = {p.stem for p in (V50 / 'artifacts').glob('*.json')}
    return dict(
        path=str(V50.relative_to(REPO)),
        state={k: status[k] for k in ('state', 'started_utc', 'ended_utc', 'pid') if k in status},
        freeze_sha256=sha(V50 / 'freeze.json'),
        generation_frozen_sha256=sha(V50 / 'generation_frozen.json'),
        sources=compare(frozen['sources'], sources),
        prepared=compare(frozen['prepared'], tree(V50 / 'prepared')),
        rubric_matches=frozen['evaluation_sha256'] == sha(
            REPO / 'trickcatcher_linefacts/analysis/v50_binding_revision_20261023/EVALUATION.md'),
        preparation_approval_matches=frozen['preparation_approval_sha256'] == sha(V50 / 'preparation_approval.json'),
        generation={name: compare(expected, tree(V50 / name)) for name, expected in generation.items()},
        slots=dict(expected=len(expected_slots), artifacts=len(actual_slots),
                   missing=sorted(expected_slots - actual_slots), extra=sorted(actual_slots - expected_slots),
                   status_records=slots),
    )


def v53():
    problems = read(V53 / 'problems.json')
    expected = {f'{pid}_{arm}.txt' for pid in problems for arm in ('concept', 'lines', 'open')}
    actual = {p.name for p in (V53 / 'answers').glob('*.txt')}
    prompts = {p.name for p in (V53 / 'prompts').glob('*.txt')}
    return dict(
        path=str(V53.relative_to(REPO)), problems=len(problems),
        put_tasks=sum(len(cids) for cids in problems.values()),
        expected_answers=len(expected), answers=len(actual), prompts=len(prompts),
        missing_answers=sorted(expected - actual), extra_answers=sorted(actual - expected),
        missing_prompts=sorted(expected - prompts), extra_prompts=sorted(prompts - expected),
        root_files=sorted(p.name for p in V53.iterdir() if p.is_file()),
        problems_sha256=sha(V53 / 'problems.json'),
        prompt_sha256=tree(V53 / 'prompts'), answer_sha256=tree(V53 / 'answers'),
        scorer_sha256=sha(REPO / 'trickcatcher_linefacts/analysis/v53_validity_smallscope/validity.py'),
        prereg_sha256=sha(REPO / 'trickcatcher_linefacts/analysis/v53_validity_smallscope/PREREG.md'),
        answer_semantics='not evaluated by this inventory',
        transcript_compliance='not evaluated by this inventory',
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), v50=v50(), v53=v53())
    # Refuse to replace an earlier snapshot; no run-owned paths are modified.
    with args.out.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(
        v50_state=result['v50']['state']['state'],
        v50_sources=result['v50']['sources']['matches'],
        v50_generation=all(v['matches'] for v in result['v50']['generation'].values()),
        v50_slots=result['v50']['slots']['artifacts'],
        v53_answers=result['v53']['answers'],
        v53_expected=result['v53']['expected_answers'],
        snapshot=str(args.out),
    ), indent=2))


if __name__ == '__main__':
    main()
