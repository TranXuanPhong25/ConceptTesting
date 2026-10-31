"""CPU-only public bundle construction; no client import or model dispatch."""
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
from . import datasets,provenance
from .paths import HERE,CONFIG
from .llm_client import atomic_json

WORK=HERE/'out/cpu_preparation/continuation'
ROOT=HERE/'assets/public_bundles'
ALGORITHM=('datasets.py','ft_tools.py','ft_concepts.py','combined_facts.py','facts.py','v4_tools.py','tracer.py','spec_facts.py')


def algorithm_hashes():return {p:provenance.sha(HERE/p) for p in ALGORITHM}


def one(item):
    name,task=item
    directory=WORK/name/str(task['task']);path=ROOT/name/str(task['task'])/'prepared.json'
    if path.exists():return name,task['task'],provenance.sha(path)
    result=datasets.prepare_one(name,task,directory,Path(CONFIG['V4_PYTHON']))
    atomic_json(path,result)
    return name,task['task'],provenance.sha(path)


def load(name):
    manifest=json.loads((HERE/'assets/cpu_prepared_manifest.json').read_text())
    if manifest['algorithm']!=algorithm_hashes() or manifest['inputs_sha256']!=provenance.sha(HERE/'INPUTS.json'):
        raise ValueError('cpu_preparation_source_drift')
    out=[]
    for t in datasets.cohort(name):
        rel=f"{name}/{t['task']}/prepared.json"
        if rel not in manifest['files']:return None
        p=ROOT/rel
        if provenance.sha(p)!=manifest['files'][rel]:raise ValueError('cpu_bundle_drift:'+rel)
        out.append(json.loads(p.read_text()))
    return out


def main():
    jobs=[('humaneval',t) for t in datasets.cohort('humaneval')]
    WORK.mkdir(parents=True,exist_ok=True)
    ROOT.mkdir(parents=True,exist_ok=True)
    from .v4_runtime import immutable
    immutable(WORK/'algorithm.json',dict(algorithm=algorithm_hashes(),inputs_sha256=provenance.sha(HERE/'INPUTS.json')))
    files={}
    with ProcessPoolExecutor(max_workers=3) as pool:
        for name,n,h in pool.map(one,jobs):
            files[f'{name}/{n}/prepared.json']=h
            print(name,n,'CPU bundle verified',flush=True)
    atomic_json(HERE/'assets/cpu_prepared_manifest.json',dict(algorithm=algorithm_hashes(),inputs_sha256=provenance.sha(HERE/'INPUTS.json'),files=files,
        scope='model-independent public CPU preparation, no efficacy data; all28 fixed HumanEval dev quarter; no model outcomes'))

if __name__=='__main__':main()
