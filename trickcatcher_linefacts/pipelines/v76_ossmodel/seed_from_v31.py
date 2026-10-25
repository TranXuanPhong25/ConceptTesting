"""Reuse only frozen model-independent v31/v34 artifacts; never reuse LLM arms."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from .flow_common import immutable
from .ft_run import FTRun
from .paths import REPO

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'assets/frozen_seed_manifest.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed(run):
    if run.name != 'vibepass_half':
        raise ValueError('only_registered_33_case_cohort')
    plan = json.loads(MANIFEST.read_text())
    src, v34 = REPO / plan['source'], REPO / plan['v34_source']
    for root, key in ((src, 'v31_freeze_sha256'), (v34, 'v34_freeze_sha256')):
        if sha(root / 'generation_frozen.json') != plan[key]:
            raise ValueError('historical_generation_freeze_drift')
    cases = {c['case_id'] for c in run.cases}
    for rel, expected in plan['records'].items():
        if Path(rel).parts[1] not in cases:
            continue
        if sha(src / rel) != expected or sha(v34 / rel) != expected:
            raise ValueError('frozen_seed_source_drift:' + rel)
        target = run.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(src / rel, target)
        if sha(target) != expected:
            raise ValueError('frozen_seed_destination_drift:' + rel)
    copied = {k: v for k, v in plan['records'].items() if Path(k).parts[1] in cases}
    immutable(run.root / 'seed_manifest.json', dict(source=plan['source'], manifest_sha256=sha(MANIFEST), records=copied))
    return copied


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', choices=['vibepass_half'], default='vibepass_half')
    args = parser.parse_args()
    print(len(seed(FTRun(args.cohort))), 'model-independent records seeded; zero model calls')
