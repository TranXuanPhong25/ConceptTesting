"""V4 interpreter, immutable artifacts, and namespace-isolated job dispatch."""

# Direct-script workers run with -I: establish this copy's package explicitly.
import sys as _package_sys
from pathlib import Path as _PackagePath
if not __package__:
    _package_here = _PackagePath(__file__).resolve().parent
    _package_sys.path.insert(0, str(_package_here.parents[2]))
    __package__ = "trickcatcher_linefacts.pipelines." + _package_here.name
from .paths import REPO as _REPO, DATA_OUT, CONFIG, dataset_paths
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from . import gen_inputs, preconditions
from .llm_client import atomic_json

HERE = Path(__file__).resolve().parent
VERSIONS = {'hypothesis': '6.169.0', 'mutmut': '3.8.0', 'coverage': '7.16.2', 'libcst': '1.9.0'}


def interpreter(value=None):
    python = Path(value or os.environ.get('V4_PYTHON') or CONFIG['V4_PYTHON']).absolute()
    if not (python.parent.parent/'pyvenv.cfg').is_file():
        raise ValueError('V4_PYTHON/--python must name the dedicated v4 venv interpreter')
    return python


def require_versions():
    found = {name: importlib.metadata.version(name) for name in VERSIONS}
    if found != VERSIONS:
        raise ValueError(f'v4 tool version mismatch: {found}; expected {VERSIONS}')
    return found


def immutable(path, value):
    path = Path(path)
    if path.exists():
        if json.loads(path.read_text()) != json.loads(json.dumps(value)):
            raise ValueError(f'artifact changed; use a fresh directory: {path}')
    else:
        atomic_json(path, value)


def isolated(mode, job, directory, python=None, timeout=900):
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=True)
    jp, op = directory/(mode+'_job.json'), directory/(mode+'_result.json')
    payload = dict(job, mode=mode)
    immutable(jp, payload)
    op.unlink(missing_ok=True)
    result = gen_inputs.sandbox(interpreter(python), HERE/'v4_worker.py', jp, op, timeout)
    if isinstance(result, dict) and 'worker_error' in result:
        raise RuntimeError(result['worker_error'])
    return result


def source_hashes():
    return {p.name: preconditions.sha(p.read_bytes()) for p in sorted(HERE.glob('v4_*.py'))} | {
        p: preconditions.sha((HERE/p).read_bytes()) for p in
        ('facts.py','tracer.py','preconditions.py','precond_prompts.py','gen_inputs.py',
         'gen_prompts.py','generator_worker.py','prompts.py','llm_client.py','run_v4.py',
         'paths.py','run.py','offline_client.py','hypothesis_replay.py',
         'hypothesis_constants.json','config.json','scorer.py','fair_generation.py',
         'relations.py','rel_prompts.py','rel_report.py',
         'hypotheses.py','hyp_worker.py','hyp_prompts.py','hyp_generation.py','hyp_report.py')}
