"""Register local preset deployments; creating a preset never starts inference."""
import json
import hashlib
from pathlib import Path

from prefect import serve
from .config import ROOT,normalize
from .flows import benchmark,resume_saved_batch
from .names import RESUME_PRESET_NAME
from .benchmark_adapters import adapter_benchmark


def source_revision():
    paths=[path for path in (ROOT/'final/src/modular').rglob('*.py')
        if 'tests' not in path.parts and '__pycache__' not in path.parts]
    paths += [path for path in (ROOT/'final/src/runtime').glob('*.py')]
    paths += [path for path in (ROOT/'final/src/models').glob('*.py')]
    paths += [ROOT/'final/pynguin-requirements.txt']
    paths += [ROOT/'final/src/models/core_model.py', ROOT/'final/presets/run_console.json',
              ROOT/'final/data/contracts.json',ROOT/'final/data/humaneval.jsonl',
              ROOT/'final/data/humanevalplus_v0.1.10_references.json']
    paths += [path for path in (ROOT/'final/src/orchestration').glob('*.py')]
    paths += [path for path in (ROOT/'final/src/benchmarks').glob('*') if path.is_file()]
    paths += list((ROOT/'final/data/benchmarks').glob('*'))
    paths += [ROOT/'final/presets/benchmark_adapters.json', ROOT/'final/presets/criteria_pynguin.json']
    revision=hashlib.sha256()
    for path in sorted(set(paths)):
        revision.update(str(path.relative_to(ROOT)).encode());revision.update(path.read_bytes())
    return 'src-'+revision.hexdigest()[:20]


def main():
    presets=json.loads((ROOT/'final/presets/run_console.json').read_text())
    version=source_revision()
    deployments=[benchmark.to_deployment(name=preset['name'],parameters={**normalize(preset['parameters']),'preview_only':preset.get('preview_only',False)},
        description=preset['description'],tags=['ConceptTester','preset',preset['parameters']['mode']],
        version=version,concurrency_limit=1,enforce_parameter_schema=True) for preset in presets]
    prepared=json.loads((ROOT/'final/presets/criteria_pynguin.json').read_text())
    deployments.extend(benchmark.to_deployment(name=preset['name'],
        parameters={**normalize(preset['parameters']), 'preview_only':True},
        description=preset['description'],tags=['ConceptTester','preset','prepared'],
        version=version,concurrency_limit=1,enforce_parameter_schema=True) for preset in prepared)
    deployments.append(resume_saved_batch.to_deployment(name=RESUME_PRESET_NAME,
        description='Resume run Console hoặc matched-batch đã dừng. Giữ nguyên responses/config/retry budget. Dùng deployment này thay cho Retry một flow ID cũ.',
        tags=['ConceptTester','resume'],version=version,concurrency_limit=1,enforce_parameter_schema=True))
    adapter_presets=json.loads((ROOT/'final/presets/benchmark_adapters.json').read_text())
    deployments.extend(adapter_benchmark.to_deployment(name=preset['name'],parameters=preset['parameters'],
        description=preset['description'],tags=['ConceptTester','preset','adapters'],
        version=version,concurrency_limit=1,enforce_parameter_schema=True) for preset in adapter_presets)
    serve(*deployments,limit=1,pause_on_shutdown=False)


if __name__=='__main__':main()
