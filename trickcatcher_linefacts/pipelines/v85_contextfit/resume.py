"""Continue v85 from verified checkpoints using the amended context allocation."""
import hashlib
import json
import os
import re
from pathlib import Path
from ..v85_retrievalhybrid import comparison as run
from ..v85_retrievalhybrid.comparison_score import score
from ..v85_retrievalhybrid.llm_client import atomic_json
from ..v85_retrievalhybrid.prepare_comparison import sha, verify as verify_parent
from ..v85_retrievalhybrid.paths import REPO
from .transport import Client, request_key

HERE = Path(__file__).resolve().parent
ROOT = run.DATA_OUT/'comparison_contextfit_1'


def verify():
    verify_parent()
    for name, digest in json.loads((HERE/'FREEZE.json').read_text())['files'].items():
        if sha(REPO/name) != digest:
            raise ValueError('continuation_source_or_parent_changed')


def validate_import():
    manifest = json.loads((ROOT/'IMPORT.json').read_text())
    for name, digest in manifest['files'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('imported_checkpoint_changed')
    attempts = [json.loads(line) for line in (ROOT/'transport/attempts.jsonl').read_text().splitlines()]
    responses = list((ROOT/'transport/calls').glob('*/response.json'))
    if len(attempts) != 509 or len({r['key'] for r in attempts}) != 509 or len(responses) != 509:
        raise ValueError('inherited_attempt_inventory_mismatch')
    for attempt in attempts:
        key = attempt['key']
        folder = ROOT/'transport/calls'/key
        request = json.loads((folder/'request.json').read_text())
        response = json.loads((folder/'response.json').read_text())
        if request_key(request['body']) != key or response.get('key') != key or response.get('status') != 'received':
            raise ValueError('inherited_request_identity_mismatch')
        if request['prompt_tokens'] + request['body']['max_tokens'] > 8192:
            raise ValueError('inherited_request_exceeds_context')


def main():
    run.ROOT = ROOT
    with (ROOT/'CLAIM.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(),tasks=113,K=1,protocol='v85_contextfit'),stream)
    verify()
    validate_import()
    run.v4_runtime.require_versions()
    client = Client(ROOT/'transport')
    client.preflight()
    prepared = [json.loads(p.read_text()) for p in (ROOT/'prepared').glob('*.json')]
    expected = {t['task'] for t in json.loads((run.HERE/'assets/tasks.json').read_text())}
    if len(prepared) != 113 or {p['v11']['task'] for p in prepared} != expected:
        raise ValueError('prepared_cohort_mismatch')
    prepared.sort(key=lambda p:hashlib.sha256(str(p['v11']['task']).encode()).hexdigest())
    run.run_pool('generation_pairs',enumerate(prepared),lambda item:run.generate_pair(item,client))

    def generate_oracle(job):
        response = client.chat(job['messages'],job['seed'],temperature=0.8,top_p=0.95,max_tokens=1024)
        atomic_json(ROOT/'oracles'/str(job['task'])/f'{job["sample"]}.json',dict(task=job['task'],sample=job['sample'],response=response))

    run.run_pool('shared_spec_oracle',run.oracle_jobs(prepared),generate_oracle)
    verify()
    files = [p for part in ('generation','oracles','transport','prepared') for p in (ROOT/part).rglob('*')
             if p.is_file() and p.suffix in ('.json','.jsonl','.py')]
    atomic_json(ROOT/'GENERATION_FREEZE.json',dict(files={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},target_reference_used=False))
    score(prepared)
    verify()
    adjustments = [json.loads(p.read_text()) for p in (ROOT/'transport/context').glob('*.json')]
    adjustments = [a for a in adjustments if a['effective_max_tokens'] < a['requested_max_tokens']]
    atomic_json(ROOT/'CONTINUATION.json',dict(protocol='v85_contextfit',inherited_completion_attempts=509,
        total_completion_attempts=len((ROOT/'transport/attempts.jsonl').read_text().splitlines()),adjustments=adjustments))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        reason = str(exc) if re.fullmatch(r'[A-Za-z0-9_ ():.=-]+',str(exc)) else type(exc).__name__
        atomic_json(ROOT/'STATUS.json',dict(stage='blocked',error_type=type(exc).__name__,reason=reason))
        raise SystemExit(1)
