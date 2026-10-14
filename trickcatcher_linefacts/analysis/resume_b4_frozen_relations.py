"""Resume B4 with exact frozen relation and cached hypothesis evidence.

Operational adapter only: protected pipeline source, prompts, seeds, and samples
stay unchanged. Fail on changed sources, task snapshots, or hypothesis caches.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v13_hyp import hypotheses, run, v4_runtime

GEN = REPO / 'trickcatcher_linefacts/pipelines/v13_hyp/out/humaneval/generation'
saved = json.loads((GEN / 'tasks.json').read_text())['tasks']
frozen = {t['task']: t for t in saved}
manifest = json.loads((GEN / 'manifest.json').read_text())
if manifest['sources'] != v4_runtime.source_hashes():
    raise RuntimeError('B4 protected source differs from frozen manifest')
original = v4_runtime.isolated


def isolated(mode, job, directory, python=None, timeout=900):
    if mode == 'relations':
        task = job['task']
        record = frozen[task['task']]
        if task != {k: v for k, v in record.items()
                    if k not in ('relation_meta', 'hypothesis_meta')}:
            raise RuntimeError('B4 task differs from frozen relation snapshot')
        return copy.deepcopy(record['relation_meta'])
    return original(mode, job, directory, python, timeout)


def verify():
    incoming = json.loads((GEN.parent / 'tasks_hybrid.json').read_text())['tasks']
    if len(incoming) != len(saved) or {t['task'] for t in incoming} != set(frozen):
        raise RuntimeError('B4 task cohort changed')
    for task in incoming:
        record = frozen[task['task']]
        relation = isolated('relations', {'task': task}, None)
        proposal_task = dict(task, relation_meta=relation)
        cached = json.loads((GEN / 'hypotheses' / str(task['task']) / 'summary.json').read_text())
        if cached['cache_key'] != hypotheses.cache_key(proposal_task, manifest['model']):
            raise RuntimeError('B4 hypothesis cache key changed')
        if hypotheses.slim(cached) != record['hypothesis_meta']:
            raise RuntimeError('B4 cached hypothesis differs from frozen evidence')
    return dict(
        scope='B4 exact frozen relation replay and hypothesis-cache verification',
        tasks=len(saved), protected_sources_verified=True,
        prompts_or_config_changed=False,
        task_snapshot_sha256=hashlib.sha256((GEN / 'tasks.json').read_bytes()).hexdigest(),
        generation_manifest_sha256=hashlib.sha256((GEN / 'manifest.json').read_bytes()).hexdigest(),
        resume_adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )


if __name__ == '__main__':
    provenance = verify()
    (Path(__file__).parent / 'b4_resume_relation_replay.json').write_text(
        json.dumps(provenance, indent=2) + '\n')
    if sys.argv[1:] == ['--verify-only']:
        print('Verified exact frozen B4 relation and hypothesis evidence:', len(saved), 'tasks')
    else:
        v4_runtime.isolated = isolated
        sys.argv = [sys.argv[0], 'arms'] + sys.argv[1:]
        run.main()
