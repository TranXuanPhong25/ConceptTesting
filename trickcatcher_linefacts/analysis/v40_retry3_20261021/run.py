"""One explicitly authorized new namespace; frozen v40 implementation unchanged."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from trickcatcher_linefacts.pipelines.v40_concept_agent import d1

OLD = d1.ROOT
ROOT = OLD.with_name('d1_retry3_20261021')


def old_verify():
    inventory = d1.read(OLD / 'terminal_inventory.json')
    actual = {str(p.relative_to(OLD)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in OLD.rglob('*') if p.is_file() and p.name != 'terminal_inventory.json'}
    assert actual == inventory, 'old_terminal_inventory_drift'
    d1.verify(OLD)
    for name in ('d1_retry_20261021', 'd1_retry2_20261021'):
        prior = OLD.with_name(name)
        saved = d1.read(prior / 'terminal_inventory.json')
        actual = {str(p.relative_to(prior)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in prior.rglob('*') if p.is_file() and p.name != 'terminal_inventory.json'}
        assert saved == actual, 'prior_retry_inventory_drift'


def register():
    old_verify()
    assert sorted(p.name for p in ROOT.iterdir()) == ['metadata_probe'], 'not_a_fresh_metadata_only_root'
    assert d1.read(ROOT / 'metadata_probe/result.json')['state'] == 'passed', 'metadata_probe_not_passed'
    for name in ('preparation.json', 'approval.json'):
        shutil.copy2(OLD / name, ROOT / name)
    for name in ('prepared', 'shared'):
        shutil.copytree(OLD / name, ROOT / name)
    d1.verify(ROOT)
    d1.write_json(ROOT / 'registration.json', {
        'registered_utc': datetime.now(timezone.utc).isoformat(),
        'authorization': 'user explicit retry after served32B model correction; preliminary live metadata passed',
        'original_root': str(OLD.relative_to(REPO)),
        'old_inventory_sha256': hashlib.sha256((OLD / 'terminal_inventory.json').read_bytes()).hexdigest(),
        'launcher_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'prereg_sha256': hashlib.sha256((HERE / 'PREREG.md').read_bytes()).hexdigest(),
        'thread_id': os.environ.get('CODEX_THREAD_ID'),
        'new_completion_cap': 72, 'previous_unknown_completion_attempts': 1,
        'cumulative_completion_cap': 73,
        'shared_evidence_origin': 'byte-identical historical CPU preparation; no new workers',
        'state': 'registered_no_new_model_calls'})
    print('registered fresh run; historical preparation reused; no model calls')


def run():
    with (ROOT / 'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / 'status.json').exists():
            raise RuntimeError('new_run_already_consumed_no_automatic_retry')
        registration = d1.read(ROOT / 'registration.json')
        assert registration['launcher_sha256'] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        assert registration['prereg_sha256'] == hashlib.sha256((HERE / 'PREREG.md').read_bytes()).hexdigest()
        audit = d1.read(HERE / 'audit.json')
        assert audit['passed'] and audit['launcher_sha256'] == registration['launcher_sha256']
        old_verify(); d1.verify(ROOT); d1.quota_check(ROOT)
        approval = d1.read(ROOT / 'approval.json')
        assert approval['passed'] and approval['sources'] == d1.sources()
        assert approval['preparation_hash'] == d1.digest(d1.read(ROOT / 'preparation.json'))
        state = {'state': 'running', 'model': d1.CONFIG['model'], 'controller_pid': os.getpid(),
                 'started_utc': datetime.now(timezone.utc).isoformat()}
        d1.write_json(ROOT / 'status.json', state)
        client = None
        try:
            client = d1.Client(ROOT / 'transport')
            d1.run(client, root=ROOT)
            state['state'] = 'complete'
        except Exception as exc:
            state.update(state='stopped', error_type=type(exc).__name__,
                         reason=str(exc) if isinstance(exc, d1.TransportStop) else 'controller_failure')
        finally:
            if client:
                client.close()
            state['ended_utc'] = datetime.now(timezone.utc).isoformat()
            d1.write_json(ROOT / 'status.json', state)
        old_verify(); d1.verify(ROOT)
        inventory = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in ROOT.rglob('*') if p.is_file()}
        d1.immutable(ROOT / 'terminal_inventory.json', inventory)
        print(json.dumps(state), flush=True)
        thread_id = registration.get('thread_id')
        if thread_id:
            message = (
                'Owned explicitly user-authorized v40 Qwen32B retry finished/stopped. '
                'Read status and artifacts under /home/phong/dev/ConceptTester/trickcatcher_linefacts/'
                'out/pipelines/v40_concept_agent/humaneval/d1_retry3_20261021 and '
                'analysis/v40_retry3_20261021/PREREG.md. No duplicate/retry/reset/repair or new calls. '
                'Check Codex5h quota, stop<=15%. Verify old d1 inventory and unchanged frozen source, '
                'new run inventory/prepared/approval. If complete review all8episodes3arms raw Qwen '
                'predictions/evidence/revision/controls with clean-context audit; saved-data post-freeze '
                'scoring only. If incomplete report exact recorded terminal cause and all unattempted slots. '
                'Report new plus cumulative requests/known tokens/unknowns, reused CPU preparation '
                'vs actual new worker calls. Update own analysis/RESULTS/memory and commit/push own '
                'files main, preserve other sessions and endpoint secrecy. Reply Vietnamese.')
            done = subprocess.run(['codex', 'queue', '--thread', thread_id, '--message', message],
                                  cwd=REPO, capture_output=True, text=True, timeout=30)
            d1.write_json(HERE / 'callback.json', {'method': 'codex_queue', 'returncode': done.returncode})


if __name__ == '__main__':
    {'register': register, 'run': run}[sys.argv[1]]()
