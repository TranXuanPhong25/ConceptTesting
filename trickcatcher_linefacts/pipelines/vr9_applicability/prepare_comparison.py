"""Export only public fields and freeze the paired experiment before inference."""
import hashlib
import json
import re
import shutil
from pathlib import Path
from .paths import HERE, REPO
from .llm_client import atomic_json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_projection(line):
    # Dataset fields are JSON strings; skipped canonical_solution is never decoded.
    return {key: json.loads(value) for key, value in re.findall(
        r'"(task_id|prompt|test|entry_point)"\s*:\s*("(?:[^"\\]|\\.)*")', line)}


def verify():
    for name, expected in json.loads((HERE/'FREEZE.json').read_text())['files'].items():
        if sha(REPO/name) != expected:
            raise ValueError('frozen_source_or_input_changed')
    parent = json.loads((HERE/'PARENT.json').read_text())
    for name, expected in parent['files'].items():
        if sha(REPO/parent['source']/name) != expected:
            raise ValueError('parent_source_changed')


def main():
    assert not (HERE/'FREEZE.json').exists(), 'preserve frozen run'
    public = {r['task_id']: r for r in map(public_projection, (REPO/'PBT_EdgeCases/run/data/humaneval.jsonl').read_text().splitlines())}
    tasks = json.loads((REPO/'python_bug_concepts/retrieval_v2/evaluation/inputs.json').read_text())
    assert len(tasks) == len({t['task_id'] for t in tasks}) == 113
    baseline_ids = {t['task'] for t in json.loads((HERE/'selection.json').read_text())['tasks'] if t['split']=='dev'}
    assert baseline_ids == {int(t['task_id'].split('/')[1]) for t in tasks}
    (HERE/'assets').mkdir()
    rows, targets = [], []
    for item in tasks:
        task_id, source = item['task_id'], item['code']
        row = public[task_id]
        assert set(row) == {'task_id','prompt','test','entry_point'} and row['entry_point'] == item['entry_point']
        n = int(task_id.split('/')[1])
        path = HERE/f'assets/PUTs/HumanEval_{n}/put0.py'
        path.parent.mkdir(parents=True)
        path.write_text(source)
        rows.append(row)
        targets.append(dict(task=n, put=source, entry=row['entry_point'], base=row['test'], split='dev', public=row))
    (HERE/'assets/public_humaneval.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    atomic_json(HERE/'assets/tasks.json', targets)
    # Grading projection stays opaque until the final stage.
    shutil.copyfile(REPO/'python_bug_concepts/research/v2_full113_20261028/grading_references.json', HERE/'assets/grading_references.json')
    files = [p for p in HERE.rglob('*') if p.is_file() and p.name not in ('README.md','CHANGELOG.md','run.log','controller.pid')
             and not any(x in ('out','__pycache__','.pytest_cache') for x in p.relative_to(HERE).parts)]
    concepts = REPO/'python_bug_concepts'
    for folder in (concepts, concepts/'retrieval_v2', concepts/'retrieval_v3'):
        files += list(folder.glob('*.py'))
    files += list((concepts/'data').glob('*')) + list((concepts/'retrieval_v2/data').glob('*'))
    files += [concepts/'retrieval_v2/evaluation/inputs.json']
    atomic_json(HERE/'FREEZE.json', dict(files={str(p.relative_to(REPO)):sha(p) for p in sorted(set(files)) if p.is_file()},
                                     tasks=113, K=1, model='qwen3.5-27b-awq', max_completion_attempts=3503))
    verify()
    print('Frozen public113 tasks; no target canonical field decoded.')


if __name__ == '__main__':
    main()
