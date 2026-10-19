"""Dependency fingerprint for exact offline resume/cache, including worker interpreter."""
import hashlib
import json
from pathlib import Path
from .paths import CONFIG
HERE=Path(__file__).resolve().parent


def fingerprint():
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))}
    files['config.json']=hashlib.sha256((HERE/'config.json').read_bytes()).hexdigest()
    python=Path(CONFIG['V4_PYTHON'])
    files['worker_python']=hashlib.sha256(python.read_bytes()).hexdigest() if python.is_file() else 'unavailable'
    return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
