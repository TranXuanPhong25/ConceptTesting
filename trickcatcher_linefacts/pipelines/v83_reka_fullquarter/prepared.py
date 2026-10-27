"""Preparation snapshot, regenerated only before any paid output; no network."""
import argparse
import hashlib
import json
from pathlib import Path
from .paths import HERE


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    record=json.loads((HERE/'PREPARED.json').read_text())
    protocol=record.pop('protocol_sha256')
    if digest(record)!=protocol:raise ValueError('prepared_protocol_hash_drift')
    for rel,h in record['files'].items():
        if sha(HERE/rel)!=h:raise ValueError('prepared_source_drift:'+rel)
    return protocol


def write():
    config=json.loads((HERE/'config.json').read_text())
    record=dict(version=config['VERSION'],registered_as='v82_deepinfra_quarter',
        status='fixed HumanEval quarter, two arms K1',
        model_packages_sha256={m:digest(c) for m,c in config['models'].items()},
        files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
            if p.is_file() and p.name!='PREPARED.json' and not any(x in ('out','__pycache__','.pytest_cache') for x in p.relative_to(HERE).parts)
            and p.suffix in ('.py','.json','.md','.sh','.jinja','.txt','.tiktoken')})
    record['protocol_sha256']=digest(record)
    (HERE/'PREPARED.json').write_text(json.dumps(record,indent=2)+'\n')
    return verify()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');a=p.parse_args()
    print(write() if a.write else verify())
