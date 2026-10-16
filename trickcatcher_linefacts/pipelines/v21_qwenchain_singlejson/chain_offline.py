"""Run preregistered offline interface checks, preserving each invocation and source hashes."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from .paths import DATA_OUT,CONFIG
from .llm_client import atomic_json
HERE=Path(__file__).resolve().parent


def main():
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    root=DATA_OUT/'offline_checks'/stamp;root.mkdir(parents=True,exist_ok=False)
    sources={p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')}
    sources.update({name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('config.json','PREREG.md')})
    atomic_json(root/'before.json',dict(run=stamp,sources=sources,phase='P1_offline',model_calls=0,semantic_accuracy=None,D_IO=None))
    interpreter=HERE.parents[2]/'CoverUp_concept/.venv/bin/python'
    with (root/'pytest.log').open('w') as log:
        p=subprocess.run([str(interpreter),'-B','-m','pytest','-q',str(HERE/'test_chain_interfaces.py'),'--junitxml='+str(root/'checks.xml')],cwd=HERE.parents[2],stdout=log,stderr=subprocess.STDOUT)
    summary=dict(run=stamp,exit_code=p.returncode,phase='P1_offline',model_calls=0,semantic_accuracy=None,D_IO=None)
    atomic_json(root/'result.json',summary);print(json.dumps(dict(summary,directory=str(root))))
    raise SystemExit(p.returncode)


if __name__=='__main__':main()
