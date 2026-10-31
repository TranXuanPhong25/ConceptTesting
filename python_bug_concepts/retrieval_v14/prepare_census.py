"""Copy only public PUT/entry/task from all 113 frozen V85 prepared records."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PARENT = REPO / 'trickcatcher_linefacts/handoffs/v85_20261029_resume2/work/snapshot/trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/handoff_resume2_20261029'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    outputs = [HERE / 'census_inputs.json', HERE / 'CENSUS_PROVENANCE.json']
    if any(p.exists() for p in outputs):
        raise ValueError('preserve existing census inputs')
    manifest = PARENT / 'GENERATION_FREEZE.json'
    frozen = json.loads(manifest.read_text())['files']
    paths = sorted((PARENT / 'prepared').glob('*.json'), key=lambda p: int(p.stem))
    if len(paths) != 113:
        raise ValueError('expected complete 113-task cohort')
    rows, receipts = [], []
    for path in paths:
        digest = sha(path)
        if frozen.get(str(path.relative_to(PARENT))) != digest:
            raise ValueError('parent prepared hash mismatch: ' + path.name)
        record = json.loads(path.read_text())['retrieval']
        if str(record['task']) != path.stem:
            raise ValueError('task/file mismatch')
        rows.append(dict(id=str(record['task']), entry=record['entry'], source=record['put']))
        receipts.append(dict(path=str(path.relative_to(REPO)), sha256=digest))
    provenance = dict(parent_freeze=str(manifest.relative_to(REPO)), parent_freeze_sha256=sha(manifest),
                      fields=['retrieval.task', 'retrieval.entry', 'retrieval.put'], files=receipts)
    for path, data in zip(outputs, [rows, provenance]):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print('Prepared 113 public source records; all parent hashes verified.')


if __name__ == '__main__':
    main()
