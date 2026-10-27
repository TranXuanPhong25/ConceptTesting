"""Read-only SHA-pinned preparation sources; all new outputs stay in v77."""
import hashlib
import json
from .paths import HERE, REPO


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_file(path):
    path=path.resolve()
    manifest=json.loads((HERE/'INPUTS.json').read_text())
    key=str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)
    if key not in manifest['files'] or sha(path)!=manifest['files'][key]:
        raise ValueError('input_hash_mismatch:'+key)
    return path


def read(path):
    return json.loads(verify_file(path).read_text())


def sources():
    return {str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
            if p.is_file() and not any(x in ('out','__pycache__','.pytest_cache') for x in p.relative_to(HERE).parts)
            and p.suffix in ('.py','.json','.md','.sh','.jinja','.tiktoken','.txt')}
