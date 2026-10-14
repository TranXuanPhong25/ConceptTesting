"""Resume B3 with its exact archived relation metadata; do not retrace completed frozen facts.

The original runner/model prompts and protected source files remain unchanged. An exact task/source check guards
the replay; run provenance is recorded in b3_resume_relation_replay.json. This is an operational resume adapter.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from trickcatcher_linefacts.pipelines.v12_rel import run, v4_runtime

GEN=REPO/'trickcatcher_linefacts/pipelines/v12_rel/out/humaneval/generation'
saved=json.loads((GEN/'tasks.json').read_text())['tasks']
frozen={t['task']:t for t in saved}
manifest=json.loads((GEN/'manifest.json').read_text())
if manifest['sources']!=v4_runtime.source_hashes():
    raise RuntimeError('B3 protected source differs from frozen manifest')
original=v4_runtime.isolated


def isolated(mode,job,directory,python=None,timeout=900):
    if mode=='relations':
        task=job['task'];record=frozen[task['task']]
        if task!={k:v for k,v in record.items() if k!='relation_meta'}:
            raise RuntimeError('B3 task differs from frozen relation snapshot')
        return copy.deepcopy(record['relation_meta'])
    return original(mode,job,directory,python,timeout)


if __name__=='__main__':
    provenance=dict(scope='B3 exact frozen relation replay during resume',tasks=len(saved),
        task_snapshot_sha256=hashlib.sha256((GEN/'tasks.json').read_bytes()).hexdigest(),
        generation_manifest_sha256=hashlib.sha256((GEN/'manifest.json').read_bytes()).hexdigest(),
        resume_adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        protected_sources_verified=True,prompts_or_config_changed=False)
    (Path(__file__).parent/'b3_resume_relation_replay.json').write_text(json.dumps(provenance,indent=2)+'\n')
    v4_runtime.isolated=isolated
    sys.argv=[sys.argv[0],'arms']+sys.argv[1:]
    run.main()
