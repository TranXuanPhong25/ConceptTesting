"""Frozen program cohort validation and recorded model-call accounting."""
import json
from pathlib import Path
from final.src.runtime.artifacts import digest
from .dataset import DATA_SHA256

def load_cohort(path: Path):
    data = json.loads(path.read_text())
    if data['cohort_sha256'] != digest(data['tasks']):
        raise ValueError('Frozen cohort checksum mismatch')
    if data['dataset_sha256'] != DATA_SHA256:
        raise ValueError('Frozen cohort dataset mismatch')
    return data

def call_usage(directory):
    attempts=list(directory.glob('tasks/*/calls/*/attempt.json'))
    responses=list(directory.glob('tasks/*/calls/*/response.json'))
    totals={key:0 for key in ('prompt_tokens','completion_tokens','total_tokens')}
    for path in responses:
        usage=json.loads(path.read_text()).get('usage',{})
        for key in totals:
            value=usage.get(key,0)
            if type(value) in (int,float):
                totals[key]+=value
    return dict(invocations=len(attempts),received=len(responses),unknown=len(attempts)-len(responses),known_usage=totals)
