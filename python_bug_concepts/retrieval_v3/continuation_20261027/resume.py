"""Preserve frozen run; complete one oversized judge and original utility plan."""
import hashlib
import json
import time
from pathlib import Path
from ..client import Client, atomic
from ..run import execute, validate_judge
from ..grade_utility import grade
from ..report import report
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'out/run_20261026'

def compact(value):
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items() if k != 'repr'}
    if isinstance(value, str) and len(value) > 320:
        return {'presentation_omitted': True, 'length': len(value), 'sha256': hashlib.sha256(value.encode()).hexdigest(), 'prefix': value[:160], 'suffix': value[-160:]}
    if isinstance(value, list):
        return [compact(v) for v in value]
    return value

def main():
    client = Client(OUT)
    client.preflight()
    original = json.loads((OUT/'judge_jobs/HumanEval_15.json').read_text())
    revised = json.loads(json.dumps(original))
    payload = json.loads(revised['messages'][1]['content'])
    payload['validated_witness'] = compact(payload['validated_witness'])
    revised['messages'][1]['content'] = json.dumps(payload, ensure_ascii=False)
    atomic(HERE/'judge_15_original.json', original)
    atomic(HERE/'judge_15_compact.json', revised)
    response = client.complete(revised['messages'], stage='judge', max_tokens=1000, seed=314215)
    atomic(OUT/'judged/HumanEval_15.json', {'task_id':'HumanEval/15', 'arm':'blind', 'response':response, 'mapping':revised['mapping'], 'valid_schema':validate_judge(response,revised['mapping']), 'presentation_amendment':str(HERE.name)})
    atomic(HERE/'STATUS.json', {'stage':'utility', 'started':time.time()})
    execute('utility',OUT)
    grade(OUT)
    report(OUT)
    atomic(HERE/'TERMINAL.json', {'status':'complete', 'finished':time.time()})

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        atomic(HERE/'TERMINAL.json', {'status':'stopped','error_type':type(exc).__name__,'finished':time.time()})
        raise SystemExit(type(exc).__name__)
