"""Copy the frozen v31 records into the v34 run root so that only template-placebo is generated.

Copies, per case: tool.json and tool/ (the same concepts and inputs) and arms/<arm>/result.json for the reused arms.
Each copied result.json must match the v31 generation_frozen.json hash. Tool ledgers are not copied (their context
hashes the pipeline code); arms with result.json never open a session. Writes seed_manifest.json (immutable).
  PYTHONPATH=. $V4_PYTHON -m trickcatcher_linefacts.pipelines.v34_ftplacebo.seed_from_v31 --cohort vibepass_half
"""
import argparse
import hashlib
import json
import shutil

from .flow_common import immutable
from .paths import CONFIG, REPO
from .ft_run import FTRun

V31 = REPO / 'trickcatcher_linefacts/out/pipelines/v31_faulttemplate/humaneval/faulttemplate/openrouter'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cohort', default='vibepass_half')
    name = ap.parse_args().cohort
    run = FTRun(name)
    src = V31 / name
    frozen = json.loads((src / 'generation_frozen.json').read_text())
    copied = {}
    for case in run.cases:
        cid = case['case_id']
        a, b = src / 'cases' / cid, run.root / 'cases' / cid
        b.mkdir(parents=True, exist_ok=True)
        if not (b / 'tool.json').exists():
            shutil.copy2(a / 'tool.json', b / 'tool.json')
            shutil.copytree(a / 'tool', b / 'tool', dirs_exist_ok=True)
        copied[f'cases/{cid}/tool.json'] = hashlib.sha256((b / 'tool.json').read_bytes()).hexdigest()
        for arm in CONFIG['faulttemplate']['reused_from_v31']:
            rel = f'cases/{cid}/arms/{arm}/result.json'
            if hashlib.sha256((src / rel).read_bytes()).hexdigest() != frozen[rel]:
                raise SystemExit('v31 frozen record changed: ' + rel)
            (run.root / rel).parent.mkdir(parents=True, exist_ok=True)
            if not (run.root / rel).exists():
                shutil.copy2(src / rel, run.root / rel)
            if hashlib.sha256((run.root / rel).read_bytes()).hexdigest() != frozen[rel]:
                raise SystemExit('copied record differs: ' + rel)
            copied[rel] = frozen[rel]
    immutable(run.root / 'seed_manifest.json', dict(source=str(src.relative_to(REPO)), records=copied))
    print(len(copied), 'records seeded from v31')


if __name__ == '__main__':
    main()
